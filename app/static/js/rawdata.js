// rawdata.js -- entrypoint for rawdata.html: live-scrolling table of
// decoded Beast frames over WS /ws/rawdata. Nothing here is persisted --
// closing the tab loses the history, by design (see app/api/routers/
// rawdata.py's docstring).

import { api } from "./api.js";

const MAX_ROWS = 500;
const RECONNECT_DELAY_MS = 3000;

const FRAME_TYPE_LABELS = {
  mode_ac: "Mode A/C",
  mode_s_short: "Mode-S (short)",
  mode_s_long: "Mode-S (long)",
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

function setConnectionState(state, label) {
  const badge = document.getElementById("connection-badge");
  if (!badge) return;
  badge.dataset.state = state;
  const textEl = badge.querySelector(".status-text");
  if (textEl) textEl.textContent = label;
}

function formatNowTime() {
  return new Date().toLocaleTimeString("ja-JP", { hour12: false });
}

function addRow(tbody, frame) {
  const decoded = frame.decoded || {};
  const row = document.createElement("tr");
  const cells = [
    formatNowTime(),
    FRAME_TYPE_LABELS[frame.frame_type] || frame.frame_type,
    decoded.df != null ? String(decoded.df) : "--",
    decoded.icao24 || "--",
    decoded.ca != null ? String(decoded.ca) : "--",
    decoded.tc_label || decoded.df_label || "--",
    frame.message_hex,
  ];
  for (const text of cells) {
    const cell = document.createElement("td");
    cell.textContent = text;
    row.appendChild(cell);
  }
  // Newest first, capped -- prepend and trim rather than letting the
  // table grow unbounded while the tab is left open.
  tbody.insertBefore(row, tbody.firstChild);
  while (tbody.children.length > MAX_ROWS) {
    tbody.removeChild(tbody.lastChild);
  }
}

// Module-level (not per-connect()) so it survives reconnects and is only
// ever toggled by the one pause-button listener set up in setupPauseButton().
let paused = false;
let rowCount = 0;

function setupPauseButton() {
  const pauseToggle = document.getElementById("pause-toggle");
  if (!pauseToggle) return;
  pauseToggle.addEventListener("click", () => {
    paused = !paused;
    pauseToggle.setAttribute("aria-pressed", String(paused));
    pauseToggle.textContent = paused ? "再開" : "一時停止";
  });
}

function connect() {
  const tbody = document.querySelector("#rawdata-table tbody");
  const emptyEl = document.getElementById("rawdata-empty");
  const rowCountEl = document.getElementById("row-count");

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/rawdata`);

  setConnectionState("connecting", "接続中…");

  ws.addEventListener("open", () => {
    setConnectionState("ok", "接続中");
  });

  ws.addEventListener("message", (event) => {
    if (paused) return;
    let frame;
    try {
      frame = JSON.parse(event.data);
    } catch (err) {
      console.error("rawdata: failed to parse message", err);
      return;
    }
    if (frame.error) {
      setConnectionState("error", frame.error);
      return;
    }
    if (!tbody) return;
    addRow(tbody, frame);
    rowCount = Math.min(rowCount + 1, MAX_ROWS);
    if (rowCountEl) rowCountEl.textContent = String(rowCount);
    if (emptyEl) emptyEl.hidden = true;
  });

  ws.addEventListener("close", () => {
    setConnectionState("stale", `切断されました。${RECONNECT_DELAY_MS / 1000}秒後に再接続します…`);
    setTimeout(connect, RECONNECT_DELAY_MS);
  });

  ws.addEventListener("error", () => {
    setConnectionState("error", "接続エラー");
  });
}

function setupClearButton() {
  const clearButton = document.getElementById("clear-button");
  const tbody = document.querySelector("#rawdata-table tbody");
  const rowCountEl = document.getElementById("row-count");
  const emptyEl = document.getElementById("rawdata-empty");
  if (!clearButton || !tbody) return;
  clearButton.addEventListener("click", () => {
    tbody.replaceChildren();
    rowCount = 0;
    if (rowCountEl) rowCountEl.textContent = "0";
    if (emptyEl) emptyEl.hidden = false;
  });
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

  setupPauseButton();
  setupClearButton();
  connect();
}

main().catch((err) => {
  console.error("rawdata page failed to start", err);
});
