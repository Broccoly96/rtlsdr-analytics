// browser-notify.js -- optional browser Notification when a favorited
// aircraft appears in fullmap.html/globe.html's live mode (Milestone RR).
// Same-page-open, live-broadcast-driven only -- NOT a Web Push background
// notification (that would need a service worker push handler + VAPID
// keys + a subscription-storage endpoint, a much larger change this
// milestone deliberately doesn't take on). The "notify me even when I'm
// not looking at any page" path is the separate, independent
// NOTIFY_FAVORITE_SEEN_ENABLED webhook (Milestone KK).
//
// Two separate concerns, kept apart deliberately: the page-level ON/OFF
// toggle (localStorage, same zero-backend precedent as every other
// setting here) and the actual browser permission grant, which only the
// browser itself tracks/revokes and which requires a user gesture to
// request -- so this is a thin wrapper, not a straight units.js clone.

import { isFavorite } from "./favorites.js";
import { t } from "./i18n.js";

const NOTIFY_ENABLED_KEY = "adsb-analytics:favorite-notify-enabled";

export function isFavoriteNotifyEnabled() {
  try {
    return localStorage.getItem(NOTIFY_ENABLED_KEY) === "true";
  } catch (err) {
    console.error("failed to read favorite-notify setting from localStorage", err);
    return false;
  }
}

export function setFavoriteNotifyEnabled(enabled) {
  try {
    localStorage.setItem(NOTIFY_ENABLED_KEY, enabled ? "true" : "false");
  } catch (err) {
    console.error("failed to persist favorite-notify setting to localStorage", err);
  }
}

export function isNotificationSupported() {
  return typeof window.Notification !== "undefined";
}

export function getNotificationPermission() {
  return isNotificationSupported() ? Notification.permission : "unsupported";
}

export async function requestNotificationPermission() {
  if (!isNotificationSupported()) return "unsupported";
  return await Notification.requestPermission();
}

function notify(label) {
  if (!isNotificationSupported() || Notification.permission !== "granted") return;
  try {
    new Notification(t("browserNotify.title"), { body: t("browserNotify.body", { label }) });
  } catch (err) {
    console.error("browser notification failed", err);
  }
}

// Tracked regardless of settings so re-enabling mid-session doesn't treat
// every already-live favorite as "new" -- same pattern as speech.js.
let knownFavoritesActive = new Set();

export function checkFavoriteArrivals(positions) {
  if (!isFavoriteNotifyEnabled() || getNotificationPermission() !== "granted") {
    knownFavoritesActive = new Set();
    return;
  }
  const seenNow = new Set();
  for (const position of positions) {
    if (!position.icao || !isFavorite(position.icao)) continue;
    seenNow.add(position.icao);
    if (!knownFavoritesActive.has(position.icao)) {
      notify(position.callsign || position.icao);
    }
  }
  knownFavoritesActive = seenNow;
}

export function resetFavoriteArrivals() {
  knownFavoritesActive = new Set();
}
