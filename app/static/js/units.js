// units.js -- shared distance/altitude display formatting for the user's
// unit preference (Settings tab, app/static/settings.html). Pure
// client-side localStorage, same zero-backend precedent as history.js's
// favorites -- internal storage/math stays km/ft (and meters for Cesium)
// everywhere; this only changes what's rendered as text. Open tabs don't
// pick up a change live -- each page reads the preference once at load.

const UNITS_KEY = "adsb-analytics:units";
const KM_TO_NM = 0.539957;
const FT_TO_M = 0.3048;

const DEFAULT_UNITS = { distance: "km", altitude: "ft" };

export function getUnits() {
  try {
    const raw = localStorage.getItem(UNITS_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return {
      distance: parsed.distance === "nm" ? "nm" : DEFAULT_UNITS.distance,
      altitude: parsed.altitude === "m" ? "m" : DEFAULT_UNITS.altitude,
    };
  } catch (err) {
    console.error("failed to read unit settings from localStorage", err);
    return { ...DEFAULT_UNITS };
  }
}

export function setUnits(units) {
  try {
    localStorage.setItem(UNITS_KEY, JSON.stringify(units));
  } catch (err) {
    console.error("failed to persist unit settings to localStorage", err);
  }
}

export function distanceUnitLabel() {
  return getUnits().distance;
}

// Raw converted number, no unit suffix -- for chart series/axis data that
// must stay numeric (so axis ticks and tooltips agree on the same
// value), as opposed to formatDistance's ready-to-display string.
export function toDisplayDistance(km) {
  if (km == null) return null;
  return getUnits().distance === "nm" ? km * KM_TO_NM : km;
}

export function formatDistance(km) {
  if (km == null) return "--";
  const { distance } = getUnits();
  if (distance === "nm") return `${(km * KM_TO_NM).toFixed(1)} nm`;
  return `${km.toFixed(1)} km`;
}

export function formatAltitude(ft) {
  if (ft == null) return "--";
  const { altitude } = getUnits();
  if (altitude === "m") return `${Math.round(ft * FT_TO_M)} m`;
  return `${Math.round(ft)} ft`;
}
