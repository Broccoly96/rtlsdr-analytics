// flags.js -- entrypoint for flags.html: a "passport" style collection
// view grouping every aircraft ever observed by country, inferred from
// its ICAO 24-bit address (app/domain/nationality.py is the single
// source of truth; nationality.js just applies the block table published
// over GET /api/config). Purely a read-only view over GET
// /api/aircraft/nationalities -- no new persisted state of its own.

import { api } from "./api.js";
import { registerServiceWorker } from "./pwa.js";
import { t, applyStaticTranslations } from "./i18n.js";
import { setNationalityBlocks, flagEmoji } from "./nationality.js";
import { ui } from "./ui.js";

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

function renderCountries(countries) {
  const grid = document.getElementById("flags-grid");
  const empty = document.getElementById("flags-empty");
  if (!grid) return;
  grid.replaceChildren();

  if (countries.length === 0) {
    if (empty) empty.hidden = false;
    return;
  }
  if (empty) empty.hidden = true;

  const sorted = [...countries].sort((a, b) => b.aircraft_count - a.aircraft_count);
  for (const country of sorted) {
    const card = document.createElement("div");
    card.className = "flag-card";

    const code = country.code.toLowerCase();
    const bg = document.createElement("img");
    bg.className = "flag-card__bg";
    bg.src = `/static/js/vendor/flag-icons/flags/4x3/${code}.svg`;
    bg.alt = "";
    bg.setAttribute("aria-hidden", "true");
    bg.addEventListener("error", () => {
      card.classList.add("flag-card--fallback");
    });

    const emojiFallback = document.createElement("div");
    emojiFallback.className = "flag-card__emoji-fallback";
    emojiFallback.textContent = flagEmoji(country.code);
    emojiFallback.setAttribute("aria-hidden", "true");

    const name = document.createElement("div");
    name.className = "flag-card__name";
    name.textContent = t(`nationality.country.${country.code}`);

    const count = document.createElement("div");
    count.className = "flag-card__count";
    count.textContent = t("flags.aircraftCount", { count: country.aircraft_count });

    const firstSeen = document.createElement("div");
    firstSeen.className = "flag-card__first-seen";
    firstSeen.textContent = t("flags.firstSeen", { date: ui.formatTime(country.first_seen_at) });

    card.append(bg, emojiFallback, name, count, firstSeen);
    grid.appendChild(card);
  }
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config", err);
    config = { version: null, git_revision: null, nationality_blocks: [], display_timezone: "UTC" };
  }
  applyStaticTranslations();
  renderVersion(config);
  registerServiceWorker();
  setNationalityBlocks(config.nationality_blocks);
  ui.setTimezone(config.display_timezone || "UTC");

  try {
    const response = await api.getAircraftNationalities();
    renderCountries(response.countries);
  } catch (err) {
    console.error("nationalities fetch failed", err);
    const errorEl = document.getElementById("flags-error");
    if (errorEl) {
      errorEl.textContent = t("flags.fetchFailed");
      errorEl.hidden = false;
    }
  }
}

main().catch((err) => {
  console.error("flags page failed to start", err);
});
