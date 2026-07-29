// main.js -- entrypoint: loads /api/config, wires map/chart/ui together,
// and drives the period switch + refresh loop.
//
// map.js is loaded via a *dynamic* import, not a static one: it in turn
// statically imports MapLibre GL JS from a CDN, and ES modules fail their
// entire static-import graph atomically -- if that one CDN fetch failed
// (network hiccup, ad/tracker blocker, offline CDN), a static import here
// would silently prevent this whole file from ever running at all (no
// status cards, no chart, nothing), which directly breaks PLAN.md D-2's
// "地図失敗時もグラフとランキングを利用可能にする" requirement. Dynamic
// import isolates that failure to the map panel only.

import { api } from "./api.js";
import { ui } from "./ui.js";
import { createTrafficChart, refreshTraffic, setTimezone as setChartTimezone } from "./chart.js";

// CSP violations (e.g. a browser extension or local policy blocking a
// same-origin script/style/connect target) don't throw a catchable JS error
// and don't show up in showMapLoadError's try/catch -- they only appear as a
// browser-generated console line, invisible without devtools. Surface them
// on-page too, since "map fails to load but the server serves everything
// correctly" was hard to diagnose without asking the user to open devtools.
document.addEventListener("securitypolicyviolation", (event) => {
  const detail = `CSPにより読み込みがブロックされました: ${event.blockedURI}(directive: ${event.violatedDirective})`;
  console.error(detail, event);
  const errorEl = document.getElementById("map-error");
  if (errorEl && errorEl.hidden) {
    errorEl.textContent = `${detail} -- ブラウザの拡張機能やセキュリティソフトが関与している可能性があります。`;
    errorEl.hidden = false;
  }
});

const TRAFFIC_WINDOW_HOURS = 24;
const AUTO_REFRESH_INTERVAL_MS = 30000;
const DEFAULT_CONFIG = {
  map_style_url: "https://tiles.openfreemap.org/styles/positron",
  display_timezone: "UTC",
  altitude_bands: [],
  version: null,
  git_revision: null,
};

// Shown in the header so it's possible to confirm which exact build a
// given browser tab is actually looking at (e.g. when debugging a remote
// preview and wondering whether a fix has actually been redeployed yet).
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
    errorEl.textContent = `地図モジュールの読み込みに失敗しました: ${detail}(他の情報は利用できます)`;
    errorEl.hidden = false;
  }
}

async function loadMapModule() {
  // A plain fetch() isn't subject to ES module linking-graph error wrapping
  // the way import() is, so on failure it gives a much more specific reason
  // (HTTP status, network error) than import()'s generic "Failed to fetch
  // dynamically imported module" message. NOTE: unlike import()'s specifier,
  // fetch() resolves a relative URL against the *document's* base URL, not
  // this module's URL -- import.meta.url must be passed explicitly as the
  // base or "./map.js" would resolve to the site root instead of this
  // module's own directory.
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
  ui.setTimezone(config.display_timezone);
  setChartTimezone(config.display_timezone);

  const chartController = createTrafficChart("chart");
  let mapController = { setTracks: () => {}, resize: () => {} };
  let currentTracksHours = 6;

  const mapModule = await loadMapModule();
  let refreshTracks = async () => {};
  if (mapModule) {
    mapModule.setTimezone(config.display_timezone);
    mapModule.setAltitudeBands(config.altitude_bands);
    mapController = mapModule.createTrackMap({ containerId: "map", styleUrl: config.map_style_url });
    refreshTracks = mapModule.refreshTracks;
    await refreshTracks(mapController, currentTracksHours);
  }

  const periodButtons = document.querySelectorAll(".period-btn");
  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      periodButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      currentTracksHours = Number(button.dataset.hours);
      refreshTracks(mapController, currentTracksHours);
    });
  });

  window.addEventListener("resize", () => {
    mapController.resize();
    chartController.resize();
  });

  await Promise.all([refreshTraffic(chartController, TRAFFIC_WINDOW_HOURS), ui.refreshStatusAndRankings()]);

  ui.startPolling();

  setInterval(() => {
    if (!document.hidden) {
      refreshTracks(mapController, currentTracksHours);
      refreshTraffic(chartController, TRAFFIC_WINDOW_HOURS);
    }
  }, AUTO_REFRESH_INTERVAL_MS);
}

main().catch((err) => {
  console.error("dashboard failed to start", err);
});
