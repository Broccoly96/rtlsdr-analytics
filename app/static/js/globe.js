// globe.js -- entrypoint for globe.html: a 3D scene (CesiumJS) showing every
// currently-live aircraft's position over the shared broadcast WS
// /ws/aircraft-positions (Milestone Z; app/api/routers/aircraft_positions.py
// -- one background readsb poll fanned out to every connected client,
// replacing "one poll per selected aircraft" now that the default view
// shows everything at once). Dots are color-coded by altitude band, same
// bands/colors as map.js's 2D track coloring. Shift+click isolates one
// aircraft: hides every other dot and draws its historical track (GET
// /api/aircraft/{icao}/positions) plus a live-extending polyline fed by
// the same broadcast stream (no separate per-aircraft WS needed here --
// that connection is still used by aircraftinfo.js's sidebar for its
// deeper tar1090-parity fields). Ground imagery (ArcGIS World Imagery) is
// fetched continuously by the browser while this page is open -- see
// README Security & Privacy. Nothing here is persisted.

import { api } from "./api.js";
import { openAircraftSidebar } from "./aircraftinfo.js";
import { formatAltitude } from "./units.js";

const FT_TO_M = 0.3048;
const DEFAULT_HOURS = 6;
const UNKNOWN_ALTITUDE_COLOR = "#8fa3bd"; // matches style.css's --text-muted

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
  if (altitudeFt == null) return UNKNOWN_ALTITUDE_COLOR;
  for (const band of altitudeBands) {
    if (altitudeFt <= band.max) return band.color;
  }
  return UNKNOWN_ALTITUDE_COLOR;
}

function segmentToCartesians(segment) {
  return Cesium.Cartesian3.fromDegreesArrayHeights(
    segment.flatMap((p) => [p.lon, p.lat, (p.altitude_ft || 0) * FT_TO_M])
  );
}

// --- state ----------------------------------------------------------------

let viewer = null;
let socket = null;
const aircraftEntities = new Map(); // icao -> Cesium.Entity (point + label)
const latestPositions = new Map(); // icao -> latest broadcast entry
const hiddenIcaos = new Set(); // user-unchecked via the picker
const knownAircraft = new Map(); // icao -> callsign|null, for the picker list
const pickerCheckboxes = new Map();
const pickerLabels = new Map();

let isolatedIcao = null;
let isolateHistoryEntities = [];
let isolateLiveEntity = null;
let isolateLiveTrackPositions = [];

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
    entity.show = isolatedIcao ? icao === isolatedIcao : !hiddenIcaos.has(icao);
  }
}

function upsertEntity(position) {
  const { icao, callsign, lat, lon, altitude_ft: altitudeFt } = position;
  const color = Cesium.Color.fromCssColorString(colorForAltitude(altitudeFt));
  const cartesian = Cesium.Cartesian3.fromDegrees(lon, lat, (altitudeFt || 0) * FT_TO_M);

  let entity = aircraftEntities.get(icao);
  if (!entity) {
    entity = viewer.entities.add({
      position: cartesian,
      point: { pixelSize: 8, color, outlineColor: Cesium.Color.BLACK, outlineWidth: 1 },
      label: {
        text: callsign || icao,
        font: "12px sans-serif",
        pixelOffset: new Cesium.Cartesian2(0, -14),
        fillColor: Cesium.Color.WHITE,
      },
    });
    entity.icao = icao;
    aircraftEntities.set(icao, entity);
  } else {
    entity.position = cartesian;
    entity.point.color = color;
    entity.label.text = callsign || icao;
  }
}

function removeStaleEntities(seenIcaos) {
  for (const icao of Array.from(aircraftEntities.keys())) {
    if (seenIcaos.has(icao)) continue;
    viewer.entities.remove(aircraftEntities.get(icao));
    aircraftEntities.delete(icao);
    latestPositions.delete(icao);
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
  for (const entity of isolateHistoryEntities) viewer.entities.remove(entity);
  isolateHistoryEntities = [];
  if (isolateLiveEntity) {
    viewer.entities.remove(isolateLiveEntity);
    isolateLiveEntity = null;
  }
  isolateLiveTrackPositions = [];
  document.getElementById("exit-isolate").hidden = true;
  if (viewer.trackedEntity) viewer.trackedEntity = undefined;
  applyVisibility();
}

function enterIsolate(icao) {
  isolatedIcao = icao;
  isolateLiveTrackPositions = [];
  applyVisibility();
  document.getElementById("exit-isolate").hidden = false;

  api
    .getAircraftPositions(icao, DEFAULT_HOURS)
    .then((positions) => {
      if (isolatedIcao !== icao) return; // exited/switched before this resolved
      for (const segment of positions.segments) {
        if (segment.length < 2) continue;
        isolateHistoryEntities.push(
          viewer.entities.add({
            polyline: { positions: segmentToCartesians(segment), width: 3, material: Cesium.Color.CYAN },
          })
        );
      }
    })
    .catch((err) => {
      console.error("aircraft positions fetch failed", err);
      showError("軌跡データの取得に失敗しました。ライブ更新は続行します。");
    });

  isolateLiveEntity = viewer.entities.add({
    polyline: {
      positions: new Cesium.CallbackProperty(() => isolateLiveTrackPositions, false),
      width: 3,
      material: Cesium.Color.YELLOW,
    },
  });

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

// --- hover tooltip ----------------------------------------------------------

function showTooltip(icao, screenPosition) {
  const tooltip = document.getElementById("globe-tooltip");
  const position = latestPositions.get(icao);
  if (!tooltip || !position) return;

  const canvasRect = viewer.scene.canvas.getBoundingClientRect();
  const parent = tooltip.offsetParent;
  const parentRect = parent ? parent.getBoundingClientRect() : canvasRect;
  tooltip.style.left = `${canvasRect.left - parentRect.left + screenPosition.x + 12}px`;
  tooltip.style.top = `${canvasRect.top - parentRect.top + screenPosition.y + 12}px`;

  const parts = [
    position.callsign || icao,
    position.altitude_ft != null ? formatAltitude(position.altitude_ft) : null,
    position.ground_speed_kt != null ? `${Math.round(position.ground_speed_kt)} kt` : null,
  ].filter(Boolean);
  tooltip.textContent = parts.join(" / ");
  tooltip.hidden = false;
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
      showError("カメラ自動追従には、先に機体をShift+クリックしてください。");
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

function wireSceneInteractions() {
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

  handler.setInputAction((movement) => {
    const picked = viewer.scene.pick(movement.position);
    if (Cesium.defined(picked) && picked.id && picked.id.icao) {
      openAircraftSidebar(picked.id.icao);
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
      showTooltip(picked.id.icao, movement.endPosition);
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

function connectBroadcast() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${window.location.host}/ws/aircraft-positions`);
  socket.addEventListener("message", (event) => {
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

      if (position.icao === isolatedIcao) {
        isolateLiveTrackPositions.push(
          Cesium.Cartesian3.fromDegrees(position.lon, position.lat, (position.altitude_ft || 0) * FT_TO_M)
        );
      }
    }
    removeStaleEntities(seenIcaos);
    applyVisibility();
    autoFrameOnFirstData(positions);
  });
  socket.addEventListener("error", () => showError("ライブ接続エラー"));
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config", err);
    config = { version: null, git_revision: null, altitude_bands: [] };
  }
  renderVersion(config);
  setAltitudeBands(config.altitude_bands);

  try {
    viewer = createViewer();
  } catch (err) {
    console.error("Cesium viewer init failed", err);
    showError(
      `3D表示の初期化に失敗しました: ${err && err.message ? err.message : err}(WebGLが利用できない環境の可能性があります)`
    );
    return;
  }

  hideError();
  await refreshPickerFromRecent();
  wirePicker();
  wireFollowToggle();
  wireIsolateExit();
  wireSceneInteractions();
  connectBroadcast();
}

main().catch((err) => {
  console.error("globe page failed to start", err);
});
