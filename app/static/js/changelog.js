// changelog.js -- source-controlled release notes; no database/API needed.

import { api } from "./api.js";
import { applyStaticTranslations, t } from "./i18n.js";
import { registerServiceWorker } from "./pwa.js";

const ENTRIES = [
  { version: "0.15.0", date: "2026-09-02", summary: "changelog.v0150" },
  { version: "0.14.8", date: "2026-09-02", summary: "changelog.v0148" },
  { version: "0.14.7", date: "2026-09-02", summary: "changelog.v0147" },
  { version: "0.14.6", date: "2026-08-02", summary: "changelog.v0146" },
  { version: "0.14.5", date: "2026-08-02", summary: "changelog.v0145" },
  { version: "0.14.4", date: "2026-08-02", summary: "changelog.v0144" },
  { version: "0.14.3", date: "2026-08-02", summary: "changelog.v0143" },
  { version: "0.14.2", date: "2026-08-02", summary: "changelog.v0142" },
  { version: "0.14.1", date: "2026-08-02", summary: "changelog.v0141" },
  { version: "0.14.0", date: "2026-08-01", summary: "changelog.v0140" },
];

function renderVersion(config) {
  const element = document.getElementById("app-version");
  if (!element) return;
  if (!config.version) {
    element.textContent = "version unknown";
    return;
  }
  element.textContent = config.git_revision
    ? `v${config.version} (${config.git_revision})`
    : `v${config.version}`;
}

function renderEntries() {
  const list = document.getElementById("changelog-list");
  if (!list) return;
  for (const entry of ENTRIES) {
    const item = document.createElement("li");
    item.className = "changelog-entry";
    const header = document.createElement("div");
    header.className = "changelog-entry__header";
    const version = document.createElement("h2");
    version.className = "changelog-entry__version";
    version.textContent = `v${entry.version}`;
    const date = document.createElement("time");
    date.className = "changelog-entry__date";
    date.dateTime = entry.date;
    date.textContent = entry.date;
    header.append(version, date);
    const summary = document.createElement("p");
    summary.className = "changelog-entry__summary";
    summary.dataset.i18n = entry.summary;
    summary.textContent = t(entry.summary);
    item.append(header, summary);
    list.append(item);
  }
}

async function main() {
  let config;
  try {
    config = await api.getConfig();
  } catch (error) {
    console.error("failed to load /api/config", error);
    config = { version: null, git_revision: null };
  }
  applyStaticTranslations();
  renderVersion(config);
  renderEntries();
  applyStaticTranslations();
  registerServiceWorker();
}

main().catch((error) => console.error("changelog page failed to start", error));
