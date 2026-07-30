// ui.js -- status cards, ingestion badge, rankings tables, recent-aircraft
// table, and the periodic refresh loop. Never uses innerHTML with API data
// (callsigns/ICAOs are externally-sourced strings) -- always textContent.

import { api } from "./api.js";
import { createAircraftInfoTrigger, isAnyAircraftInfoPanelOpen } from "./aircraftinfo.js";
import { formatDistance, formatAltitude } from "./units.js";

// Matches the collector's default POLL_INTERVAL_SECONDS (5s) -- the
// active-aircraft count can't actually change any faster than that, so
// polling faster than this would just add load without fresher data.
const REFRESH_INTERVAL_MS = 5000;
const INGESTION_STATE_LABELS = {
  ok: "正常",
  stale: "データ取得停止中",
  error: "取得エラー",
  no_data: "データなし",
};

let displayTimezone = "UTC";

function setTimezone(tz) {
  displayTimezone = tz;
}

function formatTime(isoString) {
  if (!isoString) return "--";
  try {
    return new Date(isoString).toLocaleString("ja-JP", {
      timeZone: displayTimezone,
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function renderIngestionBadge(status) {
  const badge = document.getElementById("ingestion-badge");
  if (!badge) return;
  badge.dataset.state = status.ingestion_state;
  const textEl = badge.querySelector(".status-text");
  if (textEl) {
    textEl.textContent = INGESTION_STATE_LABELS[status.ingestion_state] || status.ingestion_state;
  }
}

function setUniqueCount(count) {
  setText("card-unique", String(count));
}

function renderStatusCards(status) {
  const isOk = status.ingestion_state === "ok";
  setText("card-active", isOk ? String(status.active_aircraft_count) : "--");
  setText("card-position", isOk ? String(status.position_aircraft_count) : "--");
  setText("card-last-fetch", formatTime(status.last_ingestion_at));
  setText("last-update", formatTime(status.generated_at));

  const footer = document.getElementById("footer-last-fetch");
  if (footer) {
    footer.textContent = status.last_ingestion_at
      ? `最終取得: ${formatTime(status.last_ingestion_at)}`
      : "";
  }
}

function clearChildren(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

// `content` is plain text in the common case, but may also be a DOM node
// (e.g. history.js's favorite-toggle button cell) -- never innerHTML with
// API-derived text either way (callsigns/ICAOs are externally sourced).
function addCell(row, content) {
  const cell = document.createElement("td");
  if (content instanceof Node) {
    cell.appendChild(content);
  } else {
    cell.textContent = content;
  }
  row.appendChild(cell);
}

function toggleTableVisibility(table, hasRows) {
  const emptyMessage = table.parentElement.querySelector(".panel__empty");
  table.hidden = !hasRows;
  if (emptyMessage) emptyMessage.hidden = hasRows;
}

// Generic ranking-table renderer: `buildRow(entry)` returns the cell text
// values for one row, so this same table-rendering shell (clear/toggle-
// empty/populate) works for any entry shape, not just farthest/closest.
function renderRankingTable(tableId, entries, buildRow) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const tbody = table.querySelector("tbody");
  clearChildren(tbody);
  toggleTableVisibility(table, entries.length > 0);

  for (const entry of entries) {
    const row = document.createElement("tr");
    for (const cellText of buildRow(entry)) {
      addCell(row, cellText);
    }
    tbody.appendChild(row);
  }
}

function distanceRankingRow(entry) {
  return [
    createAircraftInfoTrigger(entry.icao, entry.callsign || entry.icao),
    formatDistance(entry.distance_km),
    formatAltitude(entry.altitude_ft),
    formatTime(entry.observed_at),
  ];
}

function renderRecentAircraft(rows) {
  const table = document.getElementById("recent-aircraft");
  if (!table) return;
  const tbody = table.querySelector("tbody");
  clearChildren(tbody);
  toggleTableVisibility(table, rows.length > 0);

  for (const row of rows) {
    const tr = document.createElement("tr");
    addCell(tr, createAircraftInfoTrigger(row.icao, row.callsign || row.icao));
    addCell(tr, formatTime(row.first_seen_at));
    addCell(tr, formatTime(row.last_seen_at));
    tbody.appendChild(tr);
  }
}

async function refreshStatusAndRankings() {
  try {
    const status = await api.getStatus();
    renderIngestionBadge(status);
    renderStatusCards(status);
  } catch (err) {
    console.error("status refresh failed", err);
    const badge = document.getElementById("ingestion-badge");
    if (badge) {
      badge.dataset.state = "error";
      const textEl = badge.querySelector(".status-text");
      if (textEl) textEl.textContent = "APIエラー";
    }
  }

  // Skip rebuilding these tables while the user has an aircraft-info panel
  // open (opened from one of these very rows) -- a full rebuild on every
  // 5s poll would otherwise yank the open panel away mid-read and discard
  // its already-fetched data. Status cards above keep refreshing regardless.
  if (isAnyAircraftInfoPanelOpen()) return;

  try {
    const [rankings, recent] = await Promise.all([
      api.getRankings(24, 10),
      api.getRecentAircraft(24, 20),
    ]);
    renderRankingTable("ranking-farthest", rankings.farthest, distanceRankingRow);
    renderRankingTable("ranking-closest", rankings.closest, distanceRankingRow);
    renderRecentAircraft(recent);
  } catch (err) {
    console.error("rankings/recent refresh failed", err);
  }
}

function startPolling() {
  let timer = null;

  const tick = async () => {
    if (!document.hidden) {
      await refreshStatusAndRankings();
    }
    timer = setTimeout(tick, REFRESH_INTERVAL_MS);
  };

  document.addEventListener("visibilitychange", () => {
    // Refresh immediately when the tab becomes visible again, but never
    // poll while hidden -- avoids unnecessary background load.
    if (!document.hidden) {
      refreshStatusAndRankings();
    }
  });

  tick();

  return () => clearTimeout(timer);
}

export const ui = {
  setTimezone,
  formatTime,
  refreshStatusAndRankings,
  startPolling,
  setUniqueCount,
  renderRankingTable,
};
