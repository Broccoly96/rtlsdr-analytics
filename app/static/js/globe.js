// globe.js -- entrypoint for globe.html: a 3D scene (CesiumJS) showing every
// currently-live aircraft's position over the shared broadcast WS
// /ws/aircraft-positions (app/api/routers/aircraft_positions.py -- one
// background readsb poll fanned out to every connected client, replacing
// "one poll per selected aircraft" now that the default view shows
// everything at once). Each aircraft is a 3D model (app/static/models/
// aircraft.glb, CesiumGS/cesium's own Apache-2.0 sample aircraft),
// color-tinted by altitude band (same bands/colors as map.js's 2D track
// coloring) and oriented by heading (track_deg) + roll (readsb's `roll`,
// often absent) + an approximated pitch (from vertical rate + ground
// speed -- readsb has no real pitch field). Every currently-tracked
// aircraft draws its own historical track (GET /api/aircraft/{icao}/positions)
// plus a live-extending polyline fed by the same broadcast stream, both
// colored by altitude band (same as the 3D models and map.js's 2D tracks,
// see addBandRunPolylines) at a user-configurable opacity (Settings tab,
// default 50%).
// Shift+click isolates one aircraft: hides every other one (model + track)
// and flies the camera to it (no separate per-aircraft WS needed here --
// that connection is still used by aircraftinfo.js's sidebar for its
// deeper tar1090-parity fields). An optional 1Hz "fast" update mode can be
// requested per-connection over the same broadcast socket (see
// aircraft_positions.py). The header's mode selector can instead switch to
// a "history" view (GET /api/tracks?hours=, same endpoint/shape the flat
// 2D map uses): every aircraft's past track over 1h/6h/24h, no live
// broadcast/3D models, with a hover popup mirroring map.js's. Ground
// imagery (ArcGIS World Imagery) is fetched continuously by the browser
// while this page is open -- see README Security & Privacy. Nothing here
// is persisted.

import { api } from "./api.js";
import { cssColor } from "./chart.js";
import { openAircraftSidebar } from "./aircraftinfo.js";
import { setNationalityBlocks } from "./nationality.js";
import { updateEmergencySquawkBanner } from "./squawk-alert.js";
import { checkTransitAlerts, resetTransitAlerts } from "./transit-alert.js";
import { checkNewArrivals, resetKnownAircraft } from "./speech.js";
import { loadFavorites } from "./favorites.js";
import { checkFavoriteArrivals, resetFavoriteArrivals } from "./browser-notify.js";
import { formatAltitude, formatDistance } from "./units.js";
import { getTrackOpacity } from "./track-settings.js";
import { renderAltitudeLegend } from "./altitude-legend.js";
import { registerServiceWorker } from "./pwa.js";
import { ui } from "./ui.js";
import { t, applyStaticTranslations } from "./i18n.js";

const formatTime = ui.formatTime;

const FT_TO_M = 0.3048;
const DEFAULT_HOURS = 6;
function unknownAltitudeColor() {
  return cssColor("--text-muted", "#96a2b3");
}

const AIRCRAFT_MODEL_URI = "/static/models/aircraft.glb";
const KT_TO_FT_PER_S = 1.68781;
const FPM_TO_FT_PER_S = 1 / 60;
// Cesium_Air.glb's own forward/bank axes vs. this app's heading=track_deg,
// roll=readsb `roll` assumption. Adjust here, not at every call site, if a
// different model is ever swapped in.
//
// Heading offset empirically confirmed via a synthetic fixed-heading test
// entity viewed top-down: a commanded heading of 0 (true north) rendered
// with the nose visibly pointing east, i.e. 90 degrees clockwise from
// intended -- -90 degrees corrects it.
const MODEL_HEADING_OFFSET_RAD = Cesium.Math.toRadians(-90);
// Roll sign is NOT independently visually confirmed the same way (no
// aircraft with a real, non-zero `roll` happened to be turning during
// testing to check bank direction against) -- left at 1 on the
// assumption that Cesium's documented HeadingPitchRoll.roll convention
// ("positive is banking to the right") already matches ADS-B's own roll
// field convention (also positive = right bank). Flip to -1 if a real
// turning aircraft is later observed banking the wrong way.
const MODEL_ROLL_SIGN = 1;

// readsb has no pitch field -- approximated from vertical rate (fpm) and
// ground speed (kt), both converted to ft/s. Best-effort visual cue, not
// real flight dynamics.
function computePitchRad(verticalRateFpm, groundSpeedKt) {
  if (verticalRateFpm == null || groundSpeedKt == null || groundSpeedKt <= 0) return 0;
  const verticalFtPerS = verticalRateFpm * FPM_TO_FT_PER_S;
  const horizontalFtPerS = groundSpeedKt * KT_TO_FT_PER_S;
  return Math.atan2(verticalFtPerS, horizontalFtPerS);
}

function computeOrientation(cartesian, position) {
  const headingRad = Cesium.Math.toRadians(position.track_deg || 0) + MODEL_HEADING_OFFSET_RAD;
  const pitchRad = computePitchRad(position.vertical_rate_fpm, position.ground_speed_kt);
  const rollRad = Cesium.Math.toRadians(position.roll_deg || 0) * MODEL_ROLL_SIGN;
  return Cesium.Transforms.headingPitchRollQuaternion(
    cartesian,
    new Cesium.HeadingPitchRoll(headingRad, pitchRad, rollRad)
  );
}

function showError(message) {
  const el = document.getElementById("globe-error");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
}

function hideError() {
  const el = document.getElementById("globe-error");
  if (el) el.hidden = true;
}

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

function createViewer() {
  const imageryProvider = new Cesium.UrlTemplateImageryProvider({
    url: "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    credit: new Cesium.Credit(
      "Esri, Maxar, Earthstar Geographics, and the GIS User Community",
      true
    ),
    maximumLevel: 19,
  });

  return new Cesium.Viewer("cesium-container", {
    baseLayer: new Cesium.ImageryLayer(imageryProvider),
    baseLayerPicker: false,
    geocoder: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    timeline: false,
    animation: false,
    infoBox: false,
    selectionIndicator: false,
    fullscreenButton: false,
  });
}

// --- altitude color coding (mirrors map.js's colorForAltitude) -----------

let altitudeBands = [];

function setAltitudeBands(bands) {
  altitudeBands = (bands || []).map((b) => ({
    max: b.max_ft == null ? Infinity : b.max_ft,
    color: b.color,
  }));
}

function colorForAltitude(altitudeFt) {
  if (altitudeFt == null) return unknownAltitudeColor();
  for (const band of altitudeBands) {
    if (altitudeFt <= band.max) return band.color;
  }
  return unknownAltitudeColor();
}

// Cesium polylines have one `material` for the whole entity (no per-vertex
// color), same constraint map.js's "one color per GeoJSON feature" paint
// expression has -- so a track that changes altitude band along its length
// is split into one polyline entity per contiguous band "run", carrying
// the boundary point into both runs so the line stays visually connected
// across a color change. `points` is any array; `toCartesianAndAltitude`
// adapts each item's shape ({lon,lat,altitude_ft} objects vs [lon,lat,alt]
// arrays) to {cartesian, altitudeFt}. New entities are pushed onto `out`.
function addBandRunPolylines(out, points, toCartesianAndAltitude, opacity) {
  let currentColor = null;
  let currentPositions = [];
  const flush = () => {
    if (currentPositions.length > 1) {
      out.push(
        viewer.entities.add({
          polyline: {
            positions: currentPositions,
            width: 3,
            material: Cesium.Color.fromCssColorString(currentColor).withAlpha(opacity),
          },
        })
      );
    }
  };
  for (const point of points) {
    const { cartesian, altitudeFt } = toCartesianAndAltitude(point);
    const color = colorForAltitude(altitudeFt);
    if (color !== currentColor) {
      flush();
      currentPositions = currentPositions.length ? [currentPositions[currentPositions.length - 1]] : [];
      currentColor = color;
    }
    currentPositions.push(cartesian);
  }
  flush();
}

function positionPointToCartesian(p) {
  return { cartesian: Cesium.Cartesian3.fromDegrees(p.lon, p.lat, (p.altitude_ft || 0) * FT_TO_M), altitudeFt: p.altitude_ft };
}

// Same shape as positionPointToCartesian, for GET /api/tracks's GeoJSON
// [lon, lat, altitude_ft] coordinate arrays (history mode) rather than
// GET /api/aircraft/{icao}/positions's {lon,lat,altitude_ft} objects.
function coordinateToCartesian([lon, lat, altitudeFt]) {
  return { cartesian: Cesium.Cartesian3.fromDegrees(lon, lat, (altitudeFt || 0) * FT_TO_M), altitudeFt };
}

// --- state ----------------------------------------------------------------

let viewer = null;
let socket = null;
const aircraftEntities = new Map(); // icao -> Cesium.Entity (model + label)
const latestPositions = new Map(); // icao -> latest broadcast entry
const hiddenIcaos = new Set(); // user-unchecked via the picker
const knownAircraft = new Map(); // icao -> callsign|null, for the picker list
const pickerCheckboxes = new Map();
const pickerLabels = new Map();

// Every currently-tracked aircraft gets its own historical + live-extending
// track -- not just the isolated one -- both colored by altitude band (see
// addBandRunPolylines) to match the legend, rather than the old fixed
// cyan=historical/yellow=live-extending distinction. icao ->
// { historyEntities: Entity[], liveRuns: [{positions, color, entity}] }.
// liveRuns is a small ordered list of same-band CallbackProperty-backed
// polylines, appended to in place while the aircraft's altitude stays in
// one band and extended with a new run (sharing the boundary point) when
// the band changes on a later broadcast tick -- see pushLiveTrackPoint.
const trackState = new Map();

let isolatedIcao = null;

// "live" (default -- the broadcast-driven multi-aircraft models/tracks
// above) or "history" (GET /api/tracks?hours=, every aircraft's past
// track only, no 3D models -- see enterHistoryMode/enterLiveMode).
let mode = "live";
let historyEntities = [];
let fastModeEnabled = false;
// Incremented on every enterHistoryMode() call; a resolved fetch only
// draws if it's still the latest request -- the slider (unlike the old
// discrete buttons) can fire several requests in quick succession while
// dragging, and responses aren't guaranteed to resolve in request order.
let historyRequestId = 0;

// Read once at load (same "reload to pick up a change" precedent as
// every other setting in this app).
const trackOpacity = getTrackOpacity();

// Cesium's default view is the whole Earth -- without this, aircraft near
// the receiver are too small/distant to see until the user manually
// zooms in. Frames once on the first broadcast frame with any aircraft,
// then leaves the camera alone (never fights the user's own pan/zoom).
let hasAutoFramed = false;

function autoFrameOnFirstData(positions) {
  if (hasAutoFramed || positions.length === 0) return;
  hasAutoFramed = true;
  const avgLat = positions.reduce((sum, p) => sum + p.lat, 0) / positions.length;
  const avgLon = positions.reduce((sum, p) => sum + p.lon, 0) / positions.length;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(avgLon, avgLat, 400000),
  });
}

function applyVisibility() {
  for (const [icao, entity] of aircraftEntities) {
    const visible = isolatedIcao ? icao === isolatedIcao : !hiddenIcaos.has(icao);
    entity.show = visible;
    const track = trackState.get(icao);
    if (track) {
      for (const historyEntity of track.historyEntities) historyEntity.show = visible;
      for (const run of track.liveRuns) run.entity.show = visible;
    }
  }
}

// Appends one broadcast tick's position to the aircraft's live-extending
// track, starting a new band-run (see addBandRunPolylines' doc comment)
// when the altitude band has changed since the last point.
function pushLiveTrackPoint(state, position) {
  const { cartesian, altitudeFt } = positionPointToCartesian(position);
  const color = colorForAltitude(altitudeFt);
  const currentRun = state.liveRuns[state.liveRuns.length - 1];
  if (currentRun && currentRun.color === color) {
    currentRun.positions.push(cartesian);
    return;
  }
  const positions = currentRun ? [currentRun.positions[currentRun.positions.length - 1], cartesian] : [cartesian];
  const run = { color, positions };
  run.entity = viewer.entities.add({
    polyline: {
      positions: new Cesium.CallbackProperty(() => run.positions, false),
      width: 3,
      material: Cesium.Color.fromCssColorString(color).withAlpha(trackOpacity),
    },
  });
  state.liveRuns.push(run);
}

// One-time (per icao) historical fetch + a live-extending polyline fed by
// every subsequent broadcast frame -- runs for every aircraft as soon as
// it's first seen, not just an isolated one.
function ensureTrack(icao) {
  if (trackState.has(icao)) return;
  const state = { historyEntities: [], liveRuns: [] };
  trackState.set(icao, state);

  api
    .getAircraftPositions(icao, DEFAULT_HOURS)
    .then((positions) => {
      if (!trackState.has(icao)) return; // aircraft went stale before this resolved
      for (const segment of positions.segments) {
        if (segment.length < 2) continue;
        addBandRunPolylines(state.historyEntities, segment, positionPointToCartesian, trackOpacity);
      }
      applyVisibility(); // newly-added entities default to show=true
    })
    .catch((err) => {
      console.error("aircraft positions fetch failed", err);
    });
}

function removeTrack(icao) {
  const state = trackState.get(icao);
  if (!state) return;
  for (const entity of state.historyEntities) viewer.entities.remove(entity);
  for (const run of state.liveRuns) viewer.entities.remove(run.entity);
  trackState.delete(icao);
}

function upsertEntity(position) {
  const { icao, callsign, lat, lon, altitude_ft: altitudeFt } = position;
  const color = Cesium.Color.fromCssColorString(colorForAltitude(altitudeFt));
  const cartesian = Cesium.Cartesian3.fromDegrees(lon, lat, (altitudeFt || 0) * FT_TO_M);
  const orientation = computeOrientation(cartesian, position);

  let entity = aircraftEntities.get(icao);
  if (!entity) {
    entity = viewer.entities.add({
      position: cartesian,
      orientation,
      model: {
        uri: AIRCRAFT_MODEL_URI,
        minimumPixelSize: 32,
        maximumScale: 20000,
        color,
        colorBlendMode: Cesium.ColorBlendMode.MIX,
        colorBlendAmount: 0.5,
        silhouetteColor: Cesium.Color.fromCssColorString(cssColor("--bg", "#080b10")),
        silhouetteSize: 1,
      },
      label: {
        text: callsign || icao,
        font: "12px sans-serif",
        pixelOffset: new Cesium.Cartesian2(0, -24),
        fillColor: Cesium.Color.fromCssColorString(cssColor("--text", "#f2f5f7")),
      },
    });
    entity.icao = icao;
    aircraftEntities.set(icao, entity);
    ensureTrack(icao);
  } else {
    entity.position = cartesian;
    entity.orientation = orientation;
    entity.model.color = color;
    entity.label.text = callsign || icao;
  }
}

function removeStaleEntities(seenIcaos) {
  for (const icao of Array.from(aircraftEntities.keys())) {
    if (seenIcaos.has(icao)) continue;
    viewer.entities.remove(aircraftEntities.get(icao));
    aircraftEntities.delete(icao);
    latestPositions.delete(icao);
    removeTrack(icao);
  }
}

// --- aircraft picker (checkbox multi-select) -------------------------------

function addPickerRow(icao, callsign) {
  const list = document.getElementById("aircraft-picker-list");
  if (!list) return;

  const row = document.createElement("div");
  row.className = "globe-picker__item";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `picker-${icao}`;
  checkbox.checked = !hiddenIcaos.has(icao);
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) hiddenIcaos.delete(icao);
    else hiddenIcaos.add(icao);
    applyVisibility();
  });

  const label = document.createElement("label");
  label.htmlFor = checkbox.id;
  label.textContent = callsign ? `${callsign} (${icao})` : icao;

  pickerCheckboxes.set(icao, checkbox);
  pickerLabels.set(icao, label);
  row.append(checkbox, label);
  list.appendChild(row);
}

function ensurePickerEntry(icao, callsign) {
  const existing = knownAircraft.get(icao);
  if (existing !== undefined) {
    if (callsign && callsign !== existing) {
      knownAircraft.set(icao, callsign);
      const label = pickerLabels.get(icao);
      if (label) label.textContent = `${callsign} (${icao})`;
    }
    return;
  }
  knownAircraft.set(icao, callsign || null);
  addPickerRow(icao, callsign);
}

async function refreshPickerFromRecent() {
  try {
    const recent = await api.getRecentAircraft(24, 50);
    for (const row of recent) {
      ensurePickerEntry(row.icao, row.callsign);
    }
  } catch (err) {
    console.error("recent aircraft fetch failed", err);
  }
}

// --- isolate mode (shift+click one aircraft) -------------------------------

function exitIsolate() {
  isolatedIcao = null;
  document.getElementById("exit-isolate").hidden = true;
  if (viewer.trackedEntity) viewer.trackedEntity = undefined;
  applyVisibility();
}

function enterIsolate(icao) {
  isolatedIcao = icao;
  applyVisibility();
  document.getElementById("exit-isolate").hidden = false;

  const position = latestPositions.get(icao);
  if (position) {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        position.lon,
        position.lat,
        (position.altitude_ft || 0) * FT_TO_M + 20000
      ),
    });
  }
}

function toggleIsolate(icao) {
  hideTooltip();
  if (isolatedIcao === icao) {
    exitIsolate();
    return;
  }
  if (isolatedIcao) exitIsolate();
  enterIsolate(icao);
}

// --- mode switching (live vs. history) --------------------------------------

function teardownLiveView() {
  if (socket) {
    socket.close();
    socket = null;
  }
  if (isolatedIcao) exitIsolate();
  for (const icao of Array.from(aircraftEntities.keys())) {
    viewer.entities.remove(aircraftEntities.get(icao));
    aircraftEntities.delete(icao);
    removeTrack(icao);
  }
  latestPositions.clear();
  updateEmergencySquawkBanner([]);
  resetTransitAlerts();
  resetKnownAircraft();
  resetFavoriteArrivals();
}

function clearHistoryEntities() {
  for (const entity of historyEntities) viewer.entities.remove(entity);
  historyEntities = [];
}

function setLiveControlsVisible(visible) {
  const liveControls = document.getElementById("live-controls");
  if (liveControls) liveControls.hidden = !visible;
}

async function enterHistoryMode(hours) {
  hideTooltip();
  hideError();
  if (mode === "live") teardownLiveView();
  mode = "history";
  setLiveControlsVisible(false);
  clearHistoryEntities();

  const requestId = ++historyRequestId;
  try {
    const response = await api.getTracks(hours);
    if (requestId !== historyRequestId) return; // a newer request has since started
    for (const feature of response.features) {
      for (const coordinates of feature.geometry.coordinates) {
        if (coordinates.length < 2) continue;
        const before = historyEntities.length;
        addBandRunPolylines(historyEntities, coordinates, coordinateToCartesian, trackOpacity);
        for (let i = before; i < historyEntities.length; i++) {
          historyEntities[i].trackInfo = feature.properties;
        }
      }
    }
  } catch (err) {
    if (requestId !== historyRequestId) return;
    console.error("tracks fetch failed", err);
    showError(t("globe.tracksFetchFailed"));
  }
}

function enterLiveMode() {
  if (mode === "live") return;
  mode = "live";
  clearHistoryEntities();
  hideTooltip();
  setLiveControlsVisible(true);
  connectBroadcast();
}

// --- hover tooltip ----------------------------------------------------------

function positionTooltip(screenPosition) {
  const tooltip = document.getElementById("globe-tooltip");
  if (!tooltip) return null;
  const canvasRect = viewer.scene.canvas.getBoundingClientRect();
  const parent = tooltip.offsetParent;
  const parentRect = parent ? parent.getBoundingClientRect() : canvasRect;
  const canvasLeft = canvasRect.left - parentRect.left;
  const canvasTop = canvasRect.top - parentRect.top;
  const padding = 8;
  const desiredLeft = canvasLeft + screenPosition.x + 12;
  const desiredTop = canvasTop + screenPosition.y + 12;
  const maxLeft = canvasLeft + canvasRect.width - tooltip.offsetWidth - padding;
  const maxTop = canvasTop + canvasRect.height - tooltip.offsetHeight - padding;
  tooltip.style.left = `${Math.max(canvasLeft + padding, Math.min(desiredLeft, maxLeft))}px`;
  tooltip.style.top = `${Math.max(canvasTop + padding, Math.min(desiredTop, maxTop))}px`;
  return tooltip;
}

function showLiveTooltip(icao, screenPosition) {
  const position = latestPositions.get(icao);
  const tooltip = document.getElementById("globe-tooltip");
  if (!tooltip || !position) return;

  const parts = [
    position.callsign || icao,
    position.altitude_ft != null ? formatAltitude(position.altitude_ft) : null,
    position.ground_speed_kt != null ? `${Math.round(position.ground_speed_kt)} kt` : null,
  ].filter(Boolean);
  tooltip.textContent = parts.join(" / ");
  tooltip.hidden = false;
  positionTooltip(screenPosition);
}

// History-mode tooltip content mirrors map.js's describeFeature exactly
// (same properties GET /api/tracks already returns).
function showTrackTooltip(trackInfo, screenPosition) {
  const tooltip = document.getElementById("globe-tooltip");
  if (!tooltip) return;

  const parts = [
    trackInfo.callsign || trackInfo.icao,
    trackInfo.last_altitude_ft != null ? formatAltitude(trackInfo.last_altitude_ft) : t("common.altitudeUnknown"),
    trackInfo.last_ground_speed_kt != null ? `${Math.round(trackInfo.last_ground_speed_kt)} kt` : null,
    trackInfo.last_distance_km != null ? formatDistance(trackInfo.last_distance_km) : null,
    formatTime(trackInfo.last_observed_at),
  ].filter(Boolean);
  tooltip.textContent = parts.join(" / ");
  tooltip.hidden = false;
  positionTooltip(screenPosition);
}

function hideTooltip() {
  const tooltip = document.getElementById("globe-tooltip");
  if (tooltip) tooltip.hidden = true;
}

// --- wiring -----------------------------------------------------------------

function wirePicker() {
  const toggle = document.getElementById("aircraft-picker-toggle");
  const picker = document.getElementById("aircraft-picker");
  if (!toggle || !picker) return;

  toggle.addEventListener("click", () => {
    const willOpen = picker.hidden;
    picker.hidden = !willOpen;
    toggle.setAttribute("aria-expanded", String(willOpen));
  });
  document.addEventListener("click", (event) => {
    if (!picker.hidden && !picker.contains(event.target) && event.target !== toggle) {
      picker.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
    }
  });

  document.getElementById("aircraft-picker-all").addEventListener("click", () => {
    hiddenIcaos.clear();
    for (const checkbox of pickerCheckboxes.values()) checkbox.checked = true;
    applyVisibility();
  });
  document.getElementById("aircraft-picker-none").addEventListener("click", () => {
    for (const icao of knownAircraft.keys()) hiddenIcaos.add(icao);
    for (const checkbox of pickerCheckboxes.values()) checkbox.checked = false;
    applyVisibility();
  });

  document.getElementById("aircraft-refresh").addEventListener("click", () => refreshPickerFromRecent());
}

function wireFollowToggle() {
  const followButton = document.getElementById("follow-toggle");
  followButton.addEventListener("click", () => {
    if (viewer.trackedEntity) {
      viewer.trackedEntity = undefined;
      return;
    }
    if (!isolatedIcao) {
      showError(t("globe.followRequiresIsolate"));
      return;
    }
    const entity = aircraftEntities.get(isolatedIcao);
    if (entity) viewer.trackedEntity = entity;
  });
  viewer.trackedEntityChanged.addEventListener(() => {
    followButton.setAttribute("aria-pressed", String(Boolean(viewer.trackedEntity)));
  });
}

function wireIsolateExit() {
  document.getElementById("exit-isolate").addEventListener("click", () => exitIsolate());
}

// "6.0H" / "0.3H" -- short fixed-width form, rounded to one decimal via
// integer tenths (avoids float-rounding drift from the slider's 0.25h steps).
function formatHoursLabel(hours) {
  const tenths = Math.round(hours * 10);
  return `${(tenths / 10).toFixed(1)}H`;
}

function wireModeButtons() {
  const liveButton = document.querySelector("#mode-switch-group button[data-mode=\"live\"]");
  const slider = document.getElementById("history-hours-slider");
  const valueLabel = document.getElementById("history-hours-value");
  if (!liveButton || !slider || !valueLabel) return;

  valueLabel.textContent = formatHoursLabel(Number(slider.value));

  liveButton.addEventListener("click", () => {
    liveButton.setAttribute("aria-pressed", "true");
    enterLiveMode();
  });

  slider.addEventListener("input", () => {
    valueLabel.textContent = formatHoursLabel(Number(slider.value));
  });
  slider.addEventListener("change", () => {
    liveButton.setAttribute("aria-pressed", "false");
    enterHistoryMode(Number(slider.value));
  });
}

function wireFastModeToggle() {
  const button = document.getElementById("fast-mode-toggle");
  if (!button) return;
  button.addEventListener("click", () => {
    fastModeEnabled = !fastModeEnabled;
    button.setAttribute("aria-pressed", String(fastModeEnabled));
    sendFastMode();
  });
}

function wireSceneInteractions() {
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

  handler.setInputAction((movement) => {
    const picked = viewer.scene.pick(movement.position);
    if (!Cesium.defined(picked) || !picked.id) return;
    if (picked.id.icao) {
      openAircraftSidebar(picked.id.icao);
    } else if (picked.id.trackInfo) {
      openAircraftSidebar(picked.id.trackInfo.icao);
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  handler.setInputAction(
    (movement) => {
      const picked = viewer.scene.pick(movement.position);
      if (Cesium.defined(picked) && picked.id && picked.id.icao) {
        toggleIsolate(picked.id.icao);
      }
    },
    Cesium.ScreenSpaceEventType.LEFT_CLICK,
    Cesium.KeyboardEventModifier.SHIFT
  );

  handler.setInputAction((movement) => {
    const picked = viewer.scene.pick(movement.endPosition);
    if (Cesium.defined(picked) && picked.id && picked.id.icao) {
      showLiveTooltip(picked.id.icao, movement.endPosition);
    } else if (Cesium.defined(picked) && picked.id && picked.id.trackInfo) {
      showTrackTooltip(picked.id.trackInfo, movement.endPosition);
    } else {
      hideTooltip();
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  // Cesium's ScreenSpaceEventHandler only fires while the pointer stays
  // over its canvas -- without this, moving the mouse off the globe
  // entirely (onto the nav bar, description text, etc.) leaves a stale
  // tooltip on screen forever.
  viewer.scene.canvas.addEventListener("mouseleave", hideTooltip);
}

function sendFastMode() {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ fast: fastModeEnabled }));
  }
}

function connectBroadcast() {
  if (socket) return; // already connected
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${window.location.host}/ws/aircraft-positions`);
  socket.addEventListener("open", () => {
    if (fastModeEnabled) sendFastMode();
  });
  socket.addEventListener("message", (event) => {
    if (mode !== "live") return; // guards against a message in flight at the exact moment of switching modes
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.error("globe: failed to parse broadcast message", err);
      return;
    }

    const positions = (data && data.aircraft) || [];
    const seenIcaos = new Set();
    for (const position of positions) {
      if (!position.icao) continue;
      seenIcaos.add(position.icao);
      latestPositions.set(position.icao, position);
      ensurePickerEntry(position.icao, position.callsign);
      upsertEntity(position);

      const track = trackState.get(position.icao);
      if (track) pushLiveTrackPoint(track, position);
    }
    removeStaleEntities(seenIcaos);
    applyVisibility();
    autoFrameOnFirstData(positions);
    updateEmergencySquawkBanner(positions);
    checkTransitAlerts(positions);
    checkNewArrivals(positions);
    checkFavoriteArrivals(positions);
  });
  socket.addEventListener("error", () => showError(t("globe.liveConnectionError")));
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config", err);
    config = { version: null, git_revision: null, altitude_bands: [] };
  }
  applyStaticTranslations();
  renderVersion(config);
  setNationalityBlocks(config.nationality_blocks);
  registerServiceWorker();
  setAltitudeBands(config.altitude_bands);
  renderAltitudeLegend(document.getElementById("altitude-legend"), config.altitude_bands);
  ui.setTimezone(config.display_timezone || "UTC");

  try {
    viewer = createViewer();
  } catch (err) {
    console.error("Cesium viewer init failed", err);
    showError(t("globe.initFailed", { detail: err && err.message ? err.message : err }));
    return;
  }

  hideError();
  await loadFavorites();
  await refreshPickerFromRecent();
  wirePicker();
  wireFollowToggle();
  wireIsolateExit();
  wireModeButtons();
  wireFastModeToggle();
  wireSceneInteractions();
  connectBroadcast();
}

main().catch((err) => {
  console.error("globe page failed to start", err);
});
