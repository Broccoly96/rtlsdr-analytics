// history.js -- entrypoint for history.html: "most frequently observed"
// ranking (GET /api/aircraft/frequent) and, when ?icao=xxxxxx is present,
// a single aircraft's detail view (GET /api/aircraft/{icao}/history).
//
// Favorites are pure client-side localStorage -- deliberately zero backend
// involvement, so this page doesn't become this API's first mutating
// endpoint (every other route in this app is GET-only, unauthenticated).

import { api } from "./api.js";
import { ui } from "./ui.js";
import { createAircraftInfoTrigger } from "./aircraftinfo.js";

const FAVORITES_KEY = "adsb-analytics:favorites";

function getFavorites() {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.error("failed to read favorites from localStorage", err);
    return [];
  }
}

function isFavorite(icao) {
  return getFavorites().includes(icao);
}

function toggleFavorite(icao) {
  const favorites = getFavorites();
  const index = favorites.indexOf(icao);
  if (index >= 0) {
    favorites.splice(index, 1);
  } else {
    favorites.push(icao);
  }
  try {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
  } catch (err) {
    console.error("failed to persist favorites to localStorage", err);
  }
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

function createFavoriteToggle(icao, onToggle) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "favorite-toggle";
  button.setAttribute("aria-pressed", String(isFavorite(icao)));
  button.setAttribute("aria-label", `${icao}をお気に入りに追加/削除`);
  button.textContent = isFavorite(icao) ? "★" : "☆";
  button.addEventListener("click", () => {
    toggleFavorite(icao);
    onToggle();
  });
  return button;
}

function buildFrequentRow(entry, onFavoriteToggle) {
  const link = document.createElement("a");
  link.href = `/static/history.html?icao=${encodeURIComponent(entry.icao)}`;
  link.textContent = entry.last_callsign || entry.icao;

  return [
    createFavoriteToggle(entry.icao, onFavoriteToggle),
    link,
    String(entry.days_observed),
    String(entry.total_pass_count),
  ];
}

async function refreshFrequentTable(days, favoritesOnly) {
  try {
    const data = await api.getAircraftFrequent(days, 50);
    const entries = favoritesOnly
      ? data.aircraft.filter((entry) => isFavorite(entry.icao))
      : data.aircraft;
    ui.renderRankingTable("ranking-frequent", entries, (entry) =>
      buildFrequentRow(entry, () => refreshFrequentTable(days, favoritesOnly))
    );
  } catch (err) {
    console.error("frequent aircraft refresh failed", err);
  }
}

function renderCallsignHistory(entries) {
  const list = document.createElement("ul");
  list.className = "callsign-history-list";
  for (const entry of entries) {
    const item = document.createElement("li");
    item.textContent = `${entry.callsign}: ${ui.formatTime(entry.first_seen_at)} 〜 ${ui.formatTime(entry.last_seen_at)}`;
    list.appendChild(item);
  }
  return list;
}

async function renderDetail(icao) {
  const panel = document.getElementById("detail-panel");
  const content = document.getElementById("detail-content");
  if (!panel || !content) return;
  panel.hidden = false;
  content.replaceChildren();

  try {
    const history = await api.getAircraftHistory(icao);

    const titleRow = document.createElement("div");
    titleRow.className = "detail-title-row";
    const title = document.createElement("h2");
    title.textContent = history.last_callsign || history.icao;
    titleRow.appendChild(title);
    titleRow.appendChild(
      createFavoriteToggle(history.icao, () => renderDetail(icao))
    );
    content.appendChild(titleRow);
    content.appendChild(createAircraftInfoTrigger(history.icao, "機体情報・写真を見る"));

    const cards = document.createElement("section");
    cards.className = "status-cards";
    const cardDefs = [
      ["初観測", ui.formatTime(history.first_seen_at)],
      ["最終観測", ui.formatTime(history.last_seen_at)],
      ["観測日数", `${history.days_observed}日`],
      ["総パス数", `${history.total_pass_count}回`],
    ];
    for (const [label, value] of cardDefs) {
      const card = document.createElement("div");
      card.className = "card";
      const labelEl = document.createElement("div");
      labelEl.className = "card__label";
      labelEl.textContent = label;
      const valueEl = document.createElement("div");
      valueEl.className = "card__value";
      valueEl.textContent = value;
      card.append(labelEl, valueEl);
      cards.appendChild(card);
    }
    content.appendChild(cards);

    const callsignHeading = document.createElement("div");
    callsignHeading.className = "panel__header";
    callsignHeading.textContent = "コールサイン履歴";
    content.appendChild(callsignHeading);

    if (history.callsign_history.length > 0) {
      content.appendChild(renderCallsignHistory(history.callsign_history));
    } else {
      const empty = document.createElement("p");
      empty.className = "panel__empty";
      empty.textContent = "データがありません";
      content.appendChild(empty);
    }
  } catch (err) {
    console.error("aircraft history fetch failed", err);
    const message = document.createElement("p");
    message.className = "panel__empty";
    message.textContent =
      err && err.status === 404 ? "機体が見つかりません。" : "機体情報の取得に失敗しました。";
    content.appendChild(message);
  }
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

  const params = new URLSearchParams(window.location.search);
  const icao = params.get("icao");
  if (icao) {
    await renderDetail(icao);
  }

  let currentDays = 30;
  const favoritesOnlyCheckbox = document.getElementById("favorites-only");

  const periodButtons = document.querySelectorAll(".frequent-period-btn");
  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      periodButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      currentDays = Number(button.dataset.days);
      refreshFrequentTable(currentDays, favoritesOnlyCheckbox.checked);
    });
  });

  if (favoritesOnlyCheckbox) {
    favoritesOnlyCheckbox.addEventListener("change", () => {
      refreshFrequentTable(currentDays, favoritesOnlyCheckbox.checked);
    });
  }

  await refreshFrequentTable(currentDays, favoritesOnlyCheckbox ? favoritesOnlyCheckbox.checked : false);
}

main().catch((err) => {
  console.error("history page failed to start", err);
});
