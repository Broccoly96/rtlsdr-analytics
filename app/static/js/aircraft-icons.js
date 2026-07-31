// aircraft-icons.js -- small, hand-authored flat SVG silhouettes for the
// fullscreen map's live mode (app/static/js/map.js), keyed by readsb's
// ADS-B emitter `category` field (e.g. "A3" = large aircraft, "A7" =
// rotorcraft, "B2" = lighter-than-air, ...) rather than exact aircraft
// type/model -- a deliberate, user-confirmed scope choice: a real
// per-exact-type icon library (tar1090/FlightRadar24-scale, hundreds of
// shapes) is a licensing and effort mismatch for this app (see CLAUDE.md's
// existing stance on not bundling third-party aircraft datasets). Each
// shape is rendered once per altitude-band color (registered via
// map.addImage()) so a moving aircraft's icon is both shape- and
// color-coded, matching the same altitude legend every other track/model
// in this app already uses.

const UNKNOWN_BAND_KEY = "unknown";
const UNKNOWN_ICON_COLOR = "#8fa3bd"; // matches style.css's --text-muted

// readsb's category is a 2-character string like "A3"; missing/"A0"/"B0"/
// "C0"/unrecognized all fall back to a generic silhouette.
export function shapeForCategory(category) {
  if (typeof category !== "string" || category.length < 2) return "unknown";
  const group = category[0];
  const num = category[1];
  if (group === "A") {
    if (num === "7") return "rotor";
    if (num === "3" || num === "4" || num === "5" || num === "6") return "jet";
    if (num === "1" || num === "2") return "light";
    return "unknown";
  }
  if (group === "B") {
    if (num === "6" || num === "7") return "uav";
    if (num === "1" || num === "2" || num === "4") return "glider";
    return "unknown";
  }
  if (group === "C") {
    if (num === "1" || num === "2") return "ground";
    return "unknown";
  }
  return "unknown";
}

// Each shape is a self-contained <svg> body (no <svg> wrapper), 24x24,
// nose pointing up (north) -- MapLibre's icon-rotate then rotates it to
// the aircraft's actual track with icon-rotation-alignment: "map".
const SHAPE_BODIES = {
  jet: (color) =>
    `<polygon points="12,1 15,10 23,16 23,18 15,15 15,20 19,23 19,24 12,22 5,24 5,23 9,20 9,15 1,18 1,16 9,10" fill="${color}"/>`,
  light: (color) =>
    `<polygon points="12,2 14,9 20,13 20,14.5 14,12.5 14,18 17,21 17,22 12,20.5 7,22 7,21 10,18 10,12.5 4,14.5 4,13 10,9" fill="${color}"/>`,
  glider: (color) =>
    `<polygon points="12,3 13,9 23,11 23,12.5 13,11.5 13,19 15,21 15,22 12,21 9,22 9,21 11,19 11,11.5 1,12.5 1,11 11,9" fill="${color}"/>`,
  rotor: (color) =>
    `<circle cx="12" cy="8" r="7" fill="none" stroke="${color}" stroke-width="1.5"/>` +
    `<rect x="10" y="10" width="4" height="8" rx="1.5" fill="${color}"/>` +
    `<rect x="12.25" y="16.5" width="8" height="1.5" fill="${color}"/>`,
  uav: (color) =>
    `<polygon points="12,4 18,12 12,20 6,12" fill="none" stroke="${color}" stroke-width="1.5"/>` +
    `<circle cx="12" cy="12" r="2" fill="${color}"/>`,
  ground: (color) => `<rect x="6" y="6" width="12" height="12" rx="3" fill="${color}"/>`,
  unknown: (color) => `<polygon points="12,2 18,20 12,16 6,20" fill="${color}"/>`,
};

const SHAPE_KEYS = Object.keys(SHAPE_BODIES);

function svgDataUri(shape, color) {
  const body = (SHAPE_BODIES[shape] || SHAPE_BODIES.unknown)(color);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">${body}</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function iconIdFor(shape, bandKey) {
  return `aircraft-icon-${shape}-${bandKey}`;
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image(24, 24);
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`icon image failed to load: ${src}`));
    img.src = src;
  });
}

// Registers one image per (shape x altitude-band-color) combination, plus
// one per shape at UNKNOWN_ICON_COLOR for aircraft with no altitude yet.
// Small combinatorial set (7 shapes x ~6 colors) -- negligible memory,
// registered once and reused for the lifetime of the map instance.
export async function registerAircraftIcons(map, bands) {
  const colorByBandKey = new Map((bands || []).map((b) => [b.key, b.color]));
  colorByBandKey.set(UNKNOWN_BAND_KEY, UNKNOWN_ICON_COLOR);

  const jobs = [];
  for (const shape of SHAPE_KEYS) {
    for (const [bandKey, color] of colorByBandKey) {
      const id = iconIdFor(shape, bandKey);
      if (map.hasImage(id)) continue;
      jobs.push(loadImage(svgDataUri(shape, color)).then((img) => map.addImage(id, img)));
    }
  }
  await Promise.all(jobs);
}

export { UNKNOWN_BAND_KEY };
