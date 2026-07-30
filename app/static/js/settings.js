// settings.js -- entrypoint for settings.html: distance/altitude unit
// preference, persisted via units.js (localStorage only). No server
// involvement -- same zero-backend precedent as history.js's favorites.

import { api } from "./api.js";
import { getUnits, setUnits } from "./units.js";

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

function wireButtonGroup(groupId, currentValue, onSelect) {
  const group = document.getElementById(groupId);
  if (!group) return;
  const buttons = group.querySelectorAll(".period-btn");
  for (const button of buttons) {
    button.setAttribute("aria-pressed", String(button.dataset.value === currentValue));
    button.addEventListener("click", () => {
      buttons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      onSelect(button.dataset.value);
    });
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

  const units = getUnits();
  wireButtonGroup("distance-unit-group", units.distance, (value) => {
    setUnits({ ...getUnits(), distance: value });
  });
  wireButtonGroup("altitude-unit-group", units.altitude, (value) => {
    setUnits({ ...getUnits(), altitude: value });
  });
}

main().catch((err) => {
  console.error("settings page failed to start", err);
});
