// reception-dome.js -- a 3rd attempt at visualizing reception range in 3D
// on receiver.html, after two prior attempts (echarts-gl scatter3D
// "hemisphere", then a CesiumJS mesh) were both built and removed for being
// hard to read (see README's Receiver performance section / PLAN.md). This
// attempt renders a genuine 3D kernel-density-style isosurface (marching
// cubes over "metaballs" placed at each observed bearing x distance x
// altitude cell, sized by observation count and colored by average RSSI),
// with the original discrete cells overlaid as solid points -- matching
// the "dome-shaped volumetric probability distribution" look the user
// asked for, after two earlier iterations within this same 3rd attempt
// (an echarts-gl point cloud, then a polar-grid + additive-blend version)
// were judged not quite right either.
//
// echarts-gl (used by the first two iterations of this same 3rd attempt)
// has no isosurface/volume-rendering capability at all, so this iteration
// switches the whole chart to Three.js's MarchingCubes -- a well-precedented
// "metaballs" utility, not a from-scratch ray-marching shader. It's kept
// deliberately self-contained (this file, one query -- unchanged from the
// prior iterations -- one vendored library) so a third removal, if
// warranted, is still a single clean diff.
//
// Loaded as a plain ES module (no import map): app/static/js/vendor/three/
// jsm/{objects/MarchingCubes,controls/OrbitControls}.js have their bare
// 'three' import rewritten to a relative path (see the vendoring note at
// the top of each file) specifically so this chart needs zero CSP
// loosening -- unlike echarts-gl (which needed 'unsafe-eval') or globe.html's
// CesiumJS (which needs 'unsafe-eval' and blob:).

import * as THREE from "./vendor/three/three.module.min.js";
import { MarchingCubes } from "./vendor/three/jsm/objects/MarchingCubes.js";
import { OrbitControls } from "./vendor/three/jsm/controls/OrbitControls.js";
import { t } from "./i18n.js";

const FT_TO_KM = 0.0003048;
const ALTITUDE_EXAGGERATION = 6;
const MC_RESOLUTION = 44;
// addBall's (strength, subtract) pair controls each metaball's effective
// radius and how sharply it falls off -- see MarchingCubes.addBall's own
// comment ("radius = sqrt(strength / subtract)"). BASE_STRENGTH is scaled
// per-cell by observation count (denser cells contribute a bigger, more
// dominant blob) up to MAX_STRENGTH so one very dense cell can't swallow
// the whole grid.
const BASE_STRENGTH = 0.5;
const MAX_STRENGTH = 2.2;
const SUBTRACT = 10;
const ISOLATION = 55;
// Only the densest cells become metaballs (keeps marching-cubes' per-ball
// voxel-touching cost bounded regardless of how many sparse cells the API
// returns); every cell still contributes its own overlaid point regardless.
const MAX_BALLS = 600;

// MarchingCubes.addBall takes coordinates in [0,1] ball-space, but the mesh
// it produces spans mesh-local [-1,1] (this.delta = 2/resolution over
// `resolution` steps) -- confirmed empirically by comparing addBall's input
// range against the actual rendered geometry's extent, since this is
// exactly the kind of "library behaves differently than assumed" gap that's
// bitten every iteration of this feature so far. ballToWorld() is the single
// place that mapping happens, so points (placed independently of the
// isosurface) and the isosurface itself can never drift apart the way they
// did in an earlier draft of this file (points floating visibly outside the
// blob because the two used different formulas).
function ballToWorld(ballCoord) {
  return 2 * (ballCoord - 0.5);
}

// Keeps ball coordinates within [0.5-MARGIN, 0.5+MARGIN] on the horizontal
// (X/Z) axes -- MarchingCubes doesn't polygonize its outermost voxel layer
// (normals aren't well-defined there), so points too close to the [0,1]
// edges would sit outside any possible surface.
const MARGIN = 0.42;
const Y_BASE = 0.1;
const Y_RANGE = 0.55;
// Shifts the lowest possible altitude ball (Y_BASE) to world y = 0, so the
// dome sits on the "ground" rather than straddling it -- ballToWorld() maps
// [0,1] symmetrically to [-1,1], so without this offset half the dome would
// render underground.
const Y_WORLD_OFFSET = -ballToWorld(Y_BASE);

function rssiColor(avgRssi, minRssi, maxRssi) {
  const t01 = Math.min(1, Math.max(0, (avgRssi - minRssi) / (maxRssi - minRssi || 1)));
  // Blue (weak) -> red (strong), same convention as the prior iteration's
  // visualMap ramp, via HSL hue interpolation (0.6 = blue, 0 = red).
  return new THREE.Color().setHSL(0.6 * (1 - t01), 0.85, 0.5);
}

function cellToKm(cell, distanceBucketKm) {
  const bearingRad = (cell.sector_center_deg * Math.PI) / 180;
  const distKm = cell.distance_bucket_km + distanceBucketKm / 2;
  return {
    xKm: distKm * Math.sin(bearingRad), // east
    zKm: distKm * Math.cos(bearingRad), // north (bearing 0 deg = north, clockwise; three.js -Z is "forward/north")
    yKm: cell.altitude_bucket_ft * FT_TO_KM * ALTITUDE_EXAGGERATION,
  };
}

class ReceptionDomeChart {
  constructor(containerId, errorElId) {
    this.container = document.getElementById(containerId);
    this.errorElId = errorElId;
    this.scene = null;
    this.renderer = null;
    this.camera = null;
    this.controls = null;
    this.mc = null;
    this.pointsGroup = null;
    this.ready = false;
    this._init();
  }

  _showError(message) {
    const el = document.getElementById(this.errorElId);
    if (el) {
      el.textContent = message;
      el.hidden = false;
    }
  }

  _hideError() {
    const el = document.getElementById(this.errorElId);
    if (el) el.hidden = true;
  }

  _init() {
    if (!this.container) return;
    try {
      const width = this.container.clientWidth || 600;
      const height = this.container.clientHeight || 460;

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.05, 50);
      this.camera.position.set(1.9, 1.4, 1.9);

      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer.setSize(width, height);
      this.container.replaceChildren(this.renderer.domElement);

      this.controls = new OrbitControls(this.camera, this.renderer.domElement);
      this.controls.target.set(0, Y_WORLD_OFFSET * 0.4, 0);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.08;
      this.controls.addEventListener("change", () => this._render());

      this.scene.add(new THREE.AmbientLight(0xffffff, 1.1));
      const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
      dirLight.position.set(1, 2, 1);
      this.scene.add(dirLight);

      const material = new THREE.MeshPhongMaterial({
        vertexColors: true,
        transparent: true,
        opacity: 0.38,
        // Overlapping translucent triangles (inevitable with a blob-shaped
        // isosurface) need depthWrite off, or the z-buffer makes whichever
        // triangle renders first opaquely occlude the ones behind it --
        // confirmed empirically: without this the whole surface looked like
        // a solid, not a translucent, ball.
        depthWrite: false,
        side: THREE.DoubleSide,
        shininess: 12,
      });
      this.mc = new MarchingCubes(MC_RESOLUTION, material, true, true, 65000);
      this.mc.position.set(0, Y_WORLD_OFFSET, 0);
      this.mc.isolation = ISOLATION;
      this.scene.add(this.mc);

      this.pointsGroup = new THREE.Group();
      this.scene.add(this.pointsGroup);

      let resizeQueued = false;
      this._resizeObserver = new ResizeObserver(() => {
        if (resizeQueued) return;
        resizeQueued = true;
        requestAnimationFrame(() => {
          resizeQueued = false;
          this.resize();
        });
      });
      this._resizeObserver.observe(this.container);

      this.ready = true;
      this._render();
    } catch (err) {
      console.error("reception-dome init failed", err);
      this._showError(t("chart.initFailed"));
    }
  }

  _render() {
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  resize() {
    if (!this.ready) return;
    const width = this.container.clientWidth || 600;
    const height = this.container.clientHeight || 460;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
    this._render();
  }

  setData(data) {
    if (!this.ready) return;
    try {
      this._hideError();
      while (this.pointsGroup.children.length) {
        const child = this.pointsGroup.children.pop();
        child.geometry?.dispose();
        child.material?.dispose();
      }

      if (!data.cells.length) {
        this.mc.reset();
        this._render();
        return;
      }

      const withKm = data.cells.map((cell) => ({
        cell,
        ...cellToKm(cell, data.distance_bucket_km),
      }));
      const maxHorizKm = Math.max(1, ...withKm.map((p) => Math.hypot(p.xKm, p.zKm)));
      const maxYKm = Math.max(0.001, ...withKm.map((p) => p.yKm));
      const maxCount = data.cells.reduce((max, c) => Math.max(max, c.count), 0) || 1;
      const rssiValues = data.cells.map((c) => c.avg_rssi);
      // Deliberately the *actual* range of this query's data, not a fixed
      // realistic hardware range (-50 to -3 dBFS) -- checked against real
      // production data first: the densest cells (which dominate the
      // isosurface's shape) cluster tightly around a "typical" mid-strength
      // RSSI, so a fixed wide range compressed nearly everything into one
      // narrow hue band. Per-query min/max spends the full color gradient
      // on whatever spread this time window actually has, at the cost of
      // not being directly color-comparable across different time ranges.
      const minRssi = Math.min(...rssiValues);
      const maxRssi = Math.max(...rssiValues);

      // Ball-space [0,1] coordinates, computed once per cell and shared by
      // both the isosurface (below, top-N densest cells only) and the
      // overlaid points (all cells) via the same ballToWorld() -- see that
      // function's comment for why this must be the single source of truth.
      const withBallCoords = withKm.map((p) => ({
        ...p,
        bx: 0.5 + (p.xKm / maxHorizKm) * MARGIN,
        by: Y_BASE + (p.yKm / maxYKm) * Y_RANGE,
        bz: 0.5 + (p.zKm / maxHorizKm) * MARGIN,
      }));

      // Only the top-N densest cells feed the isosurface (see MAX_BALLS);
      // every cell still gets its own overlaid point below regardless.
      const ranked = [...withBallCoords].sort((a, b) => b.cell.count - a.cell.count);
      const ballCells = ranked.slice(0, MAX_BALLS);

      this.mc.reset();
      for (const p of ballCells) {
        const strength = Math.min(
          MAX_STRENGTH,
          BASE_STRENGTH + (BASE_STRENGTH * 1.5 * p.cell.count) / maxCount
        );
        const color = rssiColor(p.cell.avg_rssi, minRssi, maxRssi);
        this.mc.addBall(p.bx, p.by, p.bz, strength, SUBTRACT, color);
      }
      this.mc.update();

      const sphereGeo = new THREE.SphereGeometry(0.014, 8, 8);
      for (const p of withBallCoords) {
        const color = rssiColor(p.cell.avg_rssi, minRssi, maxRssi);
        const mat = new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.3 + 0.6 * (p.cell.count / maxCount),
        });
        const mesh = new THREE.Mesh(sphereGeo, mat);
        mesh.position.set(
          ballToWorld(p.bx),
          ballToWorld(p.by) + Y_WORLD_OFFSET,
          ballToWorld(p.bz)
        );
        this.pointsGroup.add(mesh);
      }

      this._render();
    } catch (err) {
      console.error("reception-dome render failed", err);
      this._showError(t("chart.renderFailed"));
    }
  }
}

export function createReceptionDomeChart(containerId) {
  const chart = new ReceptionDomeChart(containerId, "reception-dome-chart-error");
  if (!chart.ready) {
    return { setData: () => {}, resize: () => {} };
  }
  return { setData: (data) => chart.setData(data), resize: () => chart.resize() };
}
