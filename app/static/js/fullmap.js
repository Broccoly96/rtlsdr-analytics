// fullmap.js -- entrypoint for fullmap.html: just the track map, large,
// with the same period switch and dynamic-import-isolation approach as
// main.js (a map.js/MapLibre load failure must not crash this whole page).

import { api } from "./api.js";
import { renderAltitudeLegend } from "./altitude-legend.js";

const AUTO_REFRESH_INTERVAL_MS = 30000;
const DEFAULT_CONFIG = {
  map_style_url: "https://tiles.openfreemap.org/styles/positron",
  display_timezone: "UTC",
  altitude_bands: [],
  version: null,
  git_revision: null,
};

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

function showMapLoadError(err) {
  console.error("failed to load map module", err);
  const errorEl = document.getElementById("map-error");
  if (errorEl) {
    const detail = err && err.message ? err.message : String(err);
    errorEl.textContent = `地図モジュールの読み込みに失敗しました: ${detail}`;
    errorEl.hidden = false;
  }
}

async function loadMapModule() {
  try {
    const res = await fetch(new URL("./map.js", import.meta.url));
    if (!res.ok) {
      showMapLoadError(new Error(`map.jsの取得に失敗しました (HTTP ${res.status})`));
      return null;
    }
  } catch (err) {
    showMapLoadError(new Error(`map.jsへのネットワーク接続に失敗しました: ${err && err.message ? err.message : err}`));
    return null;
  }

  try {
    return await import("./map.js");
  } catch (err) {
    showMapLoadError(err);
    return null;
  }
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config; using built-in defaults", err);
    config = DEFAULT_CONFIG;
  }

  renderVersion(config);
  renderAltitudeLegend(document.getElementById("altitude-legend"), config.altitude_bands);

  let mapController = { setTracks: () => {}, resize: () => {}, setHeatmap: () => {}, setHeatmapVisible: () => {} };
  let currentHours = 6;

  const mapModule = await loadMapModule();
  let refreshTracks = async () => {};
  if (mapModule) {
    mapModule.setTimezone(config.display_timezone);
    mapModule.setAltitudeBands(config.altitude_bands);
    mapController = mapModule.createTrackMap({ containerId: "map", styleUrl: config.map_style_url });
    refreshTracks = mapModule.refreshTracks;
    await refreshTracks(mapController, currentHours);
  }

  const periodButtons = document.querySelectorAll(".app-header__period .period-btn");
  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      periodButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      currentHours = Number(button.dataset.hours);
      refreshTracks(mapController, currentHours);
    });
  });

  window.addEventListener("resize", () => mapController.resize());

  setInterval(() => {
    if (!document.hidden) refreshTracks(mapController, currentHours);
  }, AUTO_REFRESH_INTERVAL_MS);
}

main().catch((err) => {
  console.error("fullmap page failed to start", err);
});
