// map.js -- MapLibre track rendering. Any style/tile load failure is shown
// only inside the map panel; the rest of the dashboard (chart, rankings)
// keeps working regardless (PLAN.md D-3/D-4).

// maplibre-gl@6's ESM bundle has no default export (only named exports:
// Map, Popup, Marker, ...) -- a default import silently binds to
// `undefined` at the language level, but since a *static* default import
// of a non-existent binding is a module-linking SyntaxError, it actually
// fails the entire import graph (this file, and anything that imports it)
// before any code runs at all. A namespace import matches what the module
// actually exports.
//
// Vendored locally under vendor/maplibre-gl/ (maplibre-gl.mjs +
// maplibre-gl-shared.mjs + maplibre-gl-worker.mjs, all relatively
// referenced from this one entrypoint) rather than fetched from a CDN, so
// the map doesn't depend on the *client browser's* network being able to
// reach unpkg.com -- only on it reaching this app's own origin, which it
// obviously already can.
import * as maplibregl from "./vendor/maplibre-gl/maplibre-gl.mjs";

import { api } from "./api.js";
import { formatDistance, formatAltitude } from "./units.js";
import { openAircraftSidebar } from "./aircraftinfo.js";
import { registerAircraftIcons, iconIdFor, shapeForCategory, UNKNOWN_BAND_KEY } from "./aircraft-icons.js";
import { ui } from "./ui.js";
import { t } from "./i18n.js";

const formatTime = ui.formatTime;

// Populated from GET /api/config (see setAltitudeBands below) -- Python
// (app/domain/bands.py) is the single source of truth so this can't drift
// from the server-side band definitions used for grouping/filtering.
let altitudeBands = [];
let rawAltitudeBands = []; // kept alongside altitudeBands for aircraft-icons.js (needs .key, not just .max/.color)
const UNKNOWN_ALTITUDE_COLOR = "#8fa3bd";
// Cool-to-warm density ramp for the heatmap layer, matching this app's
// existing color tokens (style.css's --accent-2/--accent/--success/--warning/--danger).
const HEATMAP_COLOR_RAMP = ["#60a5fa", "#22d3ee", "#34d399", "#fbbf24", "#fb7185"];

export function setTimezone(tz) {
  ui.setTimezone(tz);
}

// `config.altitude_bands` items have `max_ft` (null for the top,
// unbounded band); normalized here to `max: Infinity` for the same
// simple "first band whose max covers this altitude" scan colorForAltitude
// already did against the old hard-coded array.
export function setAltitudeBands(bands) {
  rawAltitudeBands = bands || [];
  altitudeBands = rawAltitudeBands.map((b) => ({
    key: b.key,
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

function bandKeyForAltitude(altitudeFt) {
  if (altitudeFt == null) return UNKNOWN_BAND_KEY;
  for (const band of altitudeBands) {
    if (altitudeFt <= band.max) return band.key;
  }
  return UNKNOWN_BAND_KEY;
}

function showMapError(message) {
  const errorEl = document.getElementById("map-error");
  if (!errorEl) return;
  errorEl.textContent = message;
  errorEl.hidden = false;
}

function hideMapError() {
  const errorEl = document.getElementById("map-error");
  if (errorEl) errorEl.hidden = true;
}

// MapLibre GL JS requires WebGL; some environments (remote desktops/VMs
// without GPU passthrough, WebGL disabled via browser flags, very old
// browsers) don't have it. Detecting this up front turns an otherwise
// silent blank map into an immediate, specific, on-page explanation.
function isWebGLAvailable() {
  try {
    const canvas = document.createElement("canvas");
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext("webgl2") || canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}

function describeError(err) {
  if (err && typeof err.message === "string" && err.message) return err.message;
  if (typeof err === "string") return err;
  return t("map.unknownError");
}

// Walks a segment's [lon, lat, altitude_ft] points and groups consecutive
// points sharing the same altitude-band color into runs, carrying the
// boundary point into both runs so the line stays visually connected
// across a color change (mirrors globe.js's equivalent split for its
// Cesium polylines, which have the same "one material per entity"
// constraint MapLibre's "one color per feature" paint expression has).
function splitCoordinatesByBand(coordinates) {
  const runs = [];
  let currentColor = null;
  let currentCoords = [];
  for (const point of coordinates) {
    const color = colorForAltitude(point[2]);
    if (color !== currentColor) {
      if (currentCoords.length > 1) runs.push({ coordinates: currentCoords, color: currentColor });
      currentCoords = currentCoords.length ? [currentCoords[currentCoords.length - 1]] : [];
      currentColor = color;
    }
    currentCoords.push(point);
  }
  if (currentCoords.length > 1) runs.push({ coordinates: currentCoords, color: currentColor });
  return runs;
}

function tracksToLineFeatures(tracksGeoJSON) {
  // Split each aircraft's MultiLineString into individual LineString
  // features, further split by altitude-band run so the line's color
  // changes along its length to match the altitude at each point, rather
  // than one color for the whole track computed once from a single
  // (e.g. last-observed) altitude value.
  const features = [];
  for (const feature of tracksGeoJSON.features) {
    const {
      icao,
      callsign,
      last_altitude_ft,
      last_ground_speed_kt,
      last_distance_km,
      last_observed_at,
    } = feature.properties;
    for (const segment of feature.geometry.coordinates) {
      for (const run of splitCoordinatesByBand(segment)) {
        features.push({
          type: "Feature",
          geometry: { type: "LineString", coordinates: run.coordinates },
          properties: {
            icao,
            callsign,
            last_altitude_ft,
            last_ground_speed_kt,
            last_distance_km,
            last_observed_at,
            color: run.color,
          },
        });
      }
    }
  }
  return { type: "FeatureCollection", features };
}

// Historical fetch window for each live-tracked aircraft's trailing track
// (mirrors globe.js's DEFAULT_HOURS for the same purpose).
const LIVE_TRACK_HISTORY_HOURS = 6;

function cellsToHeatmapFeatures(cells) {
  return {
    type: "FeatureCollection",
    features: (cells || []).map((cell) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [cell.lon, cell.lat] },
      properties: { count: cell.count },
    })),
  };
}

const LOAD_TIMEOUT_MS = 10000;

export function createTrackMap({ containerId, styleUrl }) {
  let map;
  let popup;
  let ready = false;
  let selectedIcao = null;
  let iconsReadyPromise = Promise.resolve();
  let liveFeatureShiftClickHandler = null;
  // icao -> { historyFeatures: LineString[], liveRuns: [{color, coordinates}] }
  // -- every live-tracked aircraft accumulates here regardless of picker/
  // isolate visibility (mirrors globe.js's trackState); renderLiveTracks()
  // below is what actually filters by visibility.
  const liveTrackState = new Map();
  let visibleLiveIcaos = new Set();

  const noop = {
    setTracks: () => {},
    resize: () => {},
    setHeatmap: () => {},
    setHeatmapVisible: () => {},
    setLivePositions: () => {},
    clearLivePositions: () => {},
    setLiveFeatureShiftClickHandler: () => {},
    updateLiveTracks: () => {},
    pruneLiveTracks: () => {},
    clearLiveTracks: () => {},
  };

  if (!isWebGLAvailable()) {
    showMapError(t("map.webglUnavailable"));
    return noop;
  }

  try {
    map = new maplibregl.Map({
      container: containerId,
      style: styleUrl,
      center: [139.0, 35.0],
      zoom: 5,
      attributionControl: true,
      // Renders CJK glyphs locally instead of requiring a font-glyph tile
      // fetch per character, and keeps Japanese labels legible.
      localIdeographFontFamily: "'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif",
    });
  } catch (err) {
    console.error("map init failed", err);
    showMapError(t("map.initFailed", { detail: describeError(err) }));
    return noop;
  }

  // If `load` never fires (e.g. the style URL or one of its referenced
  // tile/sprite/glyph hosts is unreachable from this browser but was
  // reachable from wherever the app was tested from), the map would
  // otherwise sit silently blank forever with no error shown at all.
  const loadTimeoutId = setTimeout(() => {
    if (!ready) {
      showMapError(t("map.loadTimeout", { seconds: LOAD_TIMEOUT_MS / 1000, styleUrl }));
    }
  }, LOAD_TIMEOUT_MS);

  map.on("error", (event) => {
    const detail = describeError(event && event.error);
    console.error("map error", event && event.error);
    showMapError(t("map.dataFetchFailed", { detail }));
  });

  map.on("load", () => {
    clearTimeout(loadTimeoutId);
    hideMapError();
    ready = true;

    map.addSource("tracks", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: "tracks-line",
      type: "line",
      source: "tracks",
      paint: {
        "line-color": ["get", "color"],
        // Clicking a track sets a thicker line-width for its icao only
        // (PLAN.md D-3 "選択中の航跡を太く表示する") -- see the click
        // handler below, which updates this via setPaintProperty.
        "line-width": 2,
        "line-opacity": 0.75,
      },
    });

    map.addSource("heatmap", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: "heatmap-layer",
      type: "heatmap",
      source: "heatmap",
      layout: { visibility: "none" },
      paint: {
        "heatmap-weight": ["interpolate", ["linear"], ["get", "count"], 0, 0, 50, 1],
        "heatmap-intensity": 1,
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(0,0,0,0)",
          0.2,
          HEATMAP_COLOR_RAMP[0],
          0.4,
          HEATMAP_COLOR_RAMP[1],
          0.6,
          HEATMAP_COLOR_RAMP[2],
          0.8,
          HEATMAP_COLOR_RAMP[3],
          1,
          HEATMAP_COLOR_RAMP[4],
        ],
        "heatmap-radius": 20,
        "heatmap-opacity": 0.8,
      },
    });

    map.addSource("live-positions", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: "live-positions-layer",
      type: "symbol",
      source: "live-positions",
      layout: {
        "icon-image": ["get", "icon"],
        "icon-rotate": ["get", "track_deg"],
        "icon-rotation-alignment": "map",
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
        "text-field": ["get", "callsign"],
        // Must be a font stack the map style's own glyphs endpoint
        // actually hosts -- this app doesn't control MAP_STYLE_URL's
        // font server, so an unavailable font silently fails to fetch
        // (404) rather than throwing; "Noto Sans Regular" is what both
        // this app's default style (OpenFreeMap/positron) and its other
        // text layers already use.
        "text-font": ["Noto Sans Regular"],
        "text-size": 10,
        "text-offset": [0, 1.3],
        "text-anchor": "top",
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": "#e8f0fa", // matches style.css's --text
        "text-halo-color": "#08111f", // matches style.css's --bg
        "text-halo-width": 1.5,
      },
    });
    // Icon images must be registered before any feature referencing them
    // is set on the source, or MapLibre silently skips rendering that
    // icon (logs a warning, doesn't throw) -- setLivePositions() below
    // awaits this same promise before its first setData() call.
    iconsReadyPromise = registerAircraftIcons(map, rawAltitudeBands).catch((err) => {
      console.error("aircraft icon registration failed", err);
    });

    popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });

    function describeFeature(props) {
      const title = document.createElement("strong");
      title.textContent = props.callsign || props.icao;

      const altitude =
        props.last_altitude_ft != null ? formatAltitude(props.last_altitude_ft) : t("common.altitudeUnknown");
      const speed =
        props.last_ground_speed_kt != null ? `${Math.round(props.last_ground_speed_kt)} kt` : null;
      const distance = props.last_distance_km != null ? formatDistance(props.last_distance_km) : null;

      const line1 = document.createElement("div");
      line1.textContent = [altitude, speed].filter(Boolean).join(" / ");
      const line2 = document.createElement("div");
      line2.textContent = [distance, formatTime(props.last_observed_at)].filter(Boolean).join(" / ");

      const content = document.createElement("div");
      content.append(title, line1, line2);
      return content;
    }

    map.on("mousemove", "tracks-line", (event) => {
      map.getCanvas().style.cursor = "pointer";
      const feature = event.features && event.features[0];
      if (!feature) return;
      popup.setLngLat(event.lngLat).setDOMContent(describeFeature(feature.properties)).addTo(map);
    });

    map.on("mouseleave", "tracks-line", () => {
      map.getCanvas().style.cursor = "";
      if (popup) popup.remove();
    });

    map.on("click", "tracks-line", (event) => {
      const feature = event.features && event.features[0];
      if (!feature) return;
      const icao = feature.properties.icao;
      selectedIcao = selectedIcao === icao ? null : icao;
      map.setPaintProperty("tracks-line", "line-width", [
        "case",
        ["==", ["get", "icao"], selectedIcao || ""],
        4,
        2,
      ]);
      openAircraftSidebar(icao);
    });

    function describeLiveFeature(props) {
      const title = document.createElement("strong");
      title.textContent = props.callsign || props.icao;

      const altitude = props.altitude_ft != null ? formatAltitude(props.altitude_ft) : t("common.altitudeUnknown");
      const speed = props.ground_speed_kt != null ? `${Math.round(props.ground_speed_kt)} kt` : null;

      const line = document.createElement("div");
      line.textContent = [altitude, speed].filter(Boolean).join(" / ");

      const content = document.createElement("div");
      content.append(title, line);
      return content;
    }

    map.on("mousemove", "live-positions-layer", (event) => {
      map.getCanvas().style.cursor = "pointer";
      const feature = event.features && event.features[0];
      if (!feature) return;
      popup.setLngLat(event.lngLat).setDOMContent(describeLiveFeature(feature.properties)).addTo(map);
    });

    map.on("mouseleave", "live-positions-layer", () => {
      map.getCanvas().style.cursor = "";
      if (popup) popup.remove();
    });

    map.on("click", "live-positions-layer", (event) => {
      const feature = event.features && event.features[0];
      if (!feature) return;
      const icao = feature.properties.icao;
      // Shift+click isolates one aircraft (same convention as the 3D
      // globe's live view) -- the caller (fullmap.js) owns which
      // aircraft are currently shown/hidden, so this just notifies it
      // rather than filtering anything here.
      if (event.originalEvent && event.originalEvent.shiftKey && liveFeatureShiftClickHandler) {
        liveFeatureShiftClickHandler(icao);
        return;
      }
      openAircraftSidebar(icao);
    });
  });

  function setTracks(tracksGeoJSON) {
    if (!ready) return;
    const source = map.getSource("tracks");
    if (source) source.setData(tracksToLineFeatures(tracksGeoJSON));
  }

  // --- live-mode per-aircraft tracks (reuses the "tracks" source/layer
  // history mode uses -- only one mode is ever active at a time) ---------

  function liveLineFeature(coordinates, color, icao) {
    return {
      type: "Feature",
      geometry: { type: "LineString", coordinates },
      properties: { icao, color },
    };
  }

  function renderLiveTracks() {
    if (!ready) return;
    const source = map.getSource("tracks");
    if (!source) return;
    const features = [];
    for (const [icao, state] of liveTrackState) {
      if (!visibleLiveIcaos.has(icao)) continue;
      features.push(...state.historyFeatures);
      for (const run of state.liveRuns) {
        if (run.coordinates.length > 1) features.push(liveLineFeature(run.coordinates, run.color, icao));
      }
    }
    source.setData({ type: "FeatureCollection", features });
  }

  // One-time (per icao) historical fetch for a live-tracked aircraft's
  // trailing track, band-split same as history mode's tracksToLineFeatures.
  function ensureLiveTrackHistory(icao) {
    if (liveTrackState.has(icao)) return;
    liveTrackState.set(icao, { historyFeatures: [], liveRuns: [] });
    api
      .getAircraftPositions(icao, LIVE_TRACK_HISTORY_HOURS)
      .then((positions) => {
        const state = liveTrackState.get(icao);
        if (!state) return; // aircraft went stale before this resolved
        for (const segment of positions.segments) {
          if (segment.length < 2) continue;
          const coords = segment.map((p) => [p.lon, p.lat, p.altitude_ft]);
          for (const run of splitCoordinatesByBand(coords)) {
            state.historyFeatures.push(liveLineFeature(run.coordinates, run.color, icao));
          }
        }
        renderLiveTracks();
      })
      .catch((err) => {
        console.error("live track history fetch failed", err);
      });
  }

  // Appends one broadcast tick's position to the aircraft's live-extending
  // track, starting a new band-run (see splitCoordinatesByBand) when the
  // altitude band has changed since the last point.
  function pushLiveTrackPoint(icao, position) {
    const state = liveTrackState.get(icao);
    if (!state) return;
    const coord = [position.lon, position.lat, position.altitude_ft];
    const color = colorForAltitude(position.altitude_ft);
    const currentRun = state.liveRuns[state.liveRuns.length - 1];
    if (currentRun && currentRun.color === color) {
      currentRun.coordinates.push(coord);
      return;
    }
    const coordinates = currentRun
      ? [currentRun.coordinates[currentRun.coordinates.length - 1], coord]
      : [coord];
    state.liveRuns.push({ color, coordinates });
  }

  // Accumulates every broadcast tick's positions into per-aircraft track
  // state (does not itself trigger a render -- setLivePositions() does,
  // right after this is called each tick, so the two don't double-render).
  function updateLiveTracks(positions) {
    if (!ready) return;
    for (const position of positions || []) {
      if (!position.icao || position.lat == null || position.lon == null) continue;
      ensureLiveTrackHistory(position.icao);
      pushLiveTrackPoint(position.icao, position);
    }
  }

  // Drops state for aircraft that have left the broadcast entirely (not
  // just hidden via the picker) -- called with every icao seen in the
  // latest raw tick, unfiltered by visibility.
  function pruneLiveTracks(seenIcaos) {
    let changed = false;
    for (const icao of Array.from(liveTrackState.keys())) {
      if (!seenIcaos.has(icao)) {
        liveTrackState.delete(icao);
        changed = true;
      }
    }
    if (changed) renderLiveTracks();
  }

  function clearLiveTracks() {
    liveTrackState.clear();
    visibleLiveIcaos = new Set();
    if (ready) {
      const source = map.getSource("tracks");
      if (source) source.setData({ type: "FeatureCollection", features: [] });
    }
  }

  function setHeatmap(cells) {
    if (!ready) return;
    const source = map.getSource("heatmap");
    if (source) source.setData(cellsToHeatmapFeatures(cells));
  }

  function setHeatmapVisible(visible) {
    if (!ready) return;
    map.setLayoutProperty("heatmap-layer", "visibility", visible ? "visible" : "none");
  }

  async function setLivePositions(positions) {
    if (!ready) return;
    await iconsReadyPromise;
    const source = map.getSource("live-positions");
    if (!source) return;
    source.setData({
      type: "FeatureCollection",
      features: (positions || [])
        .filter((p) => p.lat != null && p.lon != null)
        .map((p) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [p.lon, p.lat] },
          properties: {
            icao: p.icao,
            callsign: p.callsign,
            altitude_ft: p.altitude_ft,
            ground_speed_kt: p.ground_speed_kt,
            track_deg: p.track_deg || 0,
            icon: iconIdFor(shapeForCategory(p.category), bandKeyForAltitude(p.altitude_ft)),
          },
        })),
    });
    // `positions` here is already filtered to what should be visible
    // (fullmap.js's applyLivePositions()) -- track *accumulation* happens
    // for every aircraft regardless (updateLiveTracks, called separately
    // with the unfiltered tick), so this only controls which of those
    // already-accumulated tracks renderLiveTracks() draws.
    visibleLiveIcaos = new Set((positions || []).map((p) => p.icao).filter(Boolean));
    renderLiveTracks();
  }

  function clearLivePositions() {
    if (!ready) return;
    const source = map.getSource("live-positions");
    if (source) source.setData({ type: "FeatureCollection", features: [] });
  }

  function setLiveFeatureShiftClickHandler(fn) {
    liveFeatureShiftClickHandler = fn;
  }

  function resize() {
    if (map) map.resize();
  }

  return {
    setTracks,
    resize,
    setHeatmap,
    setHeatmapVisible,
    setLivePositions,
    clearLivePositions,
    setLiveFeatureShiftClickHandler,
    updateLiveTracks,
    pruneLiveTracks,
    clearLiveTracks,
  };
}

export async function refreshTracks(mapController, hours) {
  try {
    const tracksGeoJSON = await api.getTracks(hours);
    mapController.setTracks(tracksGeoJSON);
  } catch (err) {
    console.error("tracks refresh failed", err);
    showMapError(t("map.tracksFetchFailed"));
  }
}
