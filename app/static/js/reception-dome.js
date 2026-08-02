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
//
// Also renders, on the ground plane the dome sits on: a compass ring
// (N/E/S/W + 30-degree spokes, fixed, query-independent) and a vertical
// altitude scale (tick labels, rebuilt per query since its spacing depends
// on the query's own tallest cell) -- plus an actual basemap image
// (app/domain/basemap.py's GET /api/receiver/basemap.png), fetched and
// texture-mapped onto a third ground plane. The basemap is composited
// server-side from real OSM tiles and sent as opaque pixels -- see
// basemap.py's module docstring for why this, and not sending the
// receiver's lat/lon to the browser for a client-side MapLibre layer, was
// the deliberate choice (this app has never sent receiver coordinates to
// the browser anywhere, and this feature doesn't become the exception).

import * as THREE from "./vendor/three/three.module.min.js";
import { MarchingCubes } from "./vendor/three/jsm/objects/MarchingCubes.js";
import { OrbitControls } from "./vendor/three/jsm/controls/OrbitControls.js";
import { t } from "./i18n.js";

const FT_TO_KM = 0.0003048;
const MC_RESOLUTION = 44;
// addBall's (strength, subtract) pair controls each metaball's effective
// radius and how sharply it falls off -- see MarchingCubes.addBall's own
// comment ("radius = size * sqrt(strength / subtract)", where size ==
// MC_RESOLUTION, in VOXEL units, not ball-space [0,1] units). BASE_STRENGTH
// is scaled per-cell by observation count (denser cells contribute a
// bigger, more dominant blob) up to MAX_STRENGTH so one very dense cell
// can't swallow the whole grid.
//
// SUBTRACT=10/ISOLATION=55 (this feature's original values) worked out to
// a per-ball radius of ~10-21 voxels out of 44 total -- confirmed by
// plugging BASE_STRENGTH/MAX_STRENGTH into addBall's own formula -- close
// to half the grid's width for a single dense cell's ball alone. Combined
// with overlapping balls' fields adding together, that made the isosurface
// visibly balloon out well past the actual measured points (reported by
// the user after comparing against the point cloud). SUBTRACT=40/
// ISOLATION=75 below roughly halves each ball's radius (radius scales with
// 1/sqrt(subtract)) and raises the threshold needed to stay "inside" the
// surface, pulling it in to hug the points more closely while still
// merging nearby dense clusters into one blob.
const BASE_STRENGTH = 0.5;
const MAX_STRENGTH = 2.2;
const SUBTRACT = 40;
const ISOLATION = 75;
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
// The actual control on how "tall" the dome looks relative to its
// horizontal spread: ballToWorld() scales every axis identically, so the
// true vertical/horizontal exaggeration ratio in world units is just
// Y_RANGE vs MARGIN, not any per-cell altitude constant (see cellToKm's
// comment). Halved from an original 0.55 at the user's request ("altitude
// looks over-exaggerated") after discovering the old ALTITUDE_EXAGGERATION
// constant wasn't actually doing anything.
const Y_RANGE = 0.275;
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
    // Negated at the user's explicit request after their own direct
    // comparison against real geography: the dome/point cloud (and the
    // basemap's UV assignment, kept paired with this) needed an
    // east-west flip specifically, with north-south left untouched. The
    // compass ring/spokes are unaffected (a circle and 30-degree spokes
    // are symmetric under this), only the N/E/S/W label *text* at each
    // position needed swapping to match -- see _buildCompass().
    xKm: -distKm * Math.sin(bearingRad), // east
    zKm: distKm * Math.cos(bearingRad), // north (bearing 0 deg = north, clockwise; three.js -Z is "forward/north")
    // No altitude-exaggeration multiplier here on purpose: setData() below
    // divides every yKm by maxYKm (the tallest cell's own yKm) to get a
    // [0,1]-ish ball coordinate, so any constant multiplier applied to
    // yKm here would cancel out exactly against the same multiplier in
    // maxYKm -- a former ALTITUDE_EXAGGERATION constant here was
    // discovered to be a complete no-op for that reason (changing it had
    // zero visual effect), the same category of bug as this feature's
    // earlier echarts-gl "scaling data doesn't change the box" issue.
    // Y_RANGE below is the actual, real lever on vertical exaggeration.
    yKm: cell.altitude_bucket_ft * FT_TO_KM,
  };
}

// World-space radius of the ground ring/basemap at the data's own horizontal
// edge (ballCoord = 0.5 + MARGIN -> ballToWorld gives 2*MARGIN) -- shared by
// the compass ring (fixed, built once) and the basemap plane (rescaled per
// query, since it must line up with whatever maxHorizKm the current query
// actually has).
const GROUND_WORLD_RADIUS = 2 * MARGIN;
// Slightly below y=0 (which is where the lowest possible altitude bucket
// sits, see Y_WORLD_OFFSET above) so the compass ring/basemap read as a
// "floor" the dome sits on rather than fighting the lowest data layer for
// the same z-depth.
const GROUND_Y = -0.02;
const BASEMAP_Y = GROUND_Y - 0.004;

const ALTITUDE_TICK_STEP_CANDIDATES_FT = [1000, 2000, 5000, 10000, 20000, 50000];
const MAX_ALTITUDE_TICKS = 6;

const NM_TO_KM = 1.852;
const DISTANCE_RING_STEP_NM = 50;
const DISTANCE_RING_STEP_KM = DISTANCE_RING_STEP_NM * NM_TO_KM;

function niceAltitudeStepFt(maxAltitudeFt) {
  for (const step of ALTITUDE_TICK_STEP_CANDIDATES_FT) {
    if (maxAltitudeFt / step <= MAX_ALTITUDE_TICKS) return step;
  }
  return ALTITUDE_TICK_STEP_CANDIDATES_FT[ALTITUDE_TICK_STEP_CANDIDATES_FT.length - 1];
}

// Renders `text` onto an offscreen canvas and wraps it as a THREE.Sprite,
// the standard lightweight way to put text labels into a three.js scene
// without pulling in a font/text-geometry library.
function makeTextSprite(text, { fontSizePx = 48, color = "#c9d6e3", worldHeight = 0.075 } = {}) {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const padding = fontSizePx * 0.35;
  ctx.font = `bold ${fontSizePx}px sans-serif`;
  const textWidth = ctx.measureText(text).width;
  canvas.width = Math.ceil(textWidth + padding * 2);
  canvas.height = Math.ceil(fontSizePx * 1.5);
  // Re-set font: sizing the canvas resets its 2D context state.
  ctx.font = `bold ${fontSizePx}px sans-serif`;
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(material);
  const aspect = canvas.width / canvas.height;
  sprite.scale.set(worldHeight * aspect, worldHeight, 1);
  return sprite;
}

function disposeGroupChildren(group) {
  while (group.children.length) {
    const child = group.children.pop();
    child.geometry?.dispose();
    if (child.material?.map) child.material.map.dispose();
    child.material?.dispose();
  }
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
      // Caps how far the camera can orbit downward so it can never end up
      // below the ground plane looking up at its underside. This isn't
      // just a nicer default angle: a single flat texture on a
      // double-sided plane is fundamentally unable to look correct from
      // both sides at once (the same reason handwriting reads backwards
      // through the back of a translucent page) -- no choice of UV
      // mapping fixes that, only preventing that viewing angle does.
      this.controls.maxPolarAngle = Math.PI / 2 - 0.1;
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

      // Static (query-independent): built once here, never rebuilt in
      // setData(), since GROUND_WORLD_RADIUS doesn't depend on the data.
      this.scene.add(this._buildCompass());

      // Data-dependent (altitude scale changes with each query's own
      // maxYKm) and rebuilt every setData() call, same as pointsGroup/mc.
      this.altitudeAxisGroup = new THREE.Group();
      this.scene.add(this.altitudeAxisGroup);

      // Distance rings' world radii depend on maxHorizKm (the current
      // query's own scale), so this is rebuilt in setData() too, same as
      // the altitude axis.
      this.distanceRingsGroup = new THREE.Group();
      this.scene.add(this.distanceRingsGroup);

      this.basemapGroup = new THREE.Group();
      this.scene.add(this.basemapGroup);
      this._basemapRadiusKm = null;

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

  // Compass ring (distance ring + 30-degree spokes + N/E/S/W labels) lying
  // flat on the ground plane. Built once (see _init()): its radius is
  // GROUND_WORLD_RADIUS, a fixed constant, not derived from any query's
  // data, so it never needs rebuilding.
  _buildCompass() {
    const group = new THREE.Group();

    const ringPoints = [];
    const RING_SEGMENTS = 128;
    for (let i = 0; i <= RING_SEGMENTS; i++) {
      const angle = (i / RING_SEGMENTS) * Math.PI * 2;
      ringPoints.push(
        new THREE.Vector3(
          Math.sin(angle) * GROUND_WORLD_RADIUS,
          GROUND_Y,
          Math.cos(angle) * GROUND_WORLD_RADIUS
        )
      );
    }
    const ringGeometry = new THREE.BufferGeometry().setFromPoints(ringPoints);
    const ringMaterial = new THREE.LineBasicMaterial({
      // Dark, not the earlier teal -- needs to read clearly against the
      // basemap's light OSM tile colors, at the user's request.
      color: 0x1c1c1c,
      transparent: true,
      opacity: 0.55,
    });
    group.add(new THREE.LineLoop(ringGeometry, ringMaterial));

    const spokePoints = [];
    for (let deg = 0; deg < 360; deg += 30) {
      const angle = (deg * Math.PI) / 180;
      spokePoints.push(new THREE.Vector3(0, GROUND_Y, 0));
      spokePoints.push(
        new THREE.Vector3(
          Math.sin(angle) * GROUND_WORLD_RADIUS,
          GROUND_Y,
          Math.cos(angle) * GROUND_WORLD_RADIUS
        )
      );
    }
    const spokeGeometry = new THREE.BufferGeometry().setFromPoints(spokePoints);
    const spokeMaterial = new THREE.LineBasicMaterial({
      color: 0x1c1c1c,
      transparent: true,
      opacity: 0.2,
    });
    group.add(new THREE.LineSegments(spokeGeometry, spokeMaterial));

    // Cardinal directions only (not translated -- N/E/S/W compass
    // abbreviations, universally understood the same way this app's
    // existing bearing-range polar chart already labels degrees).
    // E/W text is swapped relative to the position formula's own
    // sin(deg) sign (rather than negating the position formula itself,
    // which would be a no-op here anyway: a full ring/spokes are
    // symmetric under X negation) -- this keeps the labels aligned with
    // cellToKm()'s now-negated xKm, since a full circle can't otherwise
    // reveal which side is which.
    const labelRadius = GROUND_WORLD_RADIUS * 1.12;
    for (const { deg, text } of [
      { deg: 0, text: "N" },
      { deg: 90, text: "W" },
      { deg: 180, text: "S" },
      { deg: 270, text: "E" },
    ]) {
      const angle = (deg * Math.PI) / 180;
      const sprite = makeTextSprite(text, {
        fontSizePx: 56,
        color: "#1c1c1c",
        worldHeight: 0.09,
      });
      sprite.position.set(
        Math.sin(angle) * labelRadius,
        GROUND_Y,
        Math.cos(angle) * labelRadius
      );
      group.add(sprite);
    }
    return group;
  }

  // Vertical altitude scale (tick marks + "N,NNN ft" labels), rebuilt each
  // setData() call because its tick spacing/positions depend on the
  // current query's own maxYKm (see setData()'s by = Y_BASE + (yKm /
  // maxYKm) * Y_RANGE mapping) -- a fixed altitude value sits at a
  // different world height depending on what the tallest cell in the
  // current query actually is.
  _buildAltitudeAxis(maxYKm) {
    const group = new THREE.Group();
    const maxAltitudeFt = maxYKm / FT_TO_KM;
    const stepFt = niceAltitudeStepFt(maxAltitudeFt);

    const cornerX = -GROUND_WORLD_RADIUS * 1.15;
    const cornerZ = -GROUND_WORLD_RADIUS * 1.15;

    const altitudeToWorldY = (altitudeFt) => {
      const yKm = altitudeFt * FT_TO_KM;
      const by = Y_BASE + (yKm / maxYKm) * Y_RANGE;
      return ballToWorld(by) + Y_WORLD_OFFSET;
    };

    const topWorldY = altitudeToWorldY(Math.ceil(maxAltitudeFt / stepFt) * stepFt);
    const axisPoints = [
      new THREE.Vector3(cornerX, altitudeToWorldY(0), cornerZ),
      new THREE.Vector3(cornerX, topWorldY, cornerZ),
    ];
    const axisGeometry = new THREE.BufferGeometry().setFromPoints(axisPoints);
    const axisMaterial = new THREE.LineBasicMaterial({
      color: 0x9aa7b5,
      transparent: true,
      opacity: 0.5,
    });
    group.add(new THREE.Line(axisGeometry, axisMaterial));

    const TICK_HALF_LENGTH = 0.02;
    for (let altitudeFt = 0; altitudeFt <= maxAltitudeFt + stepFt / 2; altitudeFt += stepFt) {
      const worldY = altitudeToWorldY(altitudeFt);
      const tickPoints = [
        new THREE.Vector3(cornerX - TICK_HALF_LENGTH, worldY, cornerZ),
        new THREE.Vector3(cornerX + TICK_HALF_LENGTH, worldY, cornerZ),
      ];
      const tickGeometry = new THREE.BufferGeometry().setFromPoints(tickPoints);
      group.add(new THREE.Line(tickGeometry, axisMaterial));

      const label = makeTextSprite(`${Math.round(altitudeFt).toLocaleString()} ft`, {
        fontSizePx: 40,
        color: "#9aa7b5",
        worldHeight: 0.055,
      });
      label.position.set(cornerX - TICK_HALF_LENGTH * 5, worldY, cornerZ);
      group.add(label);
    }
    return group;
  }

  // Concentric distance rings every 50nm on the ground plane, out to the
  // current query's own maxHorizKm -- rebuilt per query (like the altitude
  // axis) since the world-per-km scale depends on maxHorizKm. Uses the
  // same GROUND_WORLD_RADIUS/maxHorizKm conversion as the compass ring and
  // the data points themselves, not the basemap image's own (separately
  // bucketed) radius, so a ring genuinely marks 50/100/150... real
  // nautical miles from the receiver regardless of which basemap image
  // bucket happened to be fetched.
  _buildDistanceRings(maxHorizKm) {
    const group = new THREE.Group();
    const worldPerKm = GROUND_WORLD_RADIUS / maxHorizKm;
    const ringMaterial = new THREE.LineBasicMaterial({
      color: 0x1c1c1c,
      transparent: true,
      opacity: 0.4,
    });
    const RING_SEGMENTS = 96;
    const labelAngleRad = Math.PI / 4; // northeast, clear of the N/E labels

    for (
      let distKm = DISTANCE_RING_STEP_KM;
      distKm <= maxHorizKm + DISTANCE_RING_STEP_KM / 2;
      distKm += DISTANCE_RING_STEP_KM
    ) {
      const worldRadius = distKm * worldPerKm;
      const points = [];
      for (let i = 0; i <= RING_SEGMENTS; i++) {
        const angle = (i / RING_SEGMENTS) * Math.PI * 2;
        points.push(
          new THREE.Vector3(Math.sin(angle) * worldRadius, GROUND_Y + 0.001, Math.cos(angle) * worldRadius)
        );
      }
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      group.add(new THREE.LineLoop(geometry, ringMaterial));

      const nm = Math.round(distKm / NM_TO_KM);
      const label = makeTextSprite(`${nm}nm`, {
        fontSizePx: 34,
        color: "#1c1c1c",
        worldHeight: 0.045,
      });
      label.position.set(
        Math.sin(labelAngleRad) * worldRadius,
        GROUND_Y + 0.001,
        Math.cos(labelAngleRad) * worldRadius
      );
      group.add(label);
    }
    return group;
  }

  // Fetches (once per rounded-radius bucket -- the server buckets too, see
  // app/domain/basemap.py) a real basemap image centered on the receiver
  // and texture-maps it onto a flat ground plane sized to the *current*
  // query's own km-to-world-unit scale, so the map's real-world scale
  // lines up with the data points regardless of which bucket the server
  // actually rendered. Coordinates never appear anywhere in this
  // request -- only a radius (a distance) goes out, only pixels come
  // back; see basemap.py's module docstring for why.
  async _ensureBasemap(maxHorizKm) {
    const requestRadiusKm = Math.max(1, Math.ceil(maxHorizKm));
    if (this._basemapRadiusKm === requestRadiusKm) return;
    this._basemapRadiusKm = requestRadiusKm;

    try {
      const response = await fetch(`/api/receiver/basemap.png?radius_km=${requestRadiusKm}`);
      if (!response.ok) return;
      const actualRadiusKm = parseFloat(
        response.headers.get("X-Basemap-Radius-Km") || String(requestRadiusKm)
      );
      const blob = await response.blob();
      // Deliberately NOT createImageBitmap() here: verified empirically
      // (a synthetic quadrant-colored test texture, checked corner-by-
      // corner via gl.readPixels rather than by eye) that
      // createImageBitmap()+THREE.Texture renders this image mirrored
      // left-right on this vendored Three.js build, while loading through
      // a plain <img> element does not. This is what caused the very
      // real "N and S look swapped compared to the map" bug -- an actual
      // east-west mirror reads as a north-south swap once combined with
      // the compass ring's own bearing convention.
      const objectUrl = URL.createObjectURL(blob);
      const image = new Image();
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = reject;
        image.src = objectUrl;
      });

      // Stale by the time the fetch resolves (a newer query already
      // requested a different radius) -- drop this response rather than
      // showing a mismatched-scale basemap.
      if (this._basemapRadiusKm !== requestRadiusKm) {
        URL.revokeObjectURL(objectUrl);
        return;
      }

      disposeGroupChildren(this.basemapGroup);
      const texture = new THREE.Texture(image);
      texture.needsUpdate = true;
      texture.colorSpace = THREE.SRGBColorSpace;
      URL.revokeObjectURL(objectUrl);

      const worldRadius = actualRadiusKm * (GROUND_WORLD_RADIUS / maxHorizKm);
      const material = new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        opacity: 0.85,
        side: THREE.DoubleSide,
      });
      // Custom geometry (four explicit corner vertices/UVs) instead of
      // PlaneGeometry+rotation.x: an OrbitControls polar-angle cap (see
      // _init()) keeps the camera from ever seeing this plane's opposite,
      // inherently-mirrored face, so the one remaining question is purely
      // which world corner should get which source-image corner -- and
      // per the user's own direct verification against real geography,
      // this needs an east-west flip to match cellToKm()'s now-negated
      // xKm, so that the map and the data/compass agree on which side is
      // east. V (north-south) is untouched.
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(
          new Float32Array([
            -worldRadius, 0, worldRadius, // NW
            worldRadius, 0, worldRadius, // NE
            -worldRadius, 0, -worldRadius, // SW
            worldRadius, 0, -worldRadius, // SE
          ]),
          3
        )
      );
      geometry.setAttribute(
        "uv",
        new THREE.BufferAttribute(
          new Float32Array([
            1, 1, // NW
            0, 1, // NE
            1, 0, // SW
            0, 0, // SE
          ]),
          2
        )
      );
      geometry.setIndex([0, 2, 1, 2, 3, 1]);
      const plane = new THREE.Mesh(geometry, material);
      plane.position.set(0, BASEMAP_Y, 0);
      this.basemapGroup.add(plane);
      this._render();
    } catch (err) {
      console.error("reception-dome basemap load failed", err);
    }
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
        disposeGroupChildren(this.altitudeAxisGroup);
        disposeGroupChildren(this.distanceRingsGroup);
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

      disposeGroupChildren(this.altitudeAxisGroup);
      this.altitudeAxisGroup.add(this._buildAltitudeAxis(maxYKm));
      disposeGroupChildren(this.distanceRingsGroup);
      this.distanceRingsGroup.add(this._buildDistanceRings(maxHorizKm));
      // Fire-and-forget: the fetch resolves later and rebuilds
      // basemapGroup + re-renders on its own; setData() doesn't block on
      // it, and it no-ops if the radius bucket hasn't actually changed.
      this._ensureBasemap(maxHorizKm);

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
