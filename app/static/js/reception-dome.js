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
// convention as echarts itself) for the grid3D/scatter3D/line3D chart types.

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

// Polar reference grid (rings + compass spokes) drawn as line3D series
// instead of the default Cartesian box: echarts-gl has no native polar/
// cylindrical 3D coordinate system (confirmed by inspecting the vendored
// bundle -- only cartesian3D, geo3D and globe exist), so "polar" here means
// keeping the underlying bearing/distance -> X/Y math exactly as before
// (that part was already polar) and replacing the *visual* grid chrome
// with hand-drawn rings/spokes on the X/Y plane, rather than a rectangular
// box. grid3D's own axisLine/axisLabel/splitLine are hidden accordingly;
// only the Z (altitude) axis keeps its own ruler, overridden back on.
const RING_FRACTIONS = [0.25, 0.5, 0.75, 1];
const SPOKE_BEARINGS_DEG = [0, 45, 90, 135, 180, 225, 270, 315];
const RING_SEGMENTS = 64;
const GRID_LINE_STYLE = { width: 1, opacity: 0.5 };

function ringPoints(radius, segments) {
  const points = [];
  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * Math.PI * 2;
    points.push([radius * Math.sin(angle), radius * Math.cos(angle), 0]);
  }
  return points;
}

function spokeLine(bearingDeg, radius) {
  const angle = (bearingDeg * Math.PI) / 180;
  return [
    [0, 0, 0],
    [radius * Math.sin(angle), radius * Math.cos(angle), 0],
  ];
}

function polarGridSeries(maxDistDisplay) {
  const gridColor = CHART_COLORS.splitLine;
  const rings = RING_FRACTIONS.map((fraction) => ({
    type: "line3D",
    coordinateSystem: "cartesian3D",
    data: ringPoints(maxDistDisplay * fraction, RING_SEGMENTS),
    lineStyle: { ...GRID_LINE_STYLE, color: gridColor },
    silent: true,
  }));
  const spokes = SPOKE_BEARINGS_DEG.map((bearingDeg) => ({
    type: "line3D",
    coordinateSystem: "cartesian3D",
    data: spokeLine(bearingDeg, maxDistDisplay),
    lineStyle: { ...GRID_LINE_STYLE, color: gridColor },
    silent: true,
  }));
  return [...rings, ...spokes];
}

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
  const maxDistDisplay = toDisplayDistance(maxDistKm);

  return {
    backgroundColor: "transparent",
    grid3D: {
      boxWidth: 100,
      boxDepth: 100,
      boxHeight,
      viewControl: { projection: "perspective", autoRotate: false, alpha: 25 },
      // The Cartesian box chrome is replaced by the hand-drawn polar grid
      // above -- axisLine can't be hidden via `show: false` (that throws
      // inside echarts-gl for this specific property, confirmed by testing
      // each grid3D sub-option in isolation), so it's hidden via a fully
      // transparent line style instead, which works with no such issue.
      axisLine: { lineStyle: { opacity: 0 } },
      axisLabel: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisPointer: { show: false },
    },
    xAxis3D: { type: "value", min: -maxDistDisplay, max: maxDistDisplay },
    yAxis3D: { type: "value", min: -maxDistDisplay, max: maxDistDisplay },
    // Altitude keeps its own ruler (overriding grid3D's hidden defaults back
    // on for this one axis) since the polar rings only cover the horizontal
    // plane -- there's no other cue for what the exaggerated vertical scale
    // actually means otherwise.
    zAxis3D: {
      type: "value",
      name: t("receiver.receptionDomeAltitudeAxis"),
      axisLine: { show: true, lineStyle: { color: CHART_COLORS.axisLine } },
      axisLabel: { show: true, color: CHART_COLORS.axisLabel },
    },
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
      ...polarGridSeries(maxDistDisplay),
      {
        type: "scatter3D",
        symbolSize: 18,
        // Additive ("lighter") blending: overlapping translucent points
        // brighten instead of just alpha-compositing, so dense clusters
        // glow like an accumulated volumetric haze rather than reading as
        // a pile of discrete solid dots -- confirmed empirically, since
        // echarts-gl's scatter3D silently fails to render custom image
        // symbols (a soft-edged radial-gradient sprite renders zero pixels,
        // no console error either), so blendMode is the actual lever here,
        // not a custom "fog" sprite.
        blendMode: "lighter",
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
          itemStyle: { opacity: 0.12 + 0.55 * (cell.count / maxCount) },
        })),
      },
    ],
  };
}

export function createReceptionDomeChart(containerId) {
  return createChart(containerId, "reception-dome-chart-error", buildOption);
}
