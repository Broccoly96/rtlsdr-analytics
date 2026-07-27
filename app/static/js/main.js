// main.js -- entrypoint: loads /api/config, wires map/chart/ui together,
// and drives the period switch + refresh loop.

import { api } from "./api.js";
import { ui } from "./ui.js";
import { createTrackMap, refreshTracks, setTimezone as setMapTimezone } from "./map.js";
import { createTrafficChart, refreshTraffic, setTimezone as setChartTimezone } from "./chart.js";

const TRAFFIC_WINDOW_HOURS = 24;
const AUTO_REFRESH_INTERVAL_MS = 30000;
const DEFAULT_CONFIG = {
  map_style_url: "https://tiles.openfreemap.org/styles/positron",
  display_timezone: "UTC",
};

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config; using built-in defaults", err);
    config = DEFAULT_CONFIG;
  }

  ui.setTimezone(config.display_timezone);
  setChartTimezone(config.display_timezone);
  setMapTimezone(config.display_timezone);

  const mapController = createTrackMap({ containerId: "map", styleUrl: config.map_style_url });
  const chartController = createTrafficChart("chart");

  let currentTracksHours = 6;

  const periodButtons = document.querySelectorAll(".period-btn");
  periodButtons.forEach((button) => {
    button.addEventListener("click", () => {
      periodButtons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      currentTracksHours = Number(button.dataset.hours);
      refreshTracks(mapController, currentTracksHours);
    });
  });

  window.addEventListener("resize", () => {
    mapController.resize();
    chartController.resize();
  });

  await Promise.all([
    refreshTracks(mapController, currentTracksHours),
    refreshTraffic(chartController, TRAFFIC_WINDOW_HOURS),
    ui.refreshStatusAndRankings(),
  ]);

  ui.startPolling();

  setInterval(() => {
    if (!document.hidden) {
      refreshTracks(mapController, currentTracksHours);
      refreshTraffic(chartController, TRAFFIC_WINDOW_HOURS);
    }
  }, AUTO_REFRESH_INTERVAL_MS);
}

main().catch((err) => {
  console.error("dashboard failed to start", err);
});
