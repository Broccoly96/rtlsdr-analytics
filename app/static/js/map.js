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

const ALTITUDE_BANDS = [
  { max: 0, color: "#fbbf24" }, // ground / very low
  { max: 10000, color: "#34d399" },
  { max: 25000, color: "#22d3ee" },
  { max: 35000, color: "#60a5fa" },
  { max: Infinity, color: "#c084fc" },
];
const UNKNOWN_ALTITUDE_COLOR = "#8fa3bd";

let displayTimezone = "UTC";

export function setTimezone(tz) {
  displayTimezone = tz;
}

function formatTime(isoString) {
  if (!isoString) return "--";
  try {
    return new Date(isoString).toLocaleString("ja-JP", { timeZone: displayTimezone, hour12: false });
  } catch {
    return isoString;
  }
}

function colorForAltitude(altitudeFt) {
  if (altitudeFt == null) return UNKNOWN_ALTITUDE_COLOR;
  for (const band of ALTITUDE_BANDS) {
    if (altitudeFt <= band.max) return band.color;
  }
  return UNKNOWN_ALTITUDE_COLOR;
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
  return "詳細不明のエラー";
}

function tracksToLineFeatures(tracksGeoJSON) {
  // Split each aircraft's MultiLineString into individual LineString
  // features so each segment can be colored via a simple data-driven
  // paint expression (one color per feature, computed once here).
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
    const color = colorForAltitude(last_altitude_ft);
    for (const segment of feature.geometry.coordinates) {
      features.push({
        type: "Feature",
        geometry: { type: "LineString", coordinates: segment },
        properties: {
          icao,
          callsign,
          last_altitude_ft,
          last_ground_speed_kt,
          last_distance_km,
          last_observed_at,
          color,
        },
      });
    }
  }
  return { type: "FeatureCollection", features };
}

const LOAD_TIMEOUT_MS = 10000;

export function createTrackMap({ containerId, styleUrl }) {
  let map;
  let popup;
  let ready = false;
  let selectedIcao = null;

  if (!isWebGLAvailable()) {
    showMapError(
      "このブラウザ/環境ではWebGLが利用できないため地図を表示できません(グラフ・ランキングは利用できます)。リモートデスクトップ/VM環境やWebGL無効化設定が原因のことがあります。"
    );
    return { setTracks: () => {}, resize: () => {} };
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
    showMapError(`地図の初期化に失敗しました: ${describeError(err)}(グラフ・ランキングは利用できます)`);
    return { setTracks: () => {}, resize: () => {} };
  }

  // If `load` never fires (e.g. the style URL or one of its referenced
  // tile/sprite/glyph hosts is unreachable from this browser but was
  // reachable from wherever the app was tested from), the map would
  // otherwise sit silently blank forever with no error shown at all.
  const loadTimeoutId = setTimeout(() => {
    if (!ready) {
      showMapError(
        `地図の読み込みがタイムアウトしました(${LOAD_TIMEOUT_MS / 1000}秒)。スタイルURL(${styleUrl})への通信を確認してください。グラフ・ランキングは利用できます。`
      );
    }
  }, LOAD_TIMEOUT_MS);

  map.on("error", (event) => {
    const detail = describeError(event && event.error);
    console.error("map error", event && event.error);
    showMapError(`地図データの取得に失敗しました: ${detail}(グラフ・ランキングは利用できます)`);
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

    popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });

    function describeFeature(props) {
      const title = document.createElement("strong");
      title.textContent = props.callsign || props.icao;

      const altitude =
        props.last_altitude_ft != null ? `${Math.round(props.last_altitude_ft)} ft` : "高度不明";
      const speed =
        props.last_ground_speed_kt != null ? `${Math.round(props.last_ground_speed_kt)} kt` : null;
      const distance =
        props.last_distance_km != null ? `${props.last_distance_km.toFixed(1)} km` : null;

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
    });
  });

  function setTracks(tracksGeoJSON) {
    if (!ready) return;
    const source = map.getSource("tracks");
    if (source) source.setData(tracksToLineFeatures(tracksGeoJSON));
  }

  function resize() {
    if (map) map.resize();
  }

  return { setTracks, resize };
}

export async function refreshTracks(mapController, hours) {
  try {
    const tracksGeoJSON = await api.getTracks(hours);
    mapController.setTracks(tracksGeoJSON);
  } catch (err) {
    console.error("tracks refresh failed", err);
    showMapError("航跡データの取得に失敗しました。");
  }
}
