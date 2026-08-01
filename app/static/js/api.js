// api.js -- thin fetch wrappers for every backend endpoint. Every call has
// a client-side timeout so a hung request can't block the UI forever.

const DEFAULT_TIMEOUT_MS = 8000;

async function getJSON(path, params = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const url = new URL(path, window.location.origin);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }
  return requestJSON(url, {}, timeoutMs);
}

// POST/DELETE share this instead of getJSON's query-param handling --
// only /api/favorites uses these today, this app's first mutating calls.
async function requestJSON(url, init = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        if (body && body.detail) detail = body.detail;
      } catch {
        /* response body wasn't JSON -- keep the statusText fallback */
      }
      const error = new Error(detail || `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return response.status === 204 ? null : await response.json();
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  getConfig: () => getJSON("/api/config"),
  getStatus: () => getJSON("/api/status"),
  getTraffic: (hours) => getJSON("/api/traffic", { hours }),
  getTracks: (hours) => getJSON("/api/tracks", { hours }),
  getRankings: (hours, limit) => getJSON("/api/rankings", { hours, limit }),
  getRecentAircraft: (hours, limit) => getJSON("/api/aircraft/recent", { hours, limit }),
  getBearingRange: (hours) => getJSON("/api/receiver/bearing-range", { hours }),
  getAltitudeRange: (hours) => getJSON("/api/receiver/altitude-range", { hours }),
  getReception: (hours) => getJSON("/api/receiver/reception", { hours }),
  getRssiByDistance: (hours) => getJSON("/api/receiver/rssi-by-distance", { hours }),
  getReceptionDome: (hours) => getJSON("/api/receiver/reception-dome", { hours }),
  getDayNightRange: (hours) => getJSON("/api/receiver/day-night-range", { hours }),
  getWeeklyTrend: (weeks) => getJSON("/api/receiver/weekly-trend", { weeks }),
  getMetar: () => getJSON("/api/weather/metar"),
  getHourOfDay: (days) => getJSON("/api/distribution/hour-of-day", { days }),
  getAltitudeHistogram: (hours) => getJSON("/api/distribution/altitude", { hours }),
  getSpeedHistogram: (hours) => getJSON("/api/distribution/speed", { hours }),
  getHeatmap: (params) => getJSON("/api/heatmap", params),
  getTrafficDaily: (days) => getJSON("/api/traffic/daily", { days }),
  getTrafficDailySummary: (day) => getJSON("/api/traffic/daily-summary", { day }),
  getAircraftTypeDistribution: (day, limit) => getJSON("/api/distribution/aircraft-type", { day, limit }),
  getAircraftFrequent: (days, limit) => getJSON("/api/aircraft/frequent", { days, limit }),
  getAircraftHistory: (icao) => getJSON(`/api/aircraft/${encodeURIComponent(icao)}/history`),
  getAircraftPhoto: (icao) => getJSON(`/api/aircraft/${encodeURIComponent(icao)}/photo`),
  getAircraftPositions: (icao, hours) =>
    getJSON(`/api/aircraft/${encodeURIComponent(icao)}/positions`, { hours }),
  getAircraftNationalities: () => getJSON("/api/aircraft/nationalities"),
  getBadges: () => getJSON("/api/badges"),
  getArchive: (params) => getJSON("/api/aircraft/archive", params),
  getOnThisDay: () => getJSON("/api/aircraft/on-this-day"),
  getTrafficMonthly: (year, month) => getJSON("/api/traffic/monthly", { year, month }),
  getTrafficYearly: (year) => getJSON("/api/traffic/yearly", { year }),
  getFavorites: () => getJSON("/api/favorites"),
  addFavorite: (icao) =>
    requestJSON(new URL(`/api/favorites/${encodeURIComponent(icao)}`, window.location.origin), {
      method: "POST",
    }),
  removeFavorite: (icao) =>
    requestJSON(new URL(`/api/favorites/${encodeURIComponent(icao)}`, window.location.origin), {
      method: "DELETE",
    }),
};
