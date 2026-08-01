// theme-init.js -- applies a previously-chosen light theme before first
// paint (Milestone RR), avoiding a flash of the wrong theme. Loaded as a
// plain synchronous <script src> in every page's <head> (not inline: this
// app's CSP is script-src 'self' with no 'unsafe-inline', so an inline
// snippet would simply be blocked -- see app/static/js/theme.js for the
// settings-page-facing read/write API this mirrors).
try {
  if (localStorage.getItem("adsb-analytics:theme") === "light") {
    document.documentElement.dataset.theme = "light";
  }
} catch (err) {
  console.error("failed to read theme from localStorage", err);
}
