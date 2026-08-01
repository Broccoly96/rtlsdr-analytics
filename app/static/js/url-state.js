// url-state.js -- reflects page filter state into the URL query string
// (Milestone RR), so a specific view (heatmap filters, daily report day,
// history period/favorites-only) can be bookmarked or shared within the
// tailnet. Always uses history.replaceState, never pushState, so routine
// filter changes don't pollute browser back/forward history with dozens
// of entries.

export function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

export function setParam(name, value) {
  const url = new URL(window.location.href);
  if (value === null || value === undefined || value === "") {
    url.searchParams.delete(name);
  } else {
    url.searchParams.set(name, String(value));
  }
  window.history.replaceState({}, "", url);
}
