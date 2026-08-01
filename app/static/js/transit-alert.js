// transit-alert.js -- shared sun-transit toast for fullmap.html/globe.html's
// live mode, both fed by WS /ws/aircraft-positions, whose entries now carry
// a server-computed transit_candidate flag (app/domain/celestial.py; the
// receiver's coordinates themselves never reach the browser, preserving
// the existing privacy boundary documented on GET /api/config). A toast
// fires once per transit *episode*, not once per broadcast tick while it
// continues -- the same "track active state, notify on transition" pattern
// app/collector/event_watch.py uses server-side for the emergency-squawk/
// favorite-seen webhooks.

import { t } from "./i18n.js";

const TOAST_DURATION_MS = 8000;

let active = new Set();
let toastContainer = null;

function ensureToastContainer() {
  if (toastContainer) return toastContainer;
  toastContainer = document.createElement("div");
  toastContainer.className = "transit-toast-container";
  document.body.appendChild(toastContainer);
  return toastContainer;
}

function showToast(label) {
  const container = ensureToastContainer();
  const toast = document.createElement("div");
  toast.className = "transit-toast";
  toast.textContent = t("transitAlert.message", { label });
  container.appendChild(toast);
  setTimeout(() => toast.remove(), TOAST_DURATION_MS);
}

export function checkTransitAlerts(positions) {
  const seenNow = new Set();
  for (const position of positions) {
    if (!position.transit_candidate || !position.icao) continue;
    seenNow.add(position.icao);
    if (!active.has(position.icao)) {
      showToast(position.callsign || position.icao);
    }
  }
  active = seenNow;
}

export function resetTransitAlerts() {
  active = new Set();
}
