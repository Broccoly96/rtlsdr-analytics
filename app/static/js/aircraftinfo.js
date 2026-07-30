// aircraftinfo.js -- click-triggered aircraft registration/type/photo
// lookup. Both api.adsbdb.com (registration/type/manufacturer) and
// api.planespotters.net (photo + photographer credit) are third-party
// services called directly from the browser -- only when the user
// explicitly clicks, never auto-fetched or prefetched, never proxied or
// cached server-side. This is this app's one deliberate exception to
// "no calling home" (see README Security & Privacy); every other call in
// this app goes to its own origin.

const ADSBDB_TIMEOUT_MS = 6000;
const PLANESPOTTERS_TIMEOUT_MS = 6000;

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
  const data = await fetchJsonWithTimeout(
    `https://api.planespotters.net/pub/photos/hex/${encodeURIComponent(icao)}`,
    PLANESPOTTERS_TIMEOUT_MS
  );
  return data && Array.isArray(data.photos) && data.photos.length > 0 ? data.photos[0] : null;
}

function renderResult(panel, aircraft, photo) {
  panel.replaceChildren();

  const typeLine = document.createElement("div");
  if (aircraft) {
    typeLine.textContent = [aircraft.registration, aircraft.icao_type || aircraft.type, aircraft.manufacturer]
      .filter(Boolean)
      .join(" / ");
  } else {
    typeLine.className = "aircraft-info__meta";
    typeLine.textContent = "機体情報は見つかりませんでした(adsbdb.com)";
  }
  panel.appendChild(typeLine);

  if (aircraft && aircraft.registered_owner) {
    const ownerLine = document.createElement("div");
    ownerLine.className = "aircraft-info__meta";
    ownerLine.textContent = aircraft.registered_owner;
    panel.appendChild(ownerLine);
  }

  if (photo && photo.thumbnail && photo.thumbnail.src) {
    const img = document.createElement("img");
    img.src = photo.thumbnail.src;
    if (photo.thumbnail.size) {
      img.width = photo.thumbnail.size.width;
      img.height = photo.thumbnail.size.height;
    }
    img.alt = "機体写真";
    img.className = "aircraft-info__photo";
    img.loading = "lazy";

    const credit = document.createElement("a");
    credit.href = photo.link;
    credit.target = "_blank";
    credit.rel = "noopener noreferrer";
    credit.className = "aircraft-info__credit";
    credit.textContent = `撮影: ${photo.photographer || "unknown"} (Planespotters.net)`;

    panel.append(img, credit);
  } else {
    const noPhoto = document.createElement("div");
    noPhoto.className = "aircraft-info__meta";
    noPhoto.textContent = "写真は見つかりませんでした(Planespotters.net)";
    panel.appendChild(noPhoto);
  }
}

// Tracks how many info panels are currently open, so a page that rebuilds
// its DOM on a refresh timer (ui.js's ranking/recent tables) can pause
// that rebuild while the user has a panel open to read -- otherwise an
// open popup (and its already-fetched data) gets yanked away and reset
// mid-read on the next poll.
let openPanelCount = 0;

export function isAnyAircraftInfoPanelOpen() {
  return openPanelCount > 0;
}

// Returns a <button> that toggles an inline info panel on click, fetching
// (in parallel, once, cached in closure) from adsbdb.com and
// Planespotters.net the first time it's opened. `label` defaults to the
// icao itself so callers embedding this in a compact table cell (the
// ranking/recent tables) can pass the existing callsign/icao text as the
// trigger rather than adding extra chrome.
export function createAircraftInfoTrigger(icao, label = icao) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "aircraft-info-trigger";
  button.textContent = label;

  let panel = null;
  let loaded = false;

  button.addEventListener("click", async () => {
    if (!panel) {
      panel = document.createElement("div");
      panel.className = "aircraft-info";
      panel.hidden = true;
      button.insertAdjacentElement("afterend", panel);
    }

    panel.hidden = !panel.hidden;
    openPanelCount += panel.hidden ? -1 : 1;
    if (panel.hidden || loaded) return;

    loaded = true;
    panel.textContent = "読み込み中…(adsbdb.com / Planespotters.netへ問い合わせています)";
    const [aircraft, photo] = await Promise.all([fetchAircraftType(icao), fetchAircraftPhoto(icao)]);
    renderResult(panel, aircraft, photo);
  });

  return button;
}
