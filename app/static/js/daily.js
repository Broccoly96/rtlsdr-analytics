// daily.js -- entrypoint for daily.html: today's live summary, comparisons
// with yesterday and the same weekday last week, and the day's farthest/
// closest/most-observed aircraft. All from GET /api/traffic/daily-summary
// (Milestone M), called three times and diffed client-side -- there's no
// dedicated comparison endpoint, matching this API's GET-only philosophy.

import { api } from "./api.js";
import { createAircraftInfoTrigger } from "./aircraftinfo.js";
import { axisStyle, baseChartOption, CHART_COLORS, createChart } from "./chart.js";
import { formatDistance, formatAltitude } from "./units.js";

let displayTimezone = "UTC";

function formatTime(isoString) {
  if (!isoString) return "--";
  try {
    return new Date(isoString).toLocaleString("ja-JP", { timeZone: displayTimezone, hour12: false });
  } catch {
    return isoString;
  }
}

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
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

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function renderHighlight(elId, icao, callsign, valueText) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (!icao) {
    el.textContent = "データがありません";
    return;
  }
  const icaoEl = document.createElement("div");
  icaoEl.className = "daily-highlight__icao";
  icaoEl.appendChild(createAircraftInfoTrigger(icao, callsign || icao));
  const metaEl = document.createElement("div");
  metaEl.className = "daily-highlight__meta";
  metaEl.textContent = valueText;
  el.replaceChildren(icaoEl, metaEl);
}

function renderFirstSeenToday(rows) {
  const table = document.getElementById("first-seen-today");
  const emptyEl = document.getElementById("first-seen-today-empty");
  if (!table) return;
  const tbody = table.querySelector("tbody");
  tbody.replaceChildren();
  table.hidden = rows.length === 0;
  if (emptyEl) emptyEl.hidden = rows.length > 0;

  for (const row of rows) {
    const tr = document.createElement("tr");
    const icaoCell = document.createElement("td");
    icaoCell.appendChild(createAircraftInfoTrigger(row.icao, row.callsign || row.icao));
    const timeCell = document.createElement("td");
    timeCell.textContent = formatTime(row.first_seen_at);
    tr.append(icaoCell, timeCell);
    tbody.appendChild(tr);
  }
}

// Minimal line chart, no legend/axis-name chrome -- "a small sparkline",
// not a full traffic chart.
function createTrendChart(containerId) {
  return createChart(containerId, "trend-chart-error", (days) => ({
    ...baseChartOption(),
    grid: { left: 32, right: 16, top: 12, bottom: 24 },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: days.map((d) => d.day.slice(5)), // "MM-DD"
      ...axisStyle(),
    },
    yAxis: { type: "value", minInterval: 1, ...axisStyle() },
    series: [
      {
        type: "line",
        data: days.map((d) => d.unique_aircraft_count),
        showSymbol: true,
        symbolSize: 6,
        lineStyle: { color: CHART_COLORS.seriesA },
        areaStyle: { color: "rgba(96, 165, 250, 0.15)" },
        itemStyle: {
          color: (params) =>
            params.dataIndex === days.length - 1 ? CHART_COLORS.seriesB : CHART_COLORS.seriesA,
        },
      },
    ],
  }));
}

function createAircraftTypeChart(containerId) {
  return createChart(containerId, "aircraft-type-chart-error", (data) => ({
    ...baseChartOption(),
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: data.types.map((t) => t.type_code),
      ...axisStyle(),
    },
    yAxis: { type: "value", minInterval: 1, ...axisStyle() },
    series: [
      {
        type: "bar",
        data: data.types.map((t) => t.aircraft_count),
        itemStyle: { color: CHART_COLORS.seriesA },
      },
    ],
  }));
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config", err);
    config = { version: null, git_revision: null };
  }
  renderVersion(config);
  displayTimezone = config.display_timezone || "UTC";

  const aircraftTypeChart = createAircraftTypeChart("aircraft-type-chart");
  const trendChart = createTrendChart("trend-chart");
  let todayDay = null;
  let todaySummary = null;

  try {
    const today = await api.getTrafficDailySummary();
    todaySummary = today;
    todayDay = today.day;
    setText("summary-day", today.day);
    setText("card-unique", String(today.unique_aircraft_count));
    setText("card-concurrent", String(today.max_concurrent_count));
    setText("card-messages", today.message_count_total.toLocaleString("ja-JP"));
    setText("card-position-max", String(today.position_aircraft_count_max));

    renderHighlight(
      "highlight-farthest",
      today.farthest_icao,
      today.farthest_callsign,
      today.farthest_distance_km != null ? formatDistance(today.farthest_distance_km) : ""
    );
    renderHighlight(
      "highlight-closest",
      today.closest_icao,
      today.closest_callsign,
      today.closest_distance_km != null ? formatDistance(today.closest_distance_km) : ""
    );
    renderHighlight(
      "highlight-most-observed",
      today.most_observed_icao,
      today.most_observed_callsign,
      today.most_observed_count != null ? `${today.most_observed_count}回観測` : ""
    );
    renderHighlight(
      "highlight-fastest",
      today.fastest_icao,
      today.fastest_callsign,
      today.fastest_ground_speed_kt != null ? `${Math.round(today.fastest_ground_speed_kt)} kt` : ""
    );
    renderHighlight(
      "highlight-highest",
      today.highest_icao,
      today.highest_callsign,
      today.highest_altitude_ft != null ? formatAltitude(today.highest_altitude_ft) : ""
    );
    renderFirstSeenToday(today.first_seen_today || []);

    const [yesterday, lastWeek] = await Promise.all([
      api.getTrafficDailySummary(addDaysToIsoDate(today.day, -1)),
      api.getTrafficDailySummary(addDaysToIsoDate(today.day, -7)),
    ]);

    const deltasEl = document.getElementById("daily-deltas");
    if (deltasEl) {
      deltasEl.replaceChildren(
        formatDelta("前日比", today.unique_aircraft_count, yesterday.unique_aircraft_count),
        formatDelta("先週同曜日比", today.unique_aircraft_count, lastWeek.unique_aircraft_count)
      );
    }
  } catch (err) {
    console.error("daily summary refresh failed", err);
  }

  try {
    // Ends yesterday (traffic_day only ever holds finished days) --
    // splice in today's already-fetched live count as the 7th point.
    const past = await api.getTrafficDaily(6);
    const trendDays = todaySummary ? [...past.daily, todaySummary] : past.daily;
    trendChart.setData(trendDays);
  } catch (err) {
    console.error("trend chart refresh failed", err);
  }

  try {
    const aircraftTypes = await api.getAircraftTypeDistribution(todayDay, 10);
    const hasData = aircraftTypes.types.length > 0;
    const chartContainer = document.getElementById("aircraft-type-chart");
    const emptyEl = document.getElementById("aircraft-type-empty");
    if (chartContainer) chartContainer.hidden = !hasData;
    if (emptyEl) emptyEl.hidden = hasData;
    if (hasData) aircraftTypeChart.setData(aircraftTypes);
  } catch (err) {
    console.error("aircraft type distribution refresh failed", err);
  }
}

main().catch((err) => {
  console.error("daily page failed to start", err);
});
