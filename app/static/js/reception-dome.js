// reception-dome.js -- a 3rd attempt at visualizing reception range in 3D
// on receiver.html, after two prior attempts (echarts-gl scatter3D
// "hemisphere", then a CesiumJS mesh) were both built and removed for being
// hard to read (see README's Receiver performance section / PLAN.md). This
// attempt uses a structurally different encoding: a sparse point cloud of
// observation density + average RSSI binned by bearing x distance x
// altitude, rather than a single derived "max range per direction" surface
// -- so it's kept deliberately self-contained in this one file (plus one
// query, one route, one vendored library) to stay easy to remove again if
// it doesn't pan out a third time.
//
// Requires echarts-gl (loaded as a classic <script> global, same UMD
// convention as echarts itself) for the grid3D/scatter3D chart types.

import { createChart, CHART_COLORS } from "./chart.js";
import { toDisplayDistance } from "./units.js";
import { t } from "./i18n.js";

const FT_TO_KM = 0.0003048;

// grid3D auto-fits each axis's data range to its own box dimension
// (boxWidth/boxHeight/boxDepth) regardless of the real-world ratio between
// axes -- confirmed empirically before writing this file: multiplying the Z
// data by a fixed factor, while leaving boxHeight at its default, produced
// an *identical* rendered shape, just with different axis tick labels. The
// actual vertical-exaggeration lever is boxHeight itself, computed below
// from the true altitude/distance ratio -- not a multiplier baked into the
// data (avoiding the "trust the library docs" mistake the first attempt
// made with this same library).
const ALTITUDE_EXAGGERATION = 8;
const BOX_HEIGHT_MIN = 8;
const BOX_HEIGHT_MAX = 60;
const DOME_COLOR_RAMP = ["#3b82f6", "#22d3ee", "#facc15", "#f97316", "#ef4444"]; // weak -> strong RSSI
const REALISTIC_RSSI_MIN_DB = -50;
const REALISTIC_RSSI_MAX_DB = -3;

function cellToPoint(cell, distanceBucketKm) {
  const bearingRad = (cell.sector_center_deg * Math.PI) / 180;
  // Bucket center (not floor): this feeds real Cartesian geometry, not a
  // labeled category axis -- unlike rssi_by_distance's bucket-floor
  // convention, which only ever needs an axis-tick label.
  const distKm = cell.distance_bucket_km + distanceBucketKm / 2;
  return {
    x: distKm * Math.sin(bearingRad), // east
    y: distKm * Math.cos(bearingRad), // north (bearing 0 deg = north, clockwise)
    zKm: cell.altitude_bucket_ft * FT_TO_KM,
  };
}

function buildOption(data) {
  const points = data.cells.map((cell) => cellToPoint(cell, data.distance_bucket_km));
  const maxDistKm = Math.max(1, ...points.map((p) => Math.hypot(p.x, p.y)));
  const maxAltKm = Math.max(0.001, ...points.map((p) => p.zKm));
  const trueRatio = maxAltKm / maxDistKm;
  const boxHeight = Math.min(
    BOX_HEIGHT_MAX,
    Math.max(BOX_HEIGHT_MIN, trueRatio * ALTITUDE_EXAGGERATION * 100)
  );
  const maxCount = data.cells.reduce((max, cell) => Math.max(max, cell.count), 0) || 1;
  const rssiValues = data.cells.map((cell) => cell.avg_rssi);

  return {
    backgroundColor: "transparent",
    grid3D: {
      boxWidth: 100,
      boxDepth: 100,
      boxHeight,
      viewControl: { projection: "perspective", autoRotate: false },
      axisLine: { lineStyle: { color: CHART_COLORS.axisLine } },
      axisLabel: { color: CHART_COLORS.axisLabel },
      splitLine: { lineStyle: { color: CHART_COLORS.splitLine } },
    },
    xAxis3D: { type: "value", name: t("receiver.receptionDomeEastWestAxis") },
    yAxis3D: { type: "value", name: t("receiver.receptionDomeNorthSouthAxis") },
    zAxis3D: { type: "value", name: t("receiver.receptionDomeAltitudeAxis") },
    visualMap: {
      min: Math.min(REALISTIC_RSSI_MIN_DB, ...rssiValues),
      max: Math.max(REALISTIC_RSSI_MAX_DB, ...rssiValues),
      dimension: 3,
      inRange: { color: DOME_COLOR_RAMP },
      text: [t("receiver.rssiStrengthStrong"), t("receiver.rssiStrengthWeak")],
      textStyle: { color: CHART_COLORS.axisLabel },
      calculable: false,
      orient: "horizontal",
      left: "center",
      bottom: 0,
    },
    series: [
      {
        type: "scatter3D",
        symbolSize: 6,
        data: data.cells.map((cell, i) => ({
          value: [
            toDisplayDistance(points[i].x),
            toDisplayDistance(points[i].y),
            points[i].zKm,
            cell.avg_rssi,
          ],
          // "Fog density" = observation count per cell, computed by hand
          // rather than via a second visualMap channel -- echarts-gl's GL
          // series types don't consistently document opacity/colorAlpha as
          // a supported visualMap channel, while per-point itemStyle.opacity
          // is guaranteed to work regardless.
          itemStyle: { opacity: 0.15 + 0.85 * (cell.count / maxCount) },
        })),
      },
    ],
  };
}

export function createReceptionDomeChart(containerId) {
  return createChart(containerId, "reception-dome-chart-error", buildOption);
}
