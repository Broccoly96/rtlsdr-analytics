// globe.js -- entrypoint for globe.html: a 3D scene (CesiumJS) showing one
// selected aircraft's historical track (GET /api/aircraft/{icao}/positions)
// plus a live-updating current-position marker over WS /ws/aircraft/{icao}
// (shared with the aircraft detail sidebar -- see app/api/routers/
// aircraft_live.py). Ground imagery (ArcGIS World Imagery) is fetched
// continuously by the browser while this page is open, not just on click
// -- see README Security & Privacy. Nothing here is persisted.

import { api } from "./api.js";

const FT_TO_M = 0.3048;
const DEFAULT_HOURS = 6;

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

async function populateAircraftSelect(select) {
  try {
    const recent = await api.getRecentAircraft(24, 50);
    const previousValue = select.value;
    select.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "機体を選択…";
    select.appendChild(placeholder);
    for (const row of recent) {
      const option = document.createElement("option");
      option.value = row.icao;
      option.textContent = row.callsign ? `${row.callsign} (${row.icao})` : row.icao;
      select.appendChild(option);
    }
    if (previousValue) select.value = previousValue;
  } catch (err) {
    console.error("recent aircraft fetch failed", err);
  }
}

let liveEntity = null;
let socket = null;

function clearSelection(viewer) {
  if (socket) {
    socket.close();
    socket = null;
  }
  viewer.entities.removeAll();
  liveEntity = null;
}

function segmentToCartesians(segment) {
  return Cesium.Cartesian3.fromDegreesArrayHeights(
    segment.flatMap((p) => [p.lon, p.lat, (p.altitude_ft || 0) * FT_TO_M])
  );
}

async function selectAircraft(viewer, icao) {
  hideError();
  clearSelection(viewer);
  if (!icao) return;

  let lastPoint = null;
  try {
    const positions = await api.getAircraftPositions(icao, DEFAULT_HOURS);
    for (const segment of positions.segments) {
      if (segment.length < 2) continue;
      viewer.entities.add({
        polyline: {
          positions: segmentToCartesians(segment),
          width: 3,
          material: Cesium.Color.CYAN,
        },
      });
    }
    const lastSegment = positions.segments[positions.segments.length - 1];
    lastPoint = lastSegment && lastSegment[lastSegment.length - 1];
  } catch (err) {
    console.error("aircraft positions fetch failed", err);
    showError("軌跡データの取得に失敗しました。ライブ更新は続行します。");
  }

  liveEntity = viewer.entities.add({
    point: {
      pixelSize: 10,
      color: Cesium.Color.YELLOW,
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 2,
    },
    label: {
      text: icao,
      font: "14px sans-serif",
      pixelOffset: new Cesium.Cartesian2(0, -16),
      fillColor: Cesium.Color.WHITE,
    },
  });

  if (lastPoint) {
    liveEntity.position = Cesium.Cartesian3.fromDegrees(
      lastPoint.lon,
      lastPoint.lat,
      (lastPoint.altitude_ft || 0) * FT_TO_M
    );
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        lastPoint.lon,
        lastPoint.lat,
        (lastPoint.altitude_ft || 0) * FT_TO_M + 20000
      ),
    });
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(
    `${protocol}//${window.location.host}/ws/aircraft/${encodeURIComponent(icao)}`
  );
  socket.addEventListener("message", (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.error("globe: failed to parse live message", err);
      return;
    }
    if (!liveEntity || !data.received || data.lat == null || data.lon == null) return;
    const altitudeFt = data.alt_geom != null ? data.alt_geom : data.alt_baro || 0;
    liveEntity.position = Cesium.Cartesian3.fromDegrees(data.lon, data.lat, altitudeFt * FT_TO_M);
  });
  socket.addEventListener("error", () => showError("ライブ接続エラー"));
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config", err);
    config = { version: null, git_revision: null };
  }
  renderVersion(config);

  let viewer;
  try {
    viewer = createViewer();
  } catch (err) {
    console.error("Cesium viewer init failed", err);
    showError(
      `3D表示の初期化に失敗しました: ${err && err.message ? err.message : err}(WebGLが利用できない環境の可能性があります)`
    );
    return;
  }

  const select = document.getElementById("aircraft-select");
  const refreshButton = document.getElementById("aircraft-refresh");
  await populateAircraftSelect(select);

  select.addEventListener("change", () => selectAircraft(viewer, select.value));
  refreshButton.addEventListener("click", () => populateAircraftSelect(select));
}

main().catch((err) => {
  console.error("globe page failed to start", err);
});
