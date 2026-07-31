// fullmap.js -- entrypoint for fullmap.html: the track map, large, with a
// live mode (shared WS /ws/aircraft-positions broadcast, same one
// globe.js's 3D globe uses) and a history mode (GET /api/tracks?hours=,
// 1h steps up to 72h via a slider) -- mirrors globe.js's live/history mode
// switch, aircraft picker, fast-mode toggle, and shift+click isolate, just
// rendering flat 2D category-icons (app/static/js/aircraft-icons.js)
// instead of 3D models. Uses the same dynamic-import-isolation approach as
// main.js (a map.js/MapLibre load failure must not crash this whole page).

import { api } from "./api.js";
import { renderAltitudeLegend } from "./altitude-legend.js";

const HISTORY_AUTO_REFRESH_INTERVAL_MS = 30000;
const DEFAULT_CONFIG = {
  map_style_url: "https://tiles.openfreemap.org/styles/positron",
  display_timezone: "UTC",
  altitude_bands: [],
  version: null,
  git_revision: null,
};

const NOOP_CONTROLLER = {
  setTracks: () => {},
  resize: () => {},
  setHeatmap: () => {},
  setHeatmapVisible: () => {},
  setLivePositions: () => {},
  clearLivePositions: () => {},
  setLiveFeatureShiftClickHandler: () => {},
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

// --- state -------------------------------------------------------------

let mapController = NOOP_CONTROLLER;
let mode = "live"; // "live" or "history" -- see enterLiveMode/enterHistoryMode
let socket = null;
let fastModeEnabled = false;
let isolatedIcao = null;
const hiddenIcaos = new Set(); // user-unchecked via the picker
const knownAircraft = new Map(); // icao -> callsign|null, for the picker list
const pickerCheckboxes = new Map();
const pickerLabels = new Map();
const latestPositions = new Map(); // icao -> latest broadcast entry
let currentHistoryHours = 6;
// Incremented on every enterHistoryMode()/refresh call; a resolved fetch
// only draws if it's still the latest request -- same guard globe.js's
// history slider uses, since the slider can fire several requests in
// quick succession while dragging.
let historyRequestId = 0;
let historyAutoRefreshTimer = null;

function applyLivePositions() {
  const visible = [];
  for (const [icao, position] of latestPositions) {
    if (isolatedIcao ? icao !== isolatedIcao : hiddenIcaos.has(icao)) continue;
    visible.push(position);
  }
  mapController.setLivePositions(visible);
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
      console.error("fullmap: failed to parse broadcast message", err);
      return;
    }
    const positions = (data && data.aircraft) || [];
    const seenIcaos = new Set();
    for (const position of positions) {
      if (!position.icao) continue;
      seenIcaos.add(position.icao);
      latestPositions.set(position.icao, position);
      ensurePickerEntry(position.icao, position.callsign);
    }
    for (const icao of Array.from(latestPositions.keys())) {
      if (!seenIcaos.has(icao)) latestPositions.delete(icao);
    }
    applyLivePositions();
  });
  socket.addEventListener("error", () => console.error("fullmap: live connection error"));
}

function teardownLiveView() {
  if (socket) {
    socket.close();
    socket = null;
  }
  if (isolatedIcao) exitIsolate();
  latestPositions.clear();
  mapController.clearLivePositions();
}

function sendFastMode() {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ fast: fastModeEnabled }));
  }
}

// --- aircraft picker (checkbox multi-select, mirrors globe.js) ---------

function addPickerRow(icao, callsign) {
  const list = document.getElementById("aircraft-picker-list");
  if (!list) return;

  const row = document.createElement("div");
  row.className = "globe-picker__item";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = `fullmap-picker-${icao}`;
  checkbox.checked = !hiddenIcaos.has(icao);
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) hiddenIcaos.delete(icao);
    else hiddenIcaos.add(icao);
    applyLivePositions();
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

// --- isolate mode (shift+click one aircraft) ----------------------------

function exitIsolate() {
  isolatedIcao = null;
  const btn = document.getElementById("exit-isolate");
  if (btn) btn.hidden = true;
  applyLivePositions();
}

function enterIsolate(icao) {
  isolatedIcao = icao;
  const btn = document.getElementById("exit-isolate");
  if (btn) btn.hidden = false;
  applyLivePositions();
}

function toggleIsolate(icao) {
  if (isolatedIcao === icao) {
    exitIsolate();
    return;
  }
  isolatedIcao = icao;
  const btn = document.getElementById("exit-isolate");
  if (btn) btn.hidden = false;
  applyLivePositions();
}

// --- mode switching (live vs. history) ----------------------------------

function setLiveControlsVisible(visible) {
  const liveControls = document.getElementById("live-controls");
  if (liveControls) liveControls.hidden = !visible;
}

function stopHistoryAutoRefresh() {
  if (historyAutoRefreshTimer) {
    clearInterval(historyAutoRefreshTimer);
    historyAutoRefreshTimer = null;
  }
}

async function refreshHistory() {
  const requestId = ++historyRequestId;
  try {
    const tracksGeoJSON = await api.getTracks(currentHistoryHours);
    if (requestId !== historyRequestId) return; // a newer request has since started
    mapController.setTracks(tracksGeoJSON);
  } catch (err) {
    if (requestId !== historyRequestId) return;
    console.error("tracks refresh failed", err);
    const errorEl = document.getElementById("map-error");
    if (errorEl) {
      errorEl.textContent = "航跡データの取得に失敗しました。";
      errorEl.hidden = false;
    }
  }
}

function enterHistoryMode(hours) {
  currentHistoryHours = hours;
  if (mode === "live") teardownLiveView();
  mode = "history";
  setLiveControlsVisible(false);
  refreshHistory();
  stopHistoryAutoRefresh();
  historyAutoRefreshTimer = setInterval(() => {
    if (!document.hidden) refreshHistory();
  }, HISTORY_AUTO_REFRESH_INTERVAL_MS);
}

function enterLiveMode() {
  if (mode === "live") return;
  mode = "live";
  stopHistoryAutoRefresh();
  mapController.setTracks({ type: "FeatureCollection", features: [] });
  setLiveControlsVisible(true);
  connectBroadcast();
}

// --- wiring --------------------------------------------------------------

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
    applyLivePositions();
  });
  document.getElementById("aircraft-picker-none").addEventListener("click", () => {
    for (const icao of knownAircraft.keys()) hiddenIcaos.add(icao);
    for (const checkbox of pickerCheckboxes.values()) checkbox.checked = false;
    applyLivePositions();
  });

  document.getElementById("aircraft-refresh").addEventListener("click", () => refreshPickerFromRecent());
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

function wireIsolateExit() {
  const btn = document.getElementById("exit-isolate");
  if (btn) btn.addEventListener("click", () => exitIsolate());
}

function wireModeButtons() {
  const liveButton = document.querySelector(
    '.app-header__period[aria-label="表示モード"] button[data-mode="live"]'
  );
  const slider = document.getElementById("history-hours-slider");
  const valueLabel = document.getElementById("history-hours-value");
  if (!liveButton || !slider || !valueLabel) return;

  valueLabel.textContent = `${slider.value}H`;

  liveButton.addEventListener("click", () => {
    liveButton.setAttribute("aria-pressed", "true");
    enterLiveMode();
  });

  slider.addEventListener("input", () => {
    valueLabel.textContent = `${slider.value}H`;
  });
  slider.addEventListener("change", () => {
    liveButton.setAttribute("aria-pressed", "false");
    enterHistoryMode(Number(slider.value));
  });
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

  const mapModule = await loadMapModule();
  if (mapModule) {
    mapModule.setTimezone(config.display_timezone);
    mapModule.setAltitudeBands(config.altitude_bands);
    mapController = mapModule.createTrackMap({ containerId: "map", styleUrl: config.map_style_url });
    mapController.setLiveFeatureShiftClickHandler(toggleIsolate);
  }

  await refreshPickerFromRecent();
  wirePicker();
  wireFastModeToggle();
  wireIsolateExit();
  wireModeButtons();
  connectBroadcast(); // starts in live mode by default

  window.addEventListener("resize", () => mapController.resize());
}

main().catch((err) => {
  console.error("fullmap page failed to start", err);
});
