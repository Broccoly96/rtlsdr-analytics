// receiver.js -- entrypoint for receiver.html: max range by bearing (polar
// bar chart), max range by altitude band (horizontal bar chart), and
// message-count/position-rate over time (line chart). All three use
// chart.js's createChart factory (Milestone H), so error handling/resize
// behave the same as the dashboard's traffic chart.

import { api } from "./api.js";
import { axisStyle, baseChartOption, CHART_COLORS, createChart, formatAxisTime, setTimezone } from "./chart.js";
import { distanceUnitLabel, formatDistance, toDisplayDistance } from "./units.js";
import { registerServiceWorker } from "./pwa.js";

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
      formatter: (p) =>
        `${p.name}: ${data.sectors[p.dataIndex].max_distance_km != null ? formatDistance(data.sectors[p.dataIndex].max_distance_km) : "データなし"}`,
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
        data: data.sectors.map((s) => toDisplayDistance(s.max_distance_km)),
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
        const raw = data.bands[point.dataIndex].max_distance_km;
        return `${point.name}: ${raw != null ? formatDistance(raw) : "データなし"}`;
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
        data: data.bands.map((b) => toDisplayDistance(b.max_distance_km)),
        itemStyle: { color: CHART_COLORS.seriesB },
      },
    ],
  }));
}

// Same density ramp as map.js's HEATMAP_COLOR_RAMP (this app's one
// "density/intensity" color convention), reused here for consistency.
const RSSI_HEATMAP_COLOR_RAMP = ["#60a5fa", "#22d3ee", "#34d399", "#fbbf24", "#fb7185"];

function createRssiHeatmapChart(containerId) {
  return createChart(containerId, "rssi-chart-error", (data) => {
    const distanceValues = [...new Set(data.cells.map((c) => c.distance_bucket_km))].sort(
      (a, b) => a - b
    );
    const rssiValues = [...new Set(data.cells.map((c) => c.rssi_bucket_db))].sort((a, b) => a - b);
    const maxCount = data.cells.reduce((max, c) => Math.max(max, c.count), 0);

    const points = data.cells.map((c) => [
      distanceValues.indexOf(c.distance_bucket_km),
      rssiValues.indexOf(c.rssi_bucket_db),
      c.count,
    ]);

    return {
      ...baseChartOption(),
      tooltip: {
        position: "top",
        formatter: (p) => {
          const bucketStartKm = distanceValues[p.value[0]];
          const bucketEndKm = bucketStartKm + data.distance_bucket_km;
          return (
            `距離 ${formatDistance(bucketStartKm)}〜${formatDistance(bucketEndKm)}` +
            `<br/>RSSI ${rssiValues[p.value[1]]}〜${rssiValues[p.value[1]] + data.rssi_bucket_db} dB` +
            `<br/>件数: ${p.value[2]}`
          );
        },
      },
      grid: { left: 60, right: 16, top: 30, bottom: 40, containLabel: true },
      xAxis: {
        type: "category",
        name: `距離 (${distanceUnitLabel()})`,
        data: distanceValues.map((v) => Math.round(toDisplayDistance(v))),
        ...axisStyle(),
      },
      yAxis: {
        type: "category",
        name: "RSSI (dB)",
        data: rssiValues.map((v) => Math.round(v)),
        ...axisStyle(),
      },
      visualMap: {
        min: 0,
        max: maxCount || 1,
        calculable: false,
        orient: "horizontal",
        left: "center",
        bottom: 0,
        text: ["多", "少"],
        inRange: { color: RSSI_HEATMAP_COLOR_RAMP },
        textStyle: { color: CHART_COLORS.axisLabel },
      },
      series: [
        {
          type: "heatmap",
          data: points,
          progressive: 0,
        },
      ],
    };
  });
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
  try {
    const rssi = await api.getRssiByDistance(hours);
    charts.rssi.setData(rssi);
  } catch (err) {
    console.error("rssi-by-distance refresh failed", err);
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
  registerServiceWorker();
  setTimezone(config.display_timezone);

  const bandLabels = {};
  for (const band of config.altitude_bands || []) {
    bandLabels[band.key] = band.label;
  }

  const charts = {
    bearing: createBearingChart("bearing-chart"),
    altitude: createAltitudeChart("altitude-chart", bandLabels),
    reception: createReceptionChart("reception-chart"),
    rssi: createRssiHeatmapChart("rssi-chart"),
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
    charts.rssi.resize();
  });
}

main().catch((err) => {
  console.error("receiver page failed to start", err);
});
