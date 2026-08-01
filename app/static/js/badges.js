// badges.js -- entrypoint for badges.html: renders GET /api/badges (Milestone
// MM), recomputed fresh server-side on every load -- no local state to keep
// in sync, no "seen/dismissed" tracking either (kept out of v1 scope).

import { api } from "./api.js";
import { registerServiceWorker } from "./pwa.js";
import { t, applyStaticTranslations } from "./i18n.js";

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

function renderBadges(badges) {
  const grid = document.getElementById("badges-grid");
  if (!grid) return;
  grid.replaceChildren();

  for (const badge of badges) {
    const card = document.createElement("div");
    card.className = badge.earned ? "badge-card badge-card--earned" : "badge-card";

    const icon = document.createElement("div");
    icon.className = "badge-card__icon";
    icon.textContent = badge.icon;
    icon.setAttribute("aria-hidden", "true");

    const name = document.createElement("div");
    name.className = "badge-card__name";
    name.textContent = t(`badges.${badge.key}.name`);

    const description = document.createElement("div");
    description.className = "badge-card__description";
    description.textContent = t(`badges.${badge.key}.description`);

    card.append(icon, name, description);

    if (badge.progress !== null && badge.progress !== undefined) {
      const progress = document.createElement("div");
      progress.className = "badge-card__progress";
      progress.textContent = t("badges.progress", { value: badge.progress });
      card.appendChild(progress);
    }

    grid.appendChild(card);
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
  registerServiceWorker();

  try {
    const response = await api.getBadges();
    renderBadges(response.badges);
  } catch (err) {
    console.error("badges fetch failed", err);
    const errorEl = document.getElementById("badges-error");
    if (errorEl) {
      errorEl.textContent = t("badges.fetchFailed");
      errorEl.hidden = false;
    }
  }
}

main().catch((err) => {
  console.error("badges page failed to start", err);
});
