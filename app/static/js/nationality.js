// nationality.js -- client-side "which country does this ICAO address
// belong to" lookup, using the block table published by GET /api/config
// (app/domain/nationality.py is the single source of truth -- same
// pattern as altitude bands in map.js/globe.js's setAltitudeBands; this
// module never keeps its own hard-coded copy of the table). The flag
// itself is never transmitted or stored anywhere: a 2-letter ISO country
// code maps to its Unicode flag emoji via the regional-indicator-symbol
// formula, computed here on demand.

let blocks = [];

export function setNationalityBlocks(nationalityBlocks) {
  blocks = nationalityBlocks || [];
}

export function countryForIcao(icao) {
  if (!icao || icao.startsWith("~")) return null;
  const value = Number.parseInt(icao, 16);
  if (!Number.isFinite(value)) return null;
  for (const block of blocks) {
    if (value >= block.start && value <= block.end) {
      return { code: block.code, name: block.name };
    }
  }
  return null;
}

export function flagEmoji(countryCode) {
  if (!countryCode || countryCode.length !== 2) return "";
  return String.fromCodePoint(...[...countryCode.toUpperCase()].map((c) => 127397 + c.charCodeAt(0)));
}
