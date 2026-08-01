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
import { t } from "./i18n.js";
import { countryForIcao, flagEmoji } from "./nationality.js";

const ADSBDB_TIMEOUT_MS = 6000;

let sidebarEl = null;
let currentIcao = null;
let currentSocket = null;

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
    typeLine.textContent = t("aircraftinfo.notFound");
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
    img.alt = t("aircraftinfo.photoAlt");
    img.className = "aircraft-info__photo";
    img.loading = "lazy";

    const credit = document.createElement("a");
    credit.href = photo.link;
    credit.target = "_blank";
    credit.rel = "noopener noreferrer";
    credit.className = "aircraft-info__credit";
    credit.textContent = t("aircraftinfo.photoCredit", { photographer: photo.photographer || "unknown" });

    container.append(img, credit);
  } else {
    const noPhoto = document.createElement("div");
    noPhoto.className = "aircraft-info__meta";
    noPhoto.textContent = t("aircraftinfo.noPhoto");
    container.appendChild(noPhoto);
  }
}

function renderOwnData(container, latest) {
  container.replaceChildren();
  if (!latest) {
    const empty = document.createElement("p");
    empty.className = "panel__empty";
    empty.textContent = t("aircraftinfo.noOwnData");
    container.appendChild(empty);
    return;
  }
  container.appendChild(
    buildSection(t("aircraftinfo.ownDataSection"), [
      [t("common.altitude"), formatAltitude(latest.altitude_ft)],
      [t("aircraftinfo.groundSpeed"), fmt(latest.ground_speed_kt, " kt")],
      ["Track", fmtRound(latest.track_deg, "°")],
      [t("aircraftinfo.verticalRate"), fmt(latest.vertical_rate_fpm, " fpm")],
      [t("common.distance"), formatDistance(latest.distance_km)],
      [t("aircraftinfo.bearing"), fmtRound(latest.bearing_deg, "°")],
      ["RSSI", fmt(latest.rssi, " dB")],
    ])
  );
}

function renderLive(container, data) {
  container.replaceChildren();
  if (!data || data.received === false) {
    const empty = document.createElement("p");
    empty.className = "panel__empty";
    empty.textContent = t("aircraftinfo.noLiveData");
    container.appendChild(empty);
    return;
  }

  container.append(
    buildSection("SIGNAL", [
      [t("aircraftinfo.squawk"), fmt(data.squawk)],
      [t("receiver.messageCount"), fmt(data.messages)],
      [t("aircraftinfo.lastPosition"), fmt(data.seen_pos, t("aircraftinfo.secondsAgoSuffix"))],
      ["MLAT/TIS-B", `${data.mlat ? "MLAT" : ""}${data.mlat && data.tisb ? " / " : ""}${data.tisb ? "TIS-B" : ""}` || "--"],
    ]),
    buildSection("SPATIAL", [
      [t("aircraftinfo.baroAltitude"), formatAltitude(data.alt_baro)],
      [t("aircraftinfo.geomAltitude"), formatAltitude(data.alt_geom)],
      [t("aircraftinfo.groundSpeed"), fmt(data.gs, " kt")],
      [t("aircraftinfo.iasTasLabel"), `${fmt(data.ias)} / ${fmt(data.tas)}`],
      [t("aircraftinfo.mach"), fmt(data.mach)],
      [t("aircraftinfo.trackMagHeading"), `${fmtRound(data.track, "°")} / ${fmtRound(data.mag_heading, "°")}`],
      [t("aircraftinfo.roll"), fmt(data.roll, "°")],
      [t("aircraftinfo.verticalRateBaroGeom"), `${fmt(data.baro_rate)} / ${fmt(data.geom_rate)} fpm`],
      [t("aircraftinfo.category"), fmt(data.category)],
    ]),
    buildSection(t("aircraftinfo.fmsSection"), [
      [t("aircraftinfo.selectedAltitude"), formatAltitude(data.nav_altitude_mcp)],
      [t("aircraftinfo.selectedHeading"), fmt(data.nav_heading, "°")],
      ["QNH", fmt(data.nav_qnh, " hPa")],
    ]),
    buildSection(t("aircraftinfo.accuracySection"), [
      ["NIC / NIC_baro", `${fmt(data.nic)} / ${fmt(data.nic_baro)}`],
      ["NACp / NACv", `${fmt(data.nac_p)} / ${fmt(data.nac_v)}`],
      ["SIL", `${fmt(data.sil)} (${fmt(data.sil_type)})`],
      ["Rc", fmt(data.rc, " m")],
    ]),
    buildSection(t("aircraftinfo.windTempSection"), [
      [t("aircraftinfo.windDirSpeed"), `${fmt(data.wd, "°")} / ${fmt(data.ws, " kt")}`],
      ["OAT / TAT", `${fmt(data.oat, "°C")} / ${fmt(data.tat, "°C")}`],
    ])
  );
}

function ensureSidebar() {
  if (sidebarEl) return sidebarEl;
  sidebarEl = document.createElement("aside");
  sidebarEl.className = "aircraft-sidebar";
  sidebarEl.hidden = true;
  document.body.appendChild(sidebarEl);
  return sidebarEl;
}

export function closeAircraftSidebar() {
  if (currentSocket) {
    currentSocket.close();
    currentSocket = null;
  }
  currentIcao = null;
  if (sidebarEl) sidebarEl.hidden = true;
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
  currentIcao = icao;

  const sidebar = ensureSidebar();
  sidebar.hidden = false;
  sidebar.replaceChildren();

  const header = document.createElement("div");
  header.className = "aircraft-sidebar__header";
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "aircraft-sidebar__close";
  closeButton.textContent = "×";
  closeButton.setAttribute("aria-label", t("aircraftinfo.close"));
  closeButton.addEventListener("click", closeAircraftSidebar);
  const title = document.createElement("h2");
  title.textContent = icao;
  const hexLabel = document.createElement("div");
  hexLabel.className = "aircraft-sidebar__hex";
  // The flag lives in `hexLabel`, not `title` -- title.textContent gets
  // overwritten once the callsign loads (below), which would silently
  // wipe a flag placed inside it; hexLabel is never touched again.
  const country = countryForIcao(icao);
  if (country) {
    const countryName = t(`nationality.country.${country.code}`);
    const flagSpan = document.createElement("span");
    flagSpan.className = "aircraft-sidebar__flag";
    flagSpan.textContent = flagEmoji(country.code);
    flagSpan.title = countryName;
    flagSpan.setAttribute("aria-label", countryName);
    hexLabel.appendChild(flagSpan);
  }
  hexLabel.appendChild(document.createTextNode(t("aircraftinfo.icaoLabel", { icao })));
  header.append(closeButton, title, hexLabel);
  sidebar.appendChild(header);

  const trackExportRow = document.createElement("div");
  trackExportRow.className = "aircraft-sidebar__track-export";
  const gpxLink = document.createElement("a");
  gpxLink.href = `/api/aircraft/${encodeURIComponent(icao)}/positions.gpx?hours=24`;
  gpxLink.download = "";
  gpxLink.className = "csv-link";
  gpxLink.textContent = t("aircraftinfo.downloadGpx");
  const kmlLink = document.createElement("a");
  kmlLink.href = `/api/aircraft/${encodeURIComponent(icao)}/positions.kml?hours=24`;
  kmlLink.download = "";
  kmlLink.className = "csv-link";
  kmlLink.textContent = t("aircraftinfo.downloadKml");
  trackExportRow.append(gpxLink, kmlLink);
  sidebar.appendChild(trackExportRow);

  const typePhotoSection = document.createElement("div");
  typePhotoSection.className = "aircraft-sidebar__type-photo";
  typePhotoSection.textContent = t("index.loading");
  sidebar.appendChild(typePhotoSection);

  const ownDataSection = document.createElement("div");
  ownDataSection.textContent = t("index.loading");
  sidebar.appendChild(ownDataSection);

  const liveSection = document.createElement("div");
  liveSection.textContent = t("rawdata.connecting");
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
        err && err.status === 404 ? t("aircraftinfo.noOwnDataFound") : t("aircraftinfo.ownDataFetchFailed");
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
    if (currentIcao === icao) liveSection.textContent = t("aircraftinfo.liveDisconnected");
  });
  socket.addEventListener("error", () => {
    if (currentIcao === icao) liveSection.textContent = t("aircraftinfo.liveError");
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
  button.textContent = label;
  button.addEventListener("click", () => openAircraftSidebar(icao));
  return button;
}
