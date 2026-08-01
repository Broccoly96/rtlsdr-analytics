// main.js -- entrypoint: loads /api/config, wires map/chart/ui together,
// and drives the period switch + refresh loop.
//
// map.js is loaded via a *dynamic* import, not a static one: it in turn
// statically imports MapLibre GL JS from a CDN, and ES modules fail their
// entire static-import graph atomically -- if that one CDN fetch failed
// (network hiccup, ad/tracker blocker, offline CDN), a static import here
// would silently prevent this whole file from ever running at all (no
// status cards, no chart, nothing), which directly breaks PLAN.md D-2's
// "地図失敗時もグラフとランキングを利用可能にする" requirement. Dynamic
// import isolates that failure to the map panel only.

import { api } from "./api.js";
import { ui } from "./ui.js";
import { renderAltitudeLegend } from "./altitude-legend.js";
import { registerServiceWorker } from "./pwa.js";
import {
  axisStyle,
  baseChartOption,
  CHART_COLORS,
  createChart,
  createTrafficChart,
  refreshTraffic,
  setTimezone as setChartTimezone,
  trafficChartOption,
} from "./chart.js";

// CSP violations (e.g. a browser extension or local policy blocking a
// same-origin script/style/connect target) don't throw a catchable JS error
// and don't show up in showMapLoadError's try/catch -- they only appear as a
// browser-generated console line, invisible without devtools. Surface them
// on-page too, since "map fails to load but the server serves everything
// correctly" was hard to diagnose without asking the user to open devtools.
document.addEventListener("securitypolicyviolation", (event) => {
  const detail = `CSPにより読み込みがブロックされました: ${event.blockedURI}(directive: ${event.violatedDirective})`;
  console.error(detail, event);
  const errorEl = document.getElementById("map-error");
  if (errorEl && errorEl.hidden) {
    errorEl.textContent = `${detail} -- ブラウザの拡張機能やセキュリティソフトが関与している可能性があります。`;
    errorEl.hidden = false;
  }
});

const TRAFFIC_WINDOW_HOURS = 24;
const AUTO_REFRESH_INTERVAL_MS = 30000;
const DEFAULT_CONFIG = {
  map_style_url: "https://tiles.openfreemap.org/styles/positron",
  display_timezone: "UTC",
  altitude_bands: [],
  version: null,
  git_revision: null,
};

// Shown in the header so it's possible to confirm which exact build a
// given browser tab is actually looking at (e.g. when debugging a remote
// preview and wondering whether a fix has actually been redeployed yet).
function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

function showMapLoadError(err) {
  console.error("failed to load map module", err);
  const errorEl = document.getElementById("map-error");
  if (errorEl) {
    const detail = err && err.message ? err.message : String(err);
    errorEl.textContent = `地図モジュールの読み込みに失敗しました: ${detail}(他の情報は利用できます)`;
    errorEl.hidden = false;
  }
}

async function loadMapModule() {
  // A plain fetch() isn't subject to ES module linking-graph error wrapping
  // the way import() is, so on failure it gives a much more specific reason
  // (HTTP status, network error) than import()'s generic "Failed to fetch
  // dynamically imported module" message. NOTE: unlike import()'s specifier,
  // fetch() resolves a relative URL against the *document's* base URL, not
  // this module's URL -- import.meta.url must be passed explicitly as the
  // base or "./map.js" would resolve to the site root instead of this
  // module's own directory.
  try {
    const res = await fetch(new URL("./map.js", import.meta.url));
    if (!res.ok) {
      showMapLoadError(new Error(`map.jsの取得に失敗しました (HTTP ${res.status})`));
      return null;
    }
  } catch (err) {
    showMapLoadError(new Error(`map.jsへのネットワーク接続に失敗しました: ${err && err.message ? err.message : err}`));
    return null;
  }

  try {
    return await import("./map.js");
  } catch (err) {
    showMapLoadError(err);
    return null;
  }
}

// Hour-of-day / altitude / speed panels are a statistical pattern view,
// not something that needs 30s freshness like the traffic chart -- fetched
// once at startup only (see main()'s single refreshDistributionPanels() call).
function createHourOfDayChart(containerId) {
  return createChart(containerId, "hour-of-day-chart-error", (data) => ({
    ...baseChartOption(),
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: data.hours.map((h) => `${h.hour}時`),
      ...axisStyle(),
    },
    yAxis: { type: "value", minInterval: 1, ...axisStyle() },
    series: [
      {
        type: "bar",
        data: data.hours.map((h) => h.unique_aircraft_count),
        itemStyle: { color: CHART_COLORS.seriesA },
      },
    ],
  }));
}

function createHistogramChart(containerId, errorElId, unitLabel) {
  return createChart(containerId, errorElId, (data) => ({
    ...baseChartOption(),
    tooltip: {
      trigger: "axis",
      formatter: (p) => {
        const point = p[0];
        return `${point.name}${unitLabel}: ${point.data}`;
      },
    },
    xAxis: {
      type: "category",
      data: data.buckets.map((b) => Math.round(b.bucket_start)),
      ...axisStyle(),
    },
    yAxis: { type: "value", minInterval: 1, ...axisStyle() },
    series: [
      {
        type: "bar",
        data: data.buckets.map((b) => b.count),
        itemStyle: { color: CHART_COLORS.seriesA },
      },
    ],
  }));
}

async function refreshDistributionPanels(charts) {
  try {
    charts.hourOfDay.setData(await api.getHourOfDay(7));
  } catch (err) {
    console.error("hour-of-day refresh failed", err);
  }
  try {
    charts.altitudeHist.setData(await api.getAltitudeHistogram(24));
  } catch (err) {
    console.error("altitude histogram refresh failed", err);
  }
  try {
    charts.speedHist.setData(await api.getSpeedHistogram(24));
  } catch (err) {
    console.error("speed histogram refresh failed", err);
  }
}

const DAY_OF_WEEK_LABELS = ["日", "月", "火", "水", "木", "金", "土"]; // matches Postgres EXTRACT(DOW): 0=Sunday

function addOption(select, value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  select.appendChild(option);
}

function populateHeatmapFilterOptions(altitudeBands) {
  const bandSelect = document.getElementById("heatmap-altitude-band");
  const hourSelect = document.getElementById("heatmap-hour");
  const dowSelect = document.getElementById("heatmap-dow");
  if (!bandSelect || !hourSelect || !dowSelect) return;

  addOption(bandSelect, "", "高度: 全て");
  for (const band of altitudeBands || []) {
    addOption(bandSelect, band.key, band.label);
  }

  addOption(hourSelect, "", "時間帯: 全て");
  for (let hour = 0; hour < 24; hour++) {
    addOption(hourSelect, String(hour), `${hour}時台`);
  }

  addOption(dowSelect, "", "曜日: 全て");
  DAY_OF_WEEK_LABELS.forEach((label, dow) => addOption(dowSelect, String(dow), `${label}曜`));
}

// Heatmap is opt-in (toggle button) and re-fetched only while visible --
// avoids an extra query on every load for a feature most sessions won't use.
function setupHeatmapControls(mapController, altitudeBands) {
  populateHeatmapFilterOptions(altitudeBands);

  const toggle = document.getElementById("heatmap-toggle");
  const bandSelect = document.getElementById("heatmap-altitude-band");
  const hourSelect = document.getElementById("heatmap-hour");
  const dowSelect = document.getElementById("heatmap-dow");
  if (!toggle || !bandSelect || !hourSelect || !dowSelect) return;

  let enabled = false;

  async function refresh() {
    if (!enabled) return;
    try {
      const params = {
        hours: TRAFFIC_WINDOW_HOURS,
        altitude_band: bandSelect.value || undefined,
        hour_of_day: hourSelect.value !== "" ? Number(hourSelect.value) : undefined,
        day_of_week: dowSelect.value !== "" ? Number(dowSelect.value) : undefined,
      };
      const data = await api.getHeatmap(params);
      mapController.setHeatmap(data.cells);
    } catch (err) {
      console.error("heatmap refresh failed", err);
    }
  }

  toggle.addEventListener("click", () => {
    enabled = !enabled;
    toggle.setAttribute("aria-pressed", String(enabled));
    mapController.setHeatmapVisible(enabled);
    if (enabled) refresh();
  });

  for (const select of [bandSelect, hourSelect, dowSelect]) {
    select.addEventListener("change", refresh);
  }
}

function dailyTrafficChartOption(daily) {
  const days = daily.daily.map((d) => d.day);
  const counts = daily.daily.map((d) => d.unique_aircraft_count);
  return {
    ...baseChartOption(),
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: days, ...axisStyle() },
    yAxis: { type: "value", minInterval: 1, ...axisStyle() },
    series: [
      {
        name: "ユニーク機数",
        type: "bar",
        data: counts,
        itemStyle: { color: CHART_COLORS.seriesA },
      },
    ],
  };
}

// Adds `delta` whole days to an ISO "YYYY-MM-DD" date string, computed in
// UTC so it never depends on the browser's own timezone -- the input is
// always a `day` value the server already resolved via DISPLAY_TIMEZONE.
function addDaysToIsoDate(isoDate, delta) {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + delta);
  return d.toISOString().slice(0, 10);
}

function formatDelta(label, current, previous) {
  const span = document.createElement("span");
  span.className = "traffic-delta";
  if (previous == null || previous === 0) {
    span.textContent = `${label}: --`;
    return span;
  }
  const pct = ((current - previous) / previous) * 100;
  const sign = pct > 0 ? "+" : "";
  span.textContent = `${label}: ${sign}${pct.toFixed(0)}%`;
  span.classList.add(pct > 0 ? "delta-up" : pct < 0 ? "delta-down" : "delta-flat");
  return span;
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config; using built-in defaults", err);
    config = DEFAULT_CONFIG;
  }

  renderVersion(config);
  registerServiceWorker();
  ui.setTimezone(config.display_timezone);
  setChartTimezone(config.display_timezone);

  const chartController = createTrafficChart("chart");
  const distributionCharts = {
    hourOfDay: createHourOfDayChart("hour-of-day-chart"),
    altitudeHist: createHistogramChart("altitude-hist-chart", "altitude-hist-chart-error", "ft"),
    speedHist: createHistogramChart("speed-hist-chart", "speed-hist-chart-error", "kt"),
  };
  let mapController = {
    setTracks: () => {},
    resize: () => {},
    setHeatmap: () => {},
    setHeatmapVisible: () => {},
  };
  let currentTracksHours = 6;

  renderAltitudeLegend(document.getElementById("altitude-legend"), config.altitude_bands);

  const mapModule = await loadMapModule();
  let refreshTracks = async () => {};
  if (mapModule) {
    mapModule.setTimezone(config.display_timezone);
    mapModule.setAltitudeBands(config.altitude_bands);
    mapController = mapModule.createTrackMap({ containerId: "map", styleUrl: config.map_style_url });
    refreshTracks = mapModule.refreshTracks;
    await refreshTracks(mapController, currentTracksHours);
  }

  // Scoped to the header's period group specifically: #heatmap-toggle
  // below also uses the `.period-btn` class for shared styling only, and
  // must not be swept up by this handler (it has no data-hours, and isn't
  // part of the mutually-exclusive tracks-period button group).
  const periodButtons = document.querySelectorAll(".app-header__period .period-btn");
  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      periodButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      currentTracksHours = Number(button.dataset.hours);
      refreshTracks(mapController, currentTracksHours);
    });
  });

  setupHeatmapControls(mapController, config.altitude_bands);

  window.addEventListener("resize", () => {
    mapController.resize();
    chartController.resize();
    distributionCharts.hourOfDay.resize();
    distributionCharts.altitudeHist.resize();
    distributionCharts.speedHist.resize();
  });

  // "24時間ユニーク機数" card is always the last-24h figure, independent of
  // whichever granularity the chart panel itself is currently showing.
  async function refreshCardUnique() {
    try {
      const traffic = await api.getTraffic(TRAFFIC_WINDOW_HOURS);
      ui.setUniqueCount(traffic.unique_aircraft_count);
    } catch (err) {
      console.error("traffic (unique card) refresh failed", err);
    }
  }

  let currentGranularity = "day";

  async function refreshTrafficPanel() {
    if (currentGranularity === "day") {
      await refreshTraffic(chartController, TRAFFIC_WINDOW_HOURS);
      return;
    }
    const days = currentGranularity === "week" ? 7 : 30;
    try {
      const daily = await api.getTrafficDaily(days);
      chartController.setData(daily);
    } catch (err) {
      console.error("daily traffic refresh failed", err);
    }
  }

  const granularityButtons = document.querySelectorAll(".granularity-btn");
  granularityButtons.forEach((button) => {
    button.addEventListener("click", () => {
      granularityButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      currentGranularity = button.dataset.granularity;
      chartController.setBuildOption(
        currentGranularity === "day" ? trafficChartOption : dailyTrafficChartOption
      );
      refreshTrafficPanel();
    });
  });

  async function refreshTrafficDeltas() {
    const el = document.getElementById("traffic-deltas");
    if (!el) return;
    try {
      const today = await api.getTrafficDailySummary();
      const [yesterday, lastWeek] = await Promise.all([
        api.getTrafficDailySummary(addDaysToIsoDate(today.day, -1)),
        api.getTrafficDailySummary(addDaysToIsoDate(today.day, -7)),
      ]);
      el.replaceChildren(
        formatDelta("前日比", today.unique_aircraft_count, yesterday.unique_aircraft_count),
        formatDelta("先週同曜日比", today.unique_aircraft_count, lastWeek.unique_aircraft_count)
      );
    } catch (err) {
      console.error("traffic deltas refresh failed", err);
    }
  }

  await Promise.all([
    refreshCardUnique(),
    refreshTrafficPanel(),
    refreshTrafficDeltas(),
    ui.refreshStatusAndRankings(),
    refreshDistributionPanels(distributionCharts),
  ]);

  ui.startPolling();

  setInterval(() => {
    if (!document.hidden) {
      refreshTracks(mapController, currentTracksHours);
      refreshCardUnique();
      refreshTrafficPanel();
      refreshTrafficDeltas();
    }
  }, AUTO_REFRESH_INTERVAL_MS);
}

main().catch((err) => {
  console.error("dashboard failed to start", err);
});
