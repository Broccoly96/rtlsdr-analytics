// theme.js -- light/dark theme preference (Milestone RR). The actual
// "apply before first paint" logic is a tiny inline snippet duplicated at
// the top of every page's <head> (this module can't do that part itself:
// ES modules are deferred, so by the time an imported module ran, the
// first frame would already have painted in the wrong theme). This
// module exists only so settings.html's toggle can read/write the same
// localStorage key and apply a change immediately on that page too.

const THEME_KEY = "adsb-analytics:theme";

export function getTheme() {
  try {
    const value = localStorage.getItem(THEME_KEY);
    return value === "light" ? "light" : "dark";
  } catch (err) {
    console.error("failed to read theme from localStorage", err);
    return "dark";
  }
}

export function setTheme(theme) {
  const resolved = theme === "light" ? "light" : "dark";
  try {
    localStorage.setItem(THEME_KEY, resolved);
  } catch (err) {
    console.error("failed to persist theme to localStorage", err);
  }
  document.documentElement.dataset.theme = resolved;
}
