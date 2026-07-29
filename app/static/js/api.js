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

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { signal: controller.signal });
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
    return await response.json();
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
  getHourOfDay: (days) => getJSON("/api/distribution/hour-of-day", { days }),
  getAltitudeHistogram: (hours) => getJSON("/api/distribution/altitude", { hours }),
  getSpeedHistogram: (hours) => getJSON("/api/distribution/speed", { hours }),
};
