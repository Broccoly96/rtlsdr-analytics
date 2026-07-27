// map.js -- MapLibre track rendering. Any style/tile load failure is shown
// only inside the map panel; the rest of the dashboard (chart, rankings)
// keeps working regardless (PLAN.md D-3/D-4).

import maplibregl from "https://unpkg.com/maplibre-gl@6.0.0/dist/maplibre-gl.mjs";

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

export function createTrackMap({ containerId, styleUrl }) {
  let map;
  let popup;
  let ready = false;
  let selectedIcao = null;

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
    showMapError("地図の初期化に失敗しました。グラフ・ランキングは利用できます。");
    return { setTracks: () => {}, resize: () => {} };
  }

  map.on("error", (event) => {
    console.error("map error", event && event.error);
    showMapError("地図データの取得に失敗しました。グラフ・ランキングは利用できます。");
  });

  map.on("load", () => {
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
