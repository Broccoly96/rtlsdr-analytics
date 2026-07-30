// track-settings.js -- the 3D globe's track-line opacity preference
// (Settings tab, app/static/settings.html). Pure client-side localStorage,
// same zero-backend precedent as units.js -- open tabs don't pick up a
// change live, each page reads the preference once at load.

const TRACK_OPACITY_KEY = "adsb-analytics:track-opacity";
const DEFAULT_TRACK_OPACITY = 0.5;

export function getTrackOpacity() {
  try {
    const raw = localStorage.getItem(TRACK_OPACITY_KEY);
    if (raw == null) return DEFAULT_TRACK_OPACITY;
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0 || value > 1) return DEFAULT_TRACK_OPACITY;
    return value;
  } catch (err) {
    console.error("failed to read track opacity from localStorage", err);
    return DEFAULT_TRACK_OPACITY;
  }
}

export function setTrackOpacity(value) {
  try {
    localStorage.setItem(TRACK_OPACITY_KEY, String(value));
  } catch (err) {
    console.error("failed to persist track opacity to localStorage", err);
  }
}
