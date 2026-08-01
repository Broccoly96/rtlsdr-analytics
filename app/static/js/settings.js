// settings.js -- entrypoint for settings.html: distance/altitude unit
// preference, persisted via units.js (localStorage only). No server
// involvement -- same zero-backend precedent as history.js's favorites.

import { api } from "./api.js";
import { getUnits, setUnits } from "./units.js";
import { getTrackOpacity, setTrackOpacity } from "./track-settings.js";
import { isSpeechEnabled, setSpeechEnabled } from "./speech.js";
import { getHiddenSections, setHiddenSections } from "./dashboard-layout.js";
import { getTheme, setTheme } from "./theme.js";
import {
  isFavoriteNotifyEnabled,
  setFavoriteNotifyEnabled,
  getNotificationPermission,
  requestNotificationPermission,
} from "./browser-notify.js";
import { registerServiceWorker } from "./pwa.js";
import { getLanguage, setLanguage, applyStaticTranslations, t } from "./i18n.js";

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
  applyStaticTranslations();
  renderVersion(config);
  registerServiceWorker();

  const units = getUnits();
  wireButtonGroup("distance-unit-group", units.distance, (value) => {
    setUnits({ ...getUnits(), distance: value });
  });
  wireButtonGroup("altitude-unit-group", units.altitude, (value) => {
    setUnits({ ...getUnits(), altitude: value });
  });
  wireButtonGroup("language-group", getLanguage(), (value) => {
    setLanguage(value);
  });
  wireButtonGroup("theme-group", getTheme(), (value) => {
    setTheme(value);
  });
  wireButtonGroup("speech-enabled-group", isSpeechEnabled() ? "on" : "off", (value) => {
    setSpeechEnabled(value === "on");
  });
  wireButtonGroup(
    "browser-notify-group",
    isFavoriteNotifyEnabled() ? "on" : "off",
    (value) => {
      setFavoriteNotifyEnabled(value === "on");
    }
  );

  const permissionButton = document.getElementById("browser-notify-permission-button");
  const permissionStatus = document.getElementById("browser-notify-permission-status");
  function renderPermissionStatus() {
    if (!permissionStatus) return;
    permissionStatus.textContent = t(`settings.browserNotify.permission.${getNotificationPermission()}`);
  }
  renderPermissionStatus();
  if (permissionButton) {
    permissionButton.addEventListener("click", async () => {
      await requestNotificationPermission();
      renderPermissionStatus();
    });
  }

  const hiddenSections = new Set(getHiddenSections());
  const sectionCheckboxes = document.querySelectorAll("#dashboard-section-toggles input[type=checkbox]");
  sectionCheckboxes.forEach((checkbox) => {
    checkbox.checked = !hiddenSections.has(checkbox.dataset.section);
    checkbox.addEventListener("change", () => {
      const nowHidden = new Set(getHiddenSections());
      if (checkbox.checked) nowHidden.delete(checkbox.dataset.section);
      else nowHidden.add(checkbox.dataset.section);
      setHiddenSections(Array.from(nowHidden));
    });
  });

  const slider = document.getElementById("track-opacity-slider");
  const valueLabel = document.getElementById("track-opacity-value");
  if (slider && valueLabel) {
    const percent = Math.round(getTrackOpacity() * 100);
    slider.value = String(percent);
    valueLabel.textContent = `${percent}%`;
    slider.addEventListener("input", () => {
      valueLabel.textContent = `${slider.value}%`;
    });
    slider.addEventListener("change", () => {
      setTrackOpacity(Number(slider.value) / 100);
    });
  }
}

main().catch((err) => {
  console.error("settings page failed to start", err);
});
