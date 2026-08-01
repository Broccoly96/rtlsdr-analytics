// aircraftinfo.js -- tar1090-style aircraft detail sidebar. Clicking any
// aircraft's callsign/icao anywhere in the app opens ONE shared, persistent
// left sidebar (injected into document.body lazily, not per-button) with:
//   - this app's own last-known position/speed/distance/RSSI (instant,
//     from GET /api/aircraft/{icao}/history -- our own DB)
//   - registration/type from api.adsbdb.com, fetched client-side (opening
//     the sidebar IS the click -- never auto-fetched elsewhere); a photo
//     from GET /api/aircraft/{icao}/photo, this app's own server-side
//     proxy to api.planespotters.net -- Planespotters requires a
//     descriptive User-Agent with a contact URL, which a browser's own
//     fetch() can never send (forbidden header), so this one call can't
//     be direct-from-browser the way the type lookup is. See README
//     Security & Privacy.
//   - live tar1090-parity fields (squawk, NAC/SIL/NIC, FMS-selected
//     altitude/heading, wind, mach, ...) via WS /ws/aircraft/{icao} -- a
//     deliberate, narrow real-time exception for one explicitly-selected
//     aircraft (see CLAUDE.md and README Security & Privacy)
//
// Never uses innerHTML with API/aircraft data -- always textContent,
// matching this app's existing convention (callsigns/ICAOs are
// externally-sourced strings).

import { api } from "./api.js";
import { formatDistance, formatAltitude } from "./units.js";

const ADSBDB_TIMEOUT_MS = 6000;

let sidebarEl = null;
let backdropEl = null;
let currentIcao = null;
let currentSocket = null;
let lastFocusedElement = null;

const SIDEBAR_ID = "aircraft-detail-drawer";
const SIDEBAR_TITLE_ID = "aircraft-detail-title";
const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export function isAnyAircraftInfoPanelOpen() {
  return currentIcao !== null;
}

async function fetchJsonWithTimeout(url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error(`aircraft info fetch failed: ${url}`, err);
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function fetchAircraftType(icao) {
  const data = await fetchJsonWithTimeout(
    `https://api.adsbdb.com/v0/aircraft/${encodeURIComponent(icao)}`,
    ADSBDB_TIMEOUT_MS
  );
  return data && data.response && data.response.aircraft ? data.response.aircraft : null;
}

async function fetchAircraftPhoto(icao) {
  try {
    return await api.getAircraftPhoto(icao);
  } catch (err) {
    console.error("aircraft photo fetch failed", err);
    return null;
  }
}

function fmt(value, suffix = "") {
  return value == null ? "--" : `${value}${suffix}`;
}

function fmtRound(value, suffix = "") {
  return value == null ? "--" : `${Math.round(value)}${suffix}`;
}

function buildTable(rows) {
  const table = document.createElement("table");
  table.className = "aircraft-sidebar__table";
  const tbody = document.createElement("tbody");
  for (const [label, value] of rows) {
    const tr = document.createElement("tr");
    const th = document.createElement("th");
    th.textContent = label;
    const td = document.createElement("td");
    td.textContent = value;
    tr.append(th, td);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  return table;
}

function buildSection(title, rows) {
  const section = document.createElement("section");
  section.className = "aircraft-sidebar__section";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.append(heading, buildTable(rows));
  return section;
}

function renderTypeAndPhoto(container, aircraft, photo) {
  container.replaceChildren();

  const typeLine = document.createElement("div");
  if (aircraft) {
    typeLine.textContent = [aircraft.registration, aircraft.icao_type || aircraft.type, aircraft.manufacturer]
      .filter(Boolean)
      .join(" / ");
  } else {
    typeLine.className = "aircraft-info__meta";
    typeLine.textContent = "機体情報は見つかりませんでした(adsbdb.com)";
  }
  container.appendChild(typeLine);

  if (aircraft && aircraft.registered_owner) {
    const ownerLine = document.createElement("div");
    ownerLine.className = "aircraft-info__meta";
    ownerLine.textContent = aircraft.registered_owner;
    container.appendChild(ownerLine);
  }

  if (photo && photo.thumbnail_url) {
    const img = document.createElement("img");
    img.src = photo.thumbnail_url;
    if (photo.thumbnail_width) img.width = photo.thumbnail_width;
    if (photo.thumbnail_height) img.height = photo.thumbnail_height;
    img.alt = "機体写真";
    img.className = "aircraft-info__photo";
    img.loading = "lazy";

    const credit = document.createElement("a");
    credit.href = photo.link;
    credit.target = "_blank";
    credit.rel = "noopener noreferrer";
    credit.className = "aircraft-info__credit";
    credit.textContent = `撮影: ${photo.photographer || "unknown"} (Planespotters.net)`;

    container.append(img, credit);
  } else {
    const noPhoto = document.createElement("div");
    noPhoto.className = "aircraft-info__meta";
    noPhoto.textContent = "写真は見つかりませんでした(Planespotters.net)";
    container.appendChild(noPhoto);
  }
}

function renderOwnData(container, latest) {
  container.replaceChildren();
  if (!latest) {
    const empty = document.createElement("p");
    empty.className = "panel__empty";
    empty.textContent = "自局での観測データはまだありません";
    container.appendChild(empty);
    return;
  }
  container.appendChild(
    buildSection("自局データ", [
      ["高度", formatAltitude(latest.altitude_ft)],
      ["地速", fmt(latest.ground_speed_kt, " kt")],
      ["Track", fmtRound(latest.track_deg, "°")],
      ["昇降率", fmt(latest.vertical_rate_fpm, " fpm")],
      ["距離", formatDistance(latest.distance_km)],
      ["方位", fmtRound(latest.bearing_deg, "°")],
      ["RSSI", fmt(latest.rssi, " dB")],
    ])
  );
}

function renderLive(container, data) {
  container.replaceChildren();
  if (!data || data.received === false) {
    const empty = document.createElement("p");
    empty.className = "panel__empty";
    empty.textContent = "現在readsbから受信していません";
    container.appendChild(empty);
    return;
  }

  container.append(
    buildSection("SIGNAL", [
      ["スコーク", fmt(data.squawk)],
      ["メッセージ数", fmt(data.messages)],
      ["最終位置", fmt(data.seen_pos, " 秒前")],
      ["MLAT/TIS-B", `${data.mlat ? "MLAT" : ""}${data.mlat && data.tisb ? " / " : ""}${data.tisb ? "TIS-B" : ""}` || "--"],
    ]),
    buildSection("SPATIAL", [
      ["気圧高度", formatAltitude(data.alt_baro)],
      ["幾何高度", formatAltitude(data.alt_geom)],
      ["地速", fmt(data.gs, " kt")],
      ["対気速度(IAS/TAS)", `${fmt(data.ias)} / ${fmt(data.tas)}`],
      ["マッハ", fmt(data.mach)],
      ["Track / 磁方位", `${fmtRound(data.track, "°")} / ${fmtRound(data.mag_heading, "°")}`],
      ["ロール", fmt(data.roll, "°")],
      ["昇降率(baro/geom)", `${fmt(data.baro_rate)} / ${fmt(data.geom_rate)} fpm`],
      ["カテゴリ", fmt(data.category)],
    ]),
    buildSection("FMS選択値", [
      ["選択高度", formatAltitude(data.nav_altitude_mcp)],
      ["選択方位", fmt(data.nav_heading, "°")],
      ["QNH", fmt(data.nav_qnh, " hPa")],
    ]),
    buildSection("精度指標(ACCURACY)", [
      ["NIC / NIC_baro", `${fmt(data.nic)} / ${fmt(data.nic_baro)}`],
      ["NACp / NACv", `${fmt(data.nac_p)} / ${fmt(data.nac_v)}`],
      ["SIL", `${fmt(data.sil)} (${fmt(data.sil_type)})`],
      ["Rc", fmt(data.rc, " m")],
    ]),
    buildSection("風・気温", [
      ["風向/風速", `${fmt(data.wd, "°")} / ${fmt(data.ws, " kt")}`],
      ["OAT / TAT", `${fmt(data.oat, "°C")} / ${fmt(data.tat, "°C")}`],
    ])
  );
}

function ensureSidebar() {
  if (sidebarEl) return sidebarEl;

  backdropEl = document.createElement("div");
  backdropEl.className = "aircraft-sidebar-backdrop";
  backdropEl.hidden = true;
  backdropEl.setAttribute("aria-hidden", "true");
  backdropEl.addEventListener("click", closeAircraftSidebar);

  sidebarEl = document.createElement("aside");
  sidebarEl.className = "aircraft-sidebar";
  sidebarEl.id = SIDEBAR_ID;
  sidebarEl.setAttribute("role", "dialog");
  sidebarEl.setAttribute("aria-modal", "true");
  sidebarEl.setAttribute("aria-labelledby", SIDEBAR_TITLE_ID);
  sidebarEl.tabIndex = -1;
  sidebarEl.hidden = true;
  document.body.append(backdropEl, sidebarEl);
  return sidebarEl;
}

function handleDrawerKeydown(event) {
  if (!sidebarEl || sidebarEl.hidden) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeAircraftSidebar();
    return;
  }
  if (event.key !== "Tab") return;

  const focusable = Array.from(sidebarEl.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
    (element) => !element.hidden && element.getAttribute("aria-hidden") !== "true"
  );
  if (focusable.length === 0) {
    event.preventDefault();
    sidebarEl.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (!sidebarEl.contains(document.activeElement)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
  } else if (event.shiftKey && (document.activeElement === first || document.activeElement === sidebarEl)) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

export function closeAircraftSidebar() {
  if (currentSocket) {
    currentSocket.close();
    currentSocket = null;
  }
  currentIcao = null;
  if (sidebarEl) sidebarEl.hidden = true;
  if (backdropEl) backdropEl.hidden = true;
  document.body.classList.remove("aircraft-drawer-open");
  document.removeEventListener("keydown", handleDrawerKeydown, true);
  if (lastFocusedElement && lastFocusedElement.isConnected) lastFocusedElement.focus();
  lastFocusedElement = null;
}

export function openAircraftSidebar(icao) {
  if (currentIcao === icao) {
    closeAircraftSidebar();
    return;
  }
  if (currentSocket) {
    currentSocket.close();
    currentSocket = null;
  }
  const wasOpen = sidebarEl && !sidebarEl.hidden;
  currentIcao = icao;
  if (!wasOpen) {
    lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  }

  const sidebar = ensureSidebar();
  sidebar.hidden = false;
  backdropEl.hidden = false;
  document.body.classList.add("aircraft-drawer-open");
  document.addEventListener("keydown", handleDrawerKeydown, true);
  sidebar.replaceChildren();

  const header = document.createElement("div");
  header.className = "aircraft-sidebar__header";
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "aircraft-sidebar__close";
  closeButton.textContent = "×";
  closeButton.setAttribute("aria-label", "閉じる");
  closeButton.addEventListener("click", closeAircraftSidebar);
  const title = document.createElement("h2");
  title.id = SIDEBAR_TITLE_ID;
  title.textContent = icao;
  const hexLabel = document.createElement("div");
  hexLabel.className = "aircraft-sidebar__hex";
  hexLabel.textContent = `ICAO: ${icao}`;
  header.append(closeButton, title, hexLabel);
  sidebar.appendChild(header);

  requestAnimationFrame(() => {
    if (currentIcao === icao) closeButton.focus();
  });

  const typePhotoSection = document.createElement("div");
  typePhotoSection.className = "aircraft-sidebar__type-photo";
  typePhotoSection.textContent = "読み込み中…";
  sidebar.appendChild(typePhotoSection);

  const ownDataSection = document.createElement("div");
  ownDataSection.textContent = "読み込み中…";
  sidebar.appendChild(ownDataSection);

  const liveSection = document.createElement("div");
  liveSection.textContent = "接続中…";
  sidebar.appendChild(liveSection);

  Promise.all([fetchAircraftType(icao), fetchAircraftPhoto(icao)]).then(([aircraft, photo]) => {
    if (currentIcao !== icao) return;
    renderTypeAndPhoto(typePhotoSection, aircraft, photo);
  });

  api
    .getAircraftHistory(icao)
    .then((history) => {
      if (currentIcao !== icao) return;
      if (history.last_callsign) title.textContent = history.last_callsign;
      renderOwnData(ownDataSection, history.latest_observation);
    })
    .catch((err) => {
      console.error("aircraft history fetch failed", err);
      if (currentIcao !== icao) return;
      ownDataSection.textContent =
        err && err.status === 404 ? "自局での観測データはありません" : "自局データの取得に失敗しました";
    });

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/aircraft/${encodeURIComponent(icao)}`);
  currentSocket = socket;
  socket.addEventListener("message", (event) => {
    if (currentIcao !== icao) return;
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.error("aircraft live message parse failed", err);
      return;
    }
    renderLive(liveSection, data);
  });
  socket.addEventListener("close", () => {
    if (currentIcao === icao) liveSection.textContent = "ライブ接続が切断されました";
  });
  socket.addEventListener("error", () => {
    if (currentIcao === icao) liveSection.textContent = "ライブ接続エラー";
  });
}

// Returns a <button> that opens the shared sidebar for `icao` on click.
// `label` defaults to the icao itself so callers embedding this in a
// compact table cell (the ranking/recent tables) can pass the existing
// callsign/icao text as the trigger rather than adding extra chrome.
export function createAircraftInfoTrigger(icao, label = icao) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "aircraft-info-trigger";
  button.setAttribute("aria-haspopup", "dialog");
  button.setAttribute("aria-controls", SIDEBAR_ID);
  button.textContent = label;
  button.addEventListener("click", () => openAircraftSidebar(icao));
  return button;
}
