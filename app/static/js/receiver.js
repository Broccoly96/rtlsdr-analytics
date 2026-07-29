// receiver.js -- entrypoint for receiver.html: max range by bearing (polar
// bar chart), max range by altitude band (horizontal bar chart), and
// message-count/position-rate over time (line chart). All three use
// chart.js's createChart factory (Milestone H), so error handling/resize
// behave the same as the dashboard's traffic chart.

import { api } from "./api.js";
import { axisStyle, baseChartOption, CHART_COLORS, createChart, formatAxisTime, setTimezone } from "./chart.js";

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

function createBearingChart(containerId) {
  return createChart(containerId, "bearing-chart-error", (data) => ({
    ...baseChartOption(),
    tooltip: {
      trigger: "item",
      formatter: (p) => `${p.name}: ${p.value != null ? p.value.toFixed(1) + " km" : "データなし"}`,
    },
    polar: {},
    angleAxis: {
      type: "category",
      data: data.sectors.map((s) => `${Math.round(s.sector_center_deg)}°`),
      startAngle: 90,
      ...axisStyle(),
    },
    radiusAxis: { type: "value", ...axisStyle() },
    series: [
      {
        type: "bar",
        coordinateSystem: "polar",
        data: data.sectors.map((s) => s.max_distance_km),
        itemStyle: { color: CHART_COLORS.seriesA },
      },
    ],
  }));
}

function createAltitudeChart(containerId, bandLabels) {
  return createChart(containerId, "altitude-chart-error", (data) => ({
    ...baseChartOption(),
    tooltip: {
      trigger: "axis",
      formatter: (p) => {
        const point = p[0];
        return `${point.name}: ${point.data != null ? point.data.toFixed(1) + " km" : "データなし"}`;
      },
    },
    xAxis: { type: "value", ...axisStyle() },
    yAxis: {
      type: "category",
      data: data.bands.map((b) => bandLabels[b.band_key] || b.band_key),
      ...axisStyle(),
    },
    series: [
      {
        type: "bar",
        data: data.bands.map((b) => b.max_distance_km),
        itemStyle: { color: CHART_COLORS.seriesB },
      },
    ],
  }));
}

function createReceptionChart(containerId) {
  return createChart(containerId, "reception-chart-error", (data) => {
    const times = data.buckets.map((b) => formatAxisTime(b.bucket_at));
    const messageCounts = data.buckets.map((b) => b.message_count);
    const positionRates = data.buckets.map((b) => (b.position_rate != null ? b.position_rate * 100 : null));

    return {
      ...baseChartOption(),
      tooltip: { trigger: "axis" },
      legend: {
        data: ["メッセージ数", "位置取得率(%)"],
        textStyle: { color: CHART_COLORS.axisLabel },
        top: 0,
      },
      xAxis: { type: "category", data: times, ...axisStyle() },
      yAxis: [
        { type: "value", name: "メッセージ数", ...axisStyle() },
        { type: "value", name: "%", min: 0, max: 100, ...axisStyle() },
      ],
      series: [
        {
          name: "メッセージ数",
          type: "bar",
          data: messageCounts,
          yAxisIndex: 0,
          itemStyle: { color: CHART_COLORS.seriesA },
        },
        {
          name: "位置取得率(%)",
          type: "line",
          data: positionRates,
          yAxisIndex: 1,
          showSymbol: false,
          lineStyle: { color: CHART_COLORS.seriesB },
        },
      ],
    };
  });
}

async function refreshAll(charts, bandLabels, hours) {
  try {
    const bearing = await api.getBearingRange(hours);
    charts.bearing.setData(bearing);
  } catch (err) {
    console.error("bearing-range refresh failed", err);
  }
  try {
    const altitude = await api.getAltitudeRange(hours);
    charts.altitude.setData(altitude);
  } catch (err) {
    console.error("altitude-range refresh failed", err);
  }
  try {
    const reception = await api.getReception(hours);
    charts.reception.setData(reception);
  } catch (err) {
    console.error("reception refresh failed", err);
  }
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config", err);
    config = { display_timezone: "UTC", altitude_bands: [], version: null, git_revision: null };
  }

  renderVersion(config);
  setTimezone(config.display_timezone);

  const bandLabels = {};
  for (const band of config.altitude_bands || []) {
    bandLabels[band.key] = band.label;
  }

  const charts = {
    bearing: createBearingChart("bearing-chart"),
    altitude: createAltitudeChart("altitude-chart", bandLabels),
    reception: createReceptionChart("reception-chart"),
  };

  let currentHours = 24;
  await refreshAll(charts, bandLabels, currentHours);

  const periodButtons = document.querySelectorAll(".period-btn");
  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      periodButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      currentHours = Number(button.dataset.hours);
      refreshAll(charts, bandLabels, currentHours);
    });
  });

  window.addEventListener("resize", () => {
    charts.bearing.resize();
    charts.altitude.resize();
    charts.reception.resize();
  });
}

main().catch((err) => {
  console.error("receiver page failed to start", err);
});
