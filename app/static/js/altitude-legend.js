// altitude-legend.js -- shared color-legend renderer for the altitude-band
// coloring used by both the 3D globe (app/static/js/globe.js) and the flat
// map (app/static/js/map.js). Takes the *raw* GET /api/config altitude_bands
// array (each {key, label, max_ft, color}) -- the human-readable Japanese
// `label` only exists on that raw shape; both consumers narrow it down to
// {max, color} internally for colorForAltitude() and would otherwise lose it.

export function renderAltitudeLegend(container, bands) {
  if (!container) return;
  container.replaceChildren();
  for (const band of bands || []) {
    const item = document.createElement("div");
    item.className = "altitude-legend__item";

    const swatch = document.createElement("span");
    swatch.className = "altitude-legend__swatch";
    swatch.style.backgroundColor = band.color;

    const label = document.createElement("span");
    label.textContent = band.label;

    item.append(swatch, label);
    container.appendChild(item);
  }
}
