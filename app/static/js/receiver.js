// receiver.js -- entrypoint for receiver.html: max range by bearing (polar
// bar chart), max range by altitude band (horizontal bar chart), and
// message-count/position-rate over time (line chart). All three use
// chart.js's createChart factory (Milestone H), so error handling/resize
// behave the same as the dashboard's traffic chart.

import { api } from "./api.js";
import { axisStyle, baseChartOption, CHART_COLORS, createChart, formatAxisTime, setTimezone } from "./chart.js";
import { distanceUnitLabel, formatDistance, toDisplayDistance } from "./units.js";

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

// createHemisphereDome() isn't built through chart.js's createChart
// (that factory is echarts-specific), so it needs its own copy of the
// same show/hide-error-div convention every other chart on this page
// already gets for free from createChart.
function showChartError(errorElId, message) {
  const el = document.getElementById(errorElId);
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
}

function hideChartError(errorElId) {
  const el = document.getElementById(errorElId);
  if (el) el.hidden = true;
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
      grid: { left: 60, right: 16, top: 30, bottom: 40 },
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
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 0,
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

// --- 3D reception dome (CesiumJS) -------------------------------------------
//
// Replaces the old echarts-gl scatter3D point cloud with a connected,
// shaded mesh ("cloud/heatmap" look instead of discrete dots), real
// compass orientation (N/E/S/W labels + distance rings, since echarts-gl
// has no polar3D coordinate system to build true polar axes from), and a
// hover tooltip -- addressing all three readability complaints together.
//
// The receiver's real coordinates are never returned by this API (by
// design -- see CLAUDE.md/README Security & Privacy). The dome is built
// in a purely LOCAL East-North-Up frame anchored at an arbitrary,
// clearly-fake placeholder point (Null Island, 0N/0E) -- never the real
// site. This costs nothing in correctness: a Cesium ENU frame is
// correctly true-north-oriented at any point on the WGS84 ellipsoid, so
// bearing/elevation/distance geometry (all receiver-relative to begin
// with) works out identically regardless of which point it's anchored
// at.
const DOME_ANCHOR_LON = 0;
const DOME_ANCHOR_LAT = 0;
const DOME_BEARING_SECTOR_COUNT = 16;
const DOME_ELEVATION_BAND_COUNT = 9;
const KM_TO_M = 1000;

function domeCellLocalPosition(entry) {
  const bearingRad = Cesium.Math.toRadians(entry.sector_center_deg);
  const elevationRad = Cesium.Math.toRadians(entry.elevation_center_deg);
  const distanceM = entry.max_distance_km * KM_TO_M;
  const horizontal = distanceM * Math.cos(elevationRad);
  const east = horizontal * Math.sin(bearingRad);
  const north = horizontal * Math.cos(bearingRad);
  const up = distanceM * Math.sin(elevationRad);
  return new Cesium.Cartesian3(east, north, up);
}

function localToWorld(enuTransform, local) {
  return Cesium.Matrix4.multiplyByPoint(enuTransform, local, new Cesium.Cartesian3());
}

function colorForDomeDistance(distanceKm, maxDistanceKm) {
  if (!maxDistanceKm) return Cesium.Color.fromCssColorString(RSSI_HEATMAP_COLOR_RAMP[0]);
  const t = Math.max(0, Math.min(1, distanceKm / maxDistanceKm));
  const scaled = t * (RSSI_HEATMAP_COLOR_RAMP.length - 1);
  const i = Math.min(RSSI_HEATMAP_COLOR_RAMP.length - 2, Math.floor(scaled));
  const localT = scaled - i;
  const c0 = Cesium.Color.fromCssColorString(RSSI_HEATMAP_COLOR_RAMP[i]);
  const c1 = Cesium.Color.fromCssColorString(RSSI_HEATMAP_COLOR_RAMP[i + 1]);
  return Cesium.Color.lerp(c0, c1, localT, new Cesium.Color());
}

function makeDomeTriangle(p0, p1, p2, color, pickInfo) {
  const positions = new Float64Array([p0.x, p0.y, p0.z, p1.x, p1.y, p1.z, p2.x, p2.y, p2.z]);
  const geometry = new Cesium.Geometry({
    attributes: {
      position: new Cesium.GeometryAttribute({
        componentDatatype: Cesium.ComponentDatatype.DOUBLE,
        componentsPerAttribute: 3,
        values: positions,
      }),
    },
    indices: new Uint16Array([0, 1, 2]),
    primitiveType: Cesium.PrimitiveType.TRIANGLES,
    boundingSphere: Cesium.BoundingSphere.fromVertices(Array.from(positions)),
  });
  return new Cesium.GeometryInstance({
    geometry,
    attributes: { color: Cesium.ColorGeometryInstanceAttribute.fromColor(color) },
    id: pickInfo,
  });
}

// Builds a sector_index x elevation_index lookup from the flat (now
// always-zero-filled, see app/db/queries/receiver.py) entries list.
function buildDomeGrid(entries) {
  const grid = [];
  for (let s = 0; s < DOME_BEARING_SECTOR_COUNT; s++) grid.push(new Array(DOME_ELEVATION_BAND_COUNT).fill(null));
  for (const entry of entries) grid[entry.sector_index][entry.elevation_index] = entry;
  return grid;
}

// One quad (2 triangles) per adjacent (sector, elevation) cell pair,
// wrapping around at sector 15->0 since bearing is circular. Skipped
// entirely if any of its 4 corner cells has no data yet -- avoids
// connecting real cells to the empty middle of a mostly-unpopulated dome.
function buildDomeGeometryInstances(grid, enuTransform, maxDistanceKm) {
  const instances = [];
  for (let s = 0; s < DOME_BEARING_SECTOR_COUNT; s++) {
    const sNext = (s + 1) % DOME_BEARING_SECTOR_COUNT;
    for (let e = 0; e < DOME_ELEVATION_BAND_COUNT - 1; e++) {
      const a = grid[s][e];
      const b = grid[s][e + 1];
      const c = grid[sNext][e];
      const d = grid[sNext][e + 1];
      if (!a?.max_distance_km || !b?.max_distance_km || !c?.max_distance_km || !d?.max_distance_km) continue;

      const posA = localToWorld(enuTransform, domeCellLocalPosition(a));
      const posB = localToWorld(enuTransform, domeCellLocalPosition(b));
      const posC = localToWorld(enuTransform, domeCellLocalPosition(c));
      const posD = localToWorld(enuTransform, domeCellLocalPosition(d));
      const avgDistance = (a.max_distance_km + b.max_distance_km + c.max_distance_km + d.max_distance_km) / 4;
      const color = colorForDomeDistance(avgDistance, maxDistanceKm);
      const pickInfo = {
        isDomeCell: true,
        sectorCenterDeg: (a.sector_center_deg + c.sector_center_deg) / 2,
        elevationCenterDeg: (a.elevation_center_deg + b.elevation_center_deg) / 2,
        maxDistanceKm: avgDistance,
      };
      instances.push(makeDomeTriangle(posA, posC, posB, color, pickInfo));
      instances.push(makeDomeTriangle(posB, posC, posD, color, pickInfo));
    }
  }
  return instances;
}

function addCompassLabels(viewer, enuTransform, radiusM) {
  const points = [
    { text: "N", bearingDeg: 0 },
    { text: "E", bearingDeg: 90 },
    { text: "S", bearingDeg: 180 },
    { text: "W", bearingDeg: 270 },
  ];
  return points.map(({ text, bearingDeg }) => {
    const bearingRad = Cesium.Math.toRadians(bearingDeg);
    const local = new Cesium.Cartesian3(radiusM * Math.sin(bearingRad), radiusM * Math.cos(bearingRad), 0);
    return viewer.entities.add({
      position: localToWorld(enuTransform, local),
      label: {
        text,
        font: "bold 16px sans-serif",
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      },
    });
  });
}

// Concentric horizon-plane rings at fractions of the max observed
// distance -- the practical stand-in for polar-style "distance from
// center" reference lines, since echarts-gl (and Cesium) have no
// off-the-shelf polar3D coordinate system to draw these from directly.
function addDistanceRings(viewer, enuTransform, maxDistanceKm) {
  const entities = [];
  for (const fraction of [0.25, 0.5, 0.75, 1.0]) {
    const radiusM = maxDistanceKm * KM_TO_M * fraction;
    const positions = [];
    for (let i = 0; i <= 64; i++) {
      const angle = (i / 64) * 2 * Math.PI;
      const local = new Cesium.Cartesian3(radiusM * Math.sin(angle), radiusM * Math.cos(angle), 0);
      positions.push(localToWorld(enuTransform, local));
    }
    entities.push(
      viewer.entities.add({
        polyline: { positions, width: 1, material: Cesium.Color.WHITE.withAlpha(0.3) },
      })
    );
    entities.push(
      viewer.entities.add({
        position: localToWorld(enuTransform, new Cesium.Cartesian3(0, radiusM, 0)),
        label: {
          text: formatDistance(maxDistanceKm * fraction),
          font: "11px sans-serif",
          fillColor: Cesium.Color.WHITE.withAlpha(0.7),
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new Cesium.Cartesian2(0, -8),
        },
      })
    );
  }
  return entities;
}

function positionHemisphereTooltip(screenPosition, viewer) {
  const tooltip = document.getElementById("hemisphere-tooltip");
  if (!tooltip) return null;
  const canvasRect = viewer.scene.canvas.getBoundingClientRect();
  const parent = tooltip.offsetParent;
  const parentRect = parent ? parent.getBoundingClientRect() : canvasRect;
  tooltip.style.left = `${canvasRect.left - parentRect.left + screenPosition.x + 12}px`;
  tooltip.style.top = `${canvasRect.top - parentRect.top + screenPosition.y + 12}px`;
  return tooltip;
}

function hideHemisphereTooltip() {
  const tooltip = document.getElementById("hemisphere-tooltip");
  if (tooltip) tooltip.hidden = true;
}

function createHemisphereDome(containerId) {
  let viewer = null;
  let enuTransform = null;
  let domePrimitive = null;
  let overlayEntities = [];
  let hasFramedOnce = false;

  try {
    const imageryProvider = new Cesium.UrlTemplateImageryProvider({
      url: "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      credit: new Cesium.Credit(
        "Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        true
      ),
      maximumLevel: 19,
    });
    viewer = new Cesium.Viewer(containerId, {
      baseLayer: new Cesium.ImageryLayer(imageryProvider),
      baseLayerPicker: false,
      geocoder: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      timeline: false,
      animation: false,
      infoBox: false,
      selectionIndicator: false,
      fullscreenButton: false,
    });
    enuTransform = Cesium.Transforms.eastNorthUpToFixedFrame(
      Cesium.Cartesian3.fromDegrees(DOME_ANCHOR_LON, DOME_ANCHOR_LAT)
    );

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((movement) => {
      const picked = viewer.scene.pick(movement.endPosition);
      if (Cesium.defined(picked) && picked.id && picked.id.isDomeCell) {
        const tooltip = positionHemisphereTooltip(movement.endPosition, viewer);
        if (tooltip) {
          const info = picked.id;
          tooltip.textContent =
            `方位 ${Math.round(info.sectorCenterDeg)}° / 仰角 ${Math.round(info.elevationCenterDeg)}° / ` +
            `距離 ${formatDistance(info.maxDistanceKm)}`;
          tooltip.hidden = false;
        }
      } else {
        hideHemisphereTooltip();
      }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
    viewer.scene.canvas.addEventListener("mouseleave", hideHemisphereTooltip);
  } catch (err) {
    console.error("hemisphere dome init failed", err);
    showChartError("hemisphere-chart-error", "3D表示の初期化に失敗しました。");
  }

  function clearDome() {
    if (domePrimitive) {
      viewer.scene.primitives.remove(domePrimitive);
      domePrimitive = null;
    }
    for (const entity of overlayEntities) viewer.entities.remove(entity);
    overlayEntities = [];
  }

  function updateCaption(maxDistanceKm) {
    const caption = document.getElementById("hemisphere-caption");
    if (!caption) return;
    caption.textContent =
      "ドラッグで視点を回転できます。中心付近が受信局(実際の位置とは無関係な仮の座標に固定表示)、" +
      "面の位置が方位(N/E/S/W、白い円は目安の距離)・仰角・受信距離、色が受信距離を表します" +
      `(青=近い 〜 赤=遠い、0〜${formatDistance(maxDistanceKm)})。ホバーで詳細を表示します。`;
  }

  function setData(data) {
    if (!viewer) return;
    hideChartError("hemisphere-chart-error");
    clearDome();

    const grid = buildDomeGrid(data.entries);
    const maxDistanceKm = data.entries.reduce((max, e) => Math.max(max, e.max_distance_km || 0), 0);
    updateCaption(maxDistanceKm);
    if (maxDistanceKm <= 0) return;

    const instances = buildDomeGeometryInstances(grid, enuTransform, maxDistanceKm);
    if (instances.length > 0) {
      domePrimitive = viewer.scene.primitives.add(
        new Cesium.Primitive({
          geometryInstances: instances,
          appearance: new Cesium.PerInstanceColorAppearance({ translucent: true, closed: false }),
        })
      );
    }
    overlayEntities = [
      ...addCompassLabels(viewer, enuTransform, maxDistanceKm * KM_TO_M * 1.15),
      ...addDistanceRings(viewer, enuTransform, maxDistanceKm),
    ];

    if (!hasFramedOnce) {
      hasFramedOnce = true;
      const anchorWorld = Cesium.Cartesian3.fromDegrees(DOME_ANCHOR_LON, DOME_ANCHOR_LAT);
      viewer.camera.lookAt(
        anchorWorld,
        new Cesium.HeadingPitchRange(
          Cesium.Math.toRadians(45),
          Cesium.Math.toRadians(-30),
          Math.max(maxDistanceKm, 10) * KM_TO_M * 2.2
        )
      );
      viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
    }
  }

  return { setData, resize: () => {} };
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
  try {
    const hemisphere = await api.getBearingElevationRange(hours);
    charts.hemisphere.setData(hemisphere);
  } catch (err) {
    console.error("bearing-elevation-range refresh failed", err);
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
    rssi: createRssiHeatmapChart("rssi-chart"),
    hemisphere: createHemisphereDome("hemisphere-container"),
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
    charts.hemisphere.resize();
  });
}

main().catch((err) => {
  console.error("receiver page failed to start", err);
});
