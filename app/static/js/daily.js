// daily.js -- entrypoint for daily.html: today's live summary, comparisons
// with yesterday and the same weekday last week, and the day's farthest/
// closest/most-observed aircraft. All from GET /api/traffic/daily-summary
// (Milestone M), called three times and diffed client-side -- there's no
// dedicated comparison endpoint, matching this API's GET-only philosophy.

import { api } from "./api.js";
import { ui } from "./ui.js";
import { createAircraftInfoTrigger } from "./aircraftinfo.js";
import { setNationalityBlocks } from "./nationality.js";
import { axisStyle, baseChartOption, CHART_COLORS, colorWithAlpha, createChart } from "./chart.js";
import { formatDistance, formatAltitude } from "./units.js";
import { registerServiceWorker } from "./pwa.js";
import { downloadHighlightImage } from "./highlight-image.js";
import { getParam, setParam } from "./url-state.js";
import { t, currentLocale, applyStaticTranslations } from "./i18n.js";

const formatTime = ui.formatTime;

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
    el.textContent = t("common.noData");
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
    grid: { left: 32, right: 16, top: 12, bottom: 24, containLabel: true },
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
        areaStyle: { color: colorWithAlpha(CHART_COLORS.seriesA, 0.15) },
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

function renderPeriodSummary(summary) {
  const el = document.getElementById("period-summary");
  if (!el) return;
  el.textContent = t("daily.period.summaryLine", {
    days: summary.days_with_data,
    unique: summary.unique_aircraft_count,
    messages: summary.message_count_total.toLocaleString(currentLocale()),
    concurrent: summary.max_concurrent_count,
    farthest: summary.farthest_icao
      ? `${summary.farthest_icao} (${summary.farthest_distance_km.toFixed(1)} km)`
      : "--",
  });
}

function wirePeriodSummary() {
  const modeSelect = document.getElementById("period-mode");
  const yearInput = document.getElementById("period-year");
  const monthSelect = document.getElementById("period-month");
  const refreshButton = document.getElementById("period-refresh");
  const errorEl = document.getElementById("period-error");
  if (!modeSelect || !yearInput || !monthSelect || !refreshButton) return;

  const now = new Date();
  yearInput.value = String(now.getFullYear());
  monthSelect.value = String(now.getMonth() + 1);

  refreshButton.addEventListener("click", async () => {
    if (errorEl) errorEl.hidden = true;
    const year = Number(yearInput.value);
    try {
      const summary =
        modeSelect.value === "year"
          ? await api.getTrafficYearly(year)
          : await api.getTrafficMonthly(year, Number(monthSelect.value));
      renderPeriodSummary(summary);
    } catch (err) {
      console.error("period summary fetch failed", err);
      if (errorEl) {
        errorEl.textContent = err && err.message ? err.message : t("chart.trafficFetchFailed");
        errorEl.hidden = false;
      }
    }
  });
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config", err);
    config = { version: null, git_revision: null };
  }
  applyStaticTranslations();
  renderVersion(config);
  setNationalityBlocks(config.nationality_blocks);
  registerServiceWorker();
  ui.setTimezone(config.display_timezone || "UTC");

  const saveImageButton = document.getElementById("save-highlight-image");
  if (saveImageButton) {
    saveImageButton.addEventListener("click", () => downloadHighlightImage());
  }

  wirePeriodSummary();

  const aircraftTypeChart = createAircraftTypeChart("aircraft-type-chart");
  const trendChart = createTrendChart("trend-chart");
  let todayDay = null;
  let todaySummary = null;

  try {
    // Permalink support (Milestone RR): ?day=YYYY-MM-DD views a specific
    // past day instead of today, e.g. for sharing a link to a notable day.
    const dayFromUrl = getParam("day");
    const today = await api.getTrafficDailySummary(dayFromUrl || undefined);
    todaySummary = today;
    todayDay = today.day;
    setParam("day", dayFromUrl ? today.day : null);
    setText("summary-day", today.day);
    setText("card-unique", String(today.unique_aircraft_count));
    setText("card-concurrent", String(today.max_concurrent_count));
    setText("card-messages", today.message_count_total.toLocaleString(currentLocale()));
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
      today.most_observed_count != null ? t("daily.timesObserved", { count: today.most_observed_count }) : ""
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
        formatDelta(t("daily.deltaVsYesterday"), today.unique_aircraft_count, yesterday.unique_aircraft_count),
        formatDelta(t("daily.deltaVsLastWeek"), today.unique_aircraft_count, lastWeek.unique_aircraft_count)
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
