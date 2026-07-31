// altitude-legend.js -- shared color-legend renderer for the altitude-band
// coloring used by both the 3D globe (app/static/js/globe.js) and the flat
// map (app/static/js/map.js). Takes the *raw* GET /api/config altitude_bands
// array (each {key, label, max_ft, color}) -- the human-readable Japanese
// `label` only exists on that raw shape; both consumers narrow it down to
// {max, color} internally for colorForAltitude() and would otherwise lose it.

import { formatAltitude } from "./units.js";

// Bands arrive in ascending-altitude order (app/domain/bands.py's tuple
// order, published as-is via /api/config) -- a band's lower bound is
// simply the previous band's max_ft, so no separate min_ft field is
// needed from the backend.
function rangeTextFor(bands, index) {
  const band = bands[index];
  const prevMax = index === 0 ? null : bands[index - 1].max_ft;
  if (prevMax == null) return `${formatAltitude(band.max_ft)}以下`;
  if (band.max_ft == null) return `${formatAltitude(prevMax)}超`;
  return `${formatAltitude(prevMax)}〜${formatAltitude(band.max_ft)}`;
}

export function renderAltitudeLegend(container, bands) {
  if (!container) return;
  container.replaceChildren();
  (bands || []).forEach((band, index) => {
    const item = document.createElement("div");
    item.className = "altitude-legend__item";

    const swatch = document.createElement("span");
    swatch.className = "altitude-legend__swatch";
    swatch.style.backgroundColor = band.color;

    const label = document.createElement("span");
    label.textContent = band.label;

    const range = document.createElement("span");
    range.className = "altitude-legend__range";
    range.textContent = rangeTextFor(bands, index);

    item.append(swatch, label, range);
    container.appendChild(item);
  });
}
