// daily.js -- entrypoint for daily.html: today's live summary, comparisons
// with yesterday and the same weekday last week, and the day's farthest/
// closest/most-observed aircraft. All from GET /api/traffic/daily-summary
// (Milestone M), called three times and diffed client-side -- there's no
// dedicated comparison endpoint, matching this API's GET-only philosophy.

import { api } from "./api.js";
import { createAircraftInfoTrigger } from "./aircraftinfo.js";
import { axisStyle, baseChartOption, CHART_COLORS, createChart } from "./chart.js";

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

function renderHighlight(elId, icao, valueText) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (!icao) {
    el.textContent = "データがありません";
    return;
  }
  const icaoEl = document.createElement("div");
  icaoEl.className = "daily-highlight__icao";
  icaoEl.appendChild(createAircraftInfoTrigger(icao));
  const metaEl = document.createElement("div");
  metaEl.className = "daily-highlight__meta";
  metaEl.textContent = valueText;
  el.replaceChildren(icaoEl, metaEl);
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

  const aircraftTypeChart = createAircraftTypeChart("aircraft-type-chart");
  let todayDay = null;

  try {
    const today = await api.getTrafficDailySummary();
    todayDay = today.day;
    setText("summary-day", today.day);
    setText("card-unique", String(today.unique_aircraft_count));
    setText("card-concurrent", String(today.max_concurrent_count));
    setText("card-messages", today.message_count_total.toLocaleString("ja-JP"));
    setText("card-position-max", String(today.position_aircraft_count_max));

    renderHighlight(
      "highlight-farthest",
      today.farthest_icao,
      today.farthest_distance_km != null ? `${today.farthest_distance_km.toFixed(1)} km` : ""
    );
    renderHighlight(
      "highlight-closest",
      today.closest_icao,
      today.closest_distance_km != null ? `${today.closest_distance_km.toFixed(1)} km` : ""
    );
    renderHighlight(
      "highlight-most-observed",
      today.most_observed_icao,
      today.most_observed_count != null ? `${today.most_observed_count}回観測` : ""
    );

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
