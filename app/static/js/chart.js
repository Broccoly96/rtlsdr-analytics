// chart.js -- ECharts traffic chart (active vs position counts per
// minute). Uses the global `echarts` loaded via a classic <script> tag in
// index.html (echarts still ships a UMD bundle, unlike maplibre-gl v6
// which is ESM-only).

import { api } from "./api.js";

let displayTimezone = "UTC";

export function setTimezone(tz) {
  displayTimezone = tz;
}

function formatAxisTime(isoString) {
  try {
    return new Date(isoString).toLocaleTimeString("ja-JP", {
      timeZone: displayTimezone,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

function showChartError(message) {
  const errorEl = document.getElementById("chart-error");
  if (!errorEl) return;
  errorEl.textContent = message;
  errorEl.hidden = false;
}

function hideChartError() {
  const errorEl = document.getElementById("chart-error");
  if (errorEl) errorEl.hidden = true;
}

export function createTrafficChart(containerId) {
  const container = document.getElementById(containerId);
  if (!container || typeof echarts === "undefined") {
    showChartError("グラフの初期化に失敗しました。");
    return { setData: () => {}, resize: () => {} };
  }

  let chart;
  try {
    chart = echarts.init(container, null, { renderer: "canvas" });
  } catch (err) {
    console.error("chart init failed", err);
    showChartError("グラフの初期化に失敗しました。");
    return { setData: () => {}, resize: () => {} };
  }

  function setData(traffic) {
    try {
      hideChartError();
      const times = traffic.buckets.map((b) => formatAxisTime(b.bucket_at));
      const active = traffic.buckets.map((b) => b.active_aircraft_count);
      const position = traffic.buckets.map((b) => b.position_aircraft_count);

      chart.setOption({
        backgroundColor: "transparent",
        textStyle: { color: "#e8f0fa" },
        grid: { left: 40, right: 16, top: 30, bottom: 30 },
        tooltip: {
          trigger: "axis",
          formatter: (params) => {
            const time = params[0] ? params[0].axisValueLabel : "";
            const lines = params.map((p) => `${p.marker}${p.seriesName}: ${p.data}`);
            return [time, ...lines].join("<br/>");
          },
        },
        legend: {
          data: ["受信中", "位置取得中"],
          textStyle: { color: "#8fa3bd" },
          top: 0,
        },
        xAxis: {
          type: "category",
          data: times,
          axisLine: { lineStyle: { color: "#263750" } },
          axisLabel: { color: "#8fa3bd" },
        },
        yAxis: {
          type: "value",
          minInterval: 1,
          axisLine: { lineStyle: { color: "#263750" } },
          axisLabel: { color: "#8fa3bd" },
          splitLine: { lineStyle: { color: "#162338" } },
        },
        series: [
          {
            name: "受信中",
            type: "line",
            data: active,
            showSymbol: false,
            lineStyle: { color: "#60a5fa" },
            areaStyle: { color: "rgba(96, 165, 250, 0.15)" },
          },
          {
            name: "位置取得中",
            type: "line",
            data: position,
            showSymbol: false,
            lineStyle: { color: "#22d3ee" },
          },
        ],
      });
    } catch (err) {
      console.error("chart render failed", err);
      showChartError("グラフの描画に失敗しました。");
    }
  }

  function resize() {
    if (chart) chart.resize();
  }

  return { setData, resize };
}

export async function refreshTraffic(chartController, hours) {
  try {
    const traffic = await api.getTraffic(hours);
    chartController.setData(traffic);
  } catch (err) {
    console.error("traffic refresh failed", err);
    showChartError("交通量データの取得に失敗しました。");
  }
}
