// speech.js -- optional "spotter radio" style announcement of newly-
// appeared live aircraft via the browser's SpeechSynthesis API. Off by
// default; the ON/OFF toggle is pure client-side localStorage, same
// zero-backend precedent as units.js/track-settings.js. Purely a same-
// page ambiance feature -- nothing here is sent to or received from the
// server, and it has no effect when the tab isn't open.

import { t, currentLocale } from "./i18n.js";

const SPEECH_ENABLED_KEY = "adsb-analytics:speech-enabled";

export function isSpeechEnabled() {
  try {
    return localStorage.getItem(SPEECH_ENABLED_KEY) === "true";
  } catch (err) {
    console.error("failed to read speech setting from localStorage", err);
    return false;
  }
}

export function setSpeechEnabled(enabled) {
  try {
    localStorage.setItem(SPEECH_ENABLED_KEY, enabled ? "true" : "false");
  } catch (err) {
    console.error("failed to persist speech setting to localStorage", err);
  }
}

function announce(label) {
  if (typeof window.speechSynthesis === "undefined") return;
  try {
    const utterance = new SpeechSynthesisUtterance(t("speech.announcement", { label }));
    utterance.lang = currentLocale();
    window.speechSynthesis.speak(utterance);
  } catch (err) {
    console.error("speech synthesis failed", err);
  }
}

// Tracked regardless of the enabled flag (so toggling it on mid-session
// doesn't treat every already-live aircraft as "new"); only the actual
// announcement is gated on isSpeechEnabled().
let knownIcaos = new Set();

export function checkNewArrivals(positions) {
  const enabled = isSpeechEnabled();
  const seenNow = new Set();
  for (const position of positions) {
    if (!position.icao) continue;
    seenNow.add(position.icao);
    if (enabled && !knownIcaos.has(position.icao)) {
      announce(position.callsign || position.icao);
    }
  }
  knownIcaos = seenNow;
}

export function resetKnownAircraft() {
  knownIcaos = new Set();
}
