// squawk-alert.js -- shared emergency-squawk (7500/7600/7700) banner for
// fullmap.html/globe.html's live mode, both fed by the same broadcast
// (WS /ws/aircraft-positions) which carries each aircraft's squawk as of
// Milestone KK. Purely a same-page visual alert, recomputed fresh on every
// broadcast tick (no state of its own) -- the "notify me even when I'm not
// looking at this page" path is the separate, independent
// NOTIFY_EMERGENCY_SQUAWK_ENABLED webhook (app/collector/event_watch.py),
// which watches the raw readsb poll directly, not this broadcast.

import { t } from "./i18n.js";

const EMERGENCY_SQUAWKS = new Set(["7500", "7600", "7700"]);

export function updateEmergencySquawkBanner(positions) {
  const banner = document.getElementById("emergency-squawk-banner");
  if (!banner) return;

  const emergencies = positions.filter((p) => EMERGENCY_SQUAWKS.has(p.squawk));
  if (emergencies.length === 0) {
    banner.hidden = true;
    banner.textContent = "";
    return;
  }

  banner.hidden = false;
  banner.textContent = emergencies
    .map((p) => t("squawkAlert.entry", { label: p.callsign || p.icao, squawk: p.squawk }))
    .join(" / ");
}
