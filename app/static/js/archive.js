// archive.js -- entrypoint for archive.html: a searchable/sortable,
// paginated browse over every aircraft ever seen (GET /api/aircraft/archive).

import { api } from "./api.js";
import { ui } from "./ui.js";
import { createAircraftInfoTrigger } from "./aircraftinfo.js";
import { setNationalityBlocks } from "./nationality.js";
import { registerServiceWorker } from "./pwa.js";
import { t, applyStaticTranslations } from "./i18n.js";

const PAGE_SIZE = 50;

function renderVersion(config) {
  const el = document.getElementById("app-version");
  if (!el) return;
  if (!config.version) {
    el.textContent = "version unknown";
    return;
  }
  el.textContent = config.git_revision ? `v${config.version} (${config.git_revision})` : `v${config.version}`;
}

let currentOffset = 0;
let currentQuery = "";
let currentSort = "last_seen_at";

function addCell(row, content) {
  const td = document.createElement("td");
  if (content instanceof Node) td.appendChild(content);
  else td.textContent = content;
  row.appendChild(td);
}

async function refresh() {
  const tbody = document.querySelector("#archive-table tbody");
  const emptyEl = document.getElementById("archive-empty");
  const pageInfo = document.getElementById("archive-page-info");
  const prevButton = document.getElementById("archive-prev");
  const nextButton = document.getElementById("archive-next");
  if (!tbody) return;

  try {
    const data = await api.getArchive({
      q: currentQuery || undefined,
      sort: currentSort,
      descending: true,
      limit: PAGE_SIZE,
      offset: currentOffset,
    });
    tbody.replaceChildren();
    if (emptyEl) emptyEl.hidden = data.aircraft.length > 0;

    for (const entry of data.aircraft) {
      const row = document.createElement("tr");
      addCell(row, createAircraftInfoTrigger(entry.icao, entry.callsign || entry.icao));
      addCell(row, entry.icao);
      addCell(row, ui.formatTime(entry.first_seen_at));
      addCell(row, ui.formatTime(entry.last_seen_at));
      addCell(row, String(entry.days_observed));
      addCell(row, String(entry.total_pass_count));
      tbody.appendChild(row);
    }

    if (pageInfo) {
      const from = data.total === 0 ? 0 : currentOffset + 1;
      const to = Math.min(currentOffset + PAGE_SIZE, data.total);
      pageInfo.textContent = t("archive.pageInfo", { from, to, total: data.total });
    }
    if (prevButton) prevButton.disabled = currentOffset === 0;
    if (nextButton) nextButton.disabled = currentOffset + PAGE_SIZE >= data.total;
  } catch (err) {
    console.error("archive fetch failed", err);
  }
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (err) {
    console.error("failed to load /api/config", err);
    config = { version: null, git_revision: null };
  }
  applyStaticTranslations();
  renderVersion(config);
  setNationalityBlocks(config.nationality_blocks);
  registerServiceWorker();
  ui.setTimezone(config.display_timezone || "UTC");

  const searchInput = document.getElementById("archive-search");
  const sortSelect = document.getElementById("archive-sort");
  const prevButton = document.getElementById("archive-prev");
  const nextButton = document.getElementById("archive-next");

  // Populated from the shared nav search box (every page's <form
  // class="nav-search"> submits here as a plain GET, no JS needed on the
  // originating page) or a direct link/bookmark.
  const urlParams = new URLSearchParams(window.location.search);
  const initialQuery = urlParams.get("q");
  if (initialQuery && searchInput) {
    searchInput.value = initialQuery;
    currentQuery = initialQuery.trim();
  }

  let searchDebounce = null;
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        currentQuery = searchInput.value.trim();
        currentOffset = 0;
        refresh();
      }, 300);
    });
  }
  if (sortSelect) {
    sortSelect.addEventListener("change", () => {
      currentSort = sortSelect.value;
      currentOffset = 0;
      refresh();
    });
  }
  if (prevButton) {
    prevButton.addEventListener("click", () => {
      currentOffset = Math.max(0, currentOffset - PAGE_SIZE);
      refresh();
    });
  }
  if (nextButton) {
    nextButton.addEventListener("click", () => {
      currentOffset += PAGE_SIZE;
      refresh();
    });
  }

  await refresh();
}

main().catch((err) => {
  console.error("archive page failed to start", err);
});
