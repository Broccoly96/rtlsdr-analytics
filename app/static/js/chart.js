// chart.js -- ECharts chart factory plus the traffic chart (active vs
// position counts per minute). Uses the global `echarts` loaded via a
// classic <script> tag in index.html (echarts still ships a UMD bundle,
// unlike maplibre-gl v6 which is ESM-only).

import { api } from "./api.js";
import { t, currentLocale } from "./i18n.js";

let displayTimezone = "UTC";

export function setTimezone(tz) {
  displayTimezone = tz;
}

export function formatAxisTime(isoString) {
  try {
    return new Date(isoString).toLocaleTimeString(currentLocale(), {
      timeZone: displayTimezone,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

// Design tokens shared with style.css's CSS custom properties -- kept as
// plain values here because ECharts options are JS objects, not CSS.
export const CHART_COLORS = {
  text: "#e8f0fa",
  axisLine: "#263750",
  axisLabel: "#8fa3bd",
  splitLine: "#162338",
  seriesA: "#60a5fa",
  seriesB: "#22d3ee",
};

function showError(errorElId, message) {
  const errorEl = document.getElementById(errorElId);
  if (!errorEl) return;
  errorEl.textContent = message;
  errorEl.hidden = false;
}

function hideError(errorElId) {
  const errorEl = document.getElementById(errorElId);
  if (errorEl) errorEl.hidden = true;
}

// Common chart chrome (background, text color, grid, axis styling). Each
// buildOption() callback spreads this in and overrides/extends the axis
// definitions with its own `type`/`data`, so callers keep full control over
// chart shape (line, bar, polar, heatmap, ...) while sharing one theme.
export function baseChartOption() {
  return {
    backgroundColor: "transparent",
    textStyle: { color: CHART_COLORS.text },
    grid: { left: 40, right: 16, top: 30, bottom: 30 },
  };
}

export function axisStyle() {
  return {
    axisLine: { lineStyle: { color: CHART_COLORS.axisLine } },
    axisLabel: { color: CHART_COLORS.axisLabel },
    splitLine: { lineStyle: { color: CHART_COLORS.splitLine } },
  };
}

// Creates an ECharts instance bound to `containerId`, reporting failures
// into `errorElId`. Returns null (never throws) on any failure so callers
// can fall back to a no-op controller -- same shape as map.js's approach.
function initChart(containerId, errorElId) {
  const container = document.getElementById(containerId);
  if (!container || typeof echarts === "undefined") {
    showError(errorElId, t("chart.initFailed"));
    return null;
  }
  try {
    return echarts.init(container, null, { renderer: "canvas" });
  } catch (err) {
    console.error("chart init failed", err);
    showError(errorElId, t("chart.initFailed"));
    return null;
  }
}

// Generic chart controller factory. `buildOption(data)` turns whatever
// shape of data the caller passes into `setData()` into an ECharts option
// object; this factory only owns instance creation, error display, and
// resize. Every chart on the site (traffic line chart, and any future
// polar/bar/heatmap chart) should be built through this, not by calling
// echarts.init() directly, so error handling and resize behave the same
// way everywhere.
//
// The returned controller also exposes setBuildOption(), so one chart
// instance/container can be repointed at a different data shape entirely
// (Milestone M's day/week/month traffic-panel granularity toggle reuses
// the single "chart" container for both the per-minute line chart and a
// per-day bar chart). setData() always calls chart.setOption(..., true)
// (notMerge) so switching shape can't leave stale series/axis config
// behind from the previous buildOption.
export function createChart(containerId, errorElId, buildOption) {
  const chart = initChart(containerId, errorElId);
  if (!chart) {
    return { setData: () => {}, resize: () => {}, setBuildOption: () => {} };
  }

  let currentBuildOption = buildOption;

  function setData(data) {
    try {
      hideError(errorElId);
      chart.setOption(currentBuildOption(data), true);
    } catch (err) {
      console.error("chart render failed", err);
      showError(errorElId, t("chart.renderFailed"));
    }
  }

  function setBuildOption(newBuildOption) {
    currentBuildOption = newBuildOption;
  }

  function resize() {
    chart.resize();
  }

  return { setData, resize, setBuildOption };
}

export function trafficChartOption(traffic) {
  const times = traffic.buckets.map((b) => formatAxisTime(b.bucket_at));
  const active = traffic.buckets.map((b) => b.active_aircraft_count);
  const position = traffic.buckets.map((b) => b.position_aircraft_count);

  return {
    ...baseChartOption(),
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const time = params[0] ? params[0].axisValueLabel : "";
        const lines = params.map((p) => `${p.marker}${p.seriesName}: ${p.data}`);
        return [time, ...lines].join("<br/>");
      },
    },
    legend: {
      data: [t("chart.active"), t("chart.positionAcquired")],
      textStyle: { color: CHART_COLORS.axisLabel },
      top: 0,
    },
    xAxis: {
      type: "category",
      data: times,
      ...axisStyle(),
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      ...axisStyle(),
    },
    series: [
      {
        name: t("chart.active"),
        type: "line",
        data: active,
        showSymbol: false,
        lineStyle: { color: CHART_COLORS.seriesA },
        areaStyle: { color: "rgba(96, 165, 250, 0.15)" },
      },
      {
        name: t("chart.positionAcquired"),
        type: "line",
        data: position,
        showSymbol: false,
        lineStyle: { color: CHART_COLORS.seriesB },
      },
    ],
  };
}

export function createTrafficChart(containerId) {
  return createChart(containerId, "chart-error", trafficChartOption);
}

export async function refreshTraffic(chartController, hours) {
  try {
    const traffic = await api.getTraffic(hours);
    chartController.setData(traffic);
    return traffic;
  } catch (err) {
    console.error("traffic refresh failed", err);
    showError("chart-error", t("chart.trafficFetchFailed"));
    return null;
  }
}
