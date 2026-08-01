// history.js -- entrypoint for history.html: "most frequently observed"
// ranking (GET /api/aircraft/frequent) and, when ?icao=xxxxxx is present,
// a single aircraft's detail view (GET /api/aircraft/{icao}/history).
//
// Favorites are server-backed (GET/POST/DELETE /api/favorites, via
// favorites.js) as of Milestone JJ -- previously pure client-side
// localStorage, migrated automatically on first load (see favorites.js).

import { api } from "./api.js";
import { ui } from "./ui.js";
import { createAircraftInfoTrigger } from "./aircraftinfo.js";
import { setNationalityBlocks } from "./nationality.js";
import { registerServiceWorker } from "./pwa.js";
import { t, applyStaticTranslations } from "./i18n.js";
import { loadFavorites, isFavorite, toggleFavorite } from "./favorites.js";
import { getParam, setParam } from "./url-state.js";

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
  button.setAttribute("aria-label", t("history.favoriteToggle", { icao }));
  button.textContent = isFavorite(icao) ? "★" : "☆";
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await toggleFavorite(icao);
      onToggle();
    } catch (err) {
      console.error(`failed to toggle favorite for ${icao}`, err);
    } finally {
      button.disabled = false;
    }
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
    content.appendChild(createAircraftInfoTrigger(history.icao, t("history.viewInfoAndPhoto")));

    const cards = document.createElement("section");
    cards.className = "status-cards";
    const cardDefs = [
      [t("index.firstSeen"), ui.formatTime(history.first_seen_at)],
      [t("index.lastSeen"), ui.formatTime(history.last_seen_at)],
      [t("history.daysObserved"), t("history.daysUnit", { count: history.days_observed })],
      [t("history.totalPasses"), t("history.passesUnit", { count: history.total_pass_count })],
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
    callsignHeading.textContent = t("history.callsignHistory");
    content.appendChild(callsignHeading);

    if (history.callsign_history.length > 0) {
      content.appendChild(renderCallsignHistory(history.callsign_history));
    } else {
      const empty = document.createElement("p");
      empty.className = "panel__empty";
      empty.textContent = t("common.noData");
      content.appendChild(empty);
    }
  } catch (err) {
    console.error("aircraft history fetch failed", err);
    const message = document.createElement("p");
    message.className = "panel__empty";
    message.textContent = err && err.status === 404 ? t("history.notFound") : t("history.fetchFailed");
    content.appendChild(message);
  }
}

async function renderOnThisDay() {
  const el = document.getElementById("on-this-day-content");
  if (!el) return;
  try {
    const data = await api.getOnThisDay();
    if (data.years.length === 0) {
      el.textContent = t("history.onThisDay.empty");
      return;
    }
    el.replaceChildren();
    for (const yearEntry of data.years) {
      const yearHeading = document.createElement("div");
      yearHeading.className = "card__label";
      yearHeading.textContent = t("history.onThisDay.yearsAgo", {
        year: yearEntry.year,
        count: new Date().getFullYear() - yearEntry.year,
      });
      el.appendChild(yearHeading);

      const list = document.createElement("ul");
      list.className = "callsign-history-list";
      for (const entry of yearEntry.aircraft) {
        const item = document.createElement("li");
        item.appendChild(createAircraftInfoTrigger(entry.icao, entry.callsign || entry.icao));
        item.appendChild(
          document.createTextNode(` — ${t("history.passesUnit", { count: entry.pass_count })}`)
        );
        list.appendChild(item);
      }
      el.appendChild(list);
    }
  } catch (err) {
    console.error("on-this-day fetch failed", err);
    el.textContent = t("history.fetchFailed");
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
  applyStaticTranslations();
  renderVersion(config);
  setNationalityBlocks(config.nationality_blocks);
  registerServiceWorker();
  await loadFavorites();
  await renderOnThisDay();

  const params = new URLSearchParams(window.location.search);
  const icao = params.get("icao");
  if (icao) {
    await renderDetail(icao);
  }

  const favoritesOnlyCheckbox = document.getElementById("favorites-only");
  const periodButtons = document.querySelectorAll(".frequent-period-btn");

  // Permalink support (Milestone RR): ?days=&favoritesOnly= override the
  // defaults so a specific view can be bookmarked/shared; reflected back
  // into the URL (via replaceState, never pushState) on every change.
  const daysFromUrl = Number(getParam("days"));
  let currentDays = [7, 30, 90].includes(daysFromUrl) ? daysFromUrl : 30;
  if (favoritesOnlyCheckbox) {
    favoritesOnlyCheckbox.checked = getParam("favoritesOnly") === "1";
  }
  periodButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(Number(button.dataset.days) === currentDays));
  });

  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      periodButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      currentDays = Number(button.dataset.days);
      setParam("days", currentDays === 30 ? null : currentDays);
      refreshFrequentTable(currentDays, favoritesOnlyCheckbox.checked);
    });
  });

  if (favoritesOnlyCheckbox) {
    favoritesOnlyCheckbox.addEventListener("change", () => {
      setParam("favoritesOnly", favoritesOnlyCheckbox.checked ? "1" : null);
      refreshFrequentTable(currentDays, favoritesOnlyCheckbox.checked);
    });
  }

  await refreshFrequentTable(currentDays, favoritesOnlyCheckbox ? favoritesOnlyCheckbox.checked : false);
}

main().catch((err) => {
  console.error("history page failed to start", err);
});
