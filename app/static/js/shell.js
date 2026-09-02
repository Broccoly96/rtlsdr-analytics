// shell.js -- enhances the plain <nav class="app-nav"> markup already
// present in every page's HTML (a flat list of <a> tags, kept that way so
// the page works with JS disabled/broken) into the icon rail + mobile
// bottom-nav/"more" dialog from the PR#2 UI refresh. Runs as a module
// (not a classic deferred script) purely so it can import i18n.js: labels
// come from the same t()/data-i18n system as the rest of the page, not a
// second hardcoded copy, and stay correct if the language setting changes
// under a `reload to apply` per i18n.js's documented zero-live-rerender
// design (matching every other page's own applyStaticTranslations() call).
//
// Runs *before* each page's own module script (document order: this tag
// always precedes the page's main module in every page's HTML), so any
// data-i18n attribute this module leaves on new nodes still gets picked
// up correctly if applyStaticTranslations() is invoked again downstream.

import { t, applyStaticTranslations } from "./i18n.js";

const SVG_NS = "http://www.w3.org/2000/svg";

const navItems = [
  { page: "dashboard", href: "/", key: "nav.dashboard", icon: "dashboard", primary: true },
  { page: "daily", href: "/static/daily.html", key: "nav.daily", icon: "today", primary: true },
  { page: "fullmap", href: "/static/fullmap.html", key: "nav.trackMap", icon: "map", primary: true },
  { page: "receiver", href: "/static/receiver.html", key: "nav.receiver", icon: "signal", primary: true },
  { page: "globe", href: "/static/globe.html", key: "nav.globe", icon: "globe" },
  { page: "history", href: "/static/history.html", key: "nav.history", icon: "history" },
  { page: "rawdata", href: "/static/rawdata.html", key: "nav.rawdata", icon: "data" },
  { page: "flags", href: "/static/flags.html", key: "nav.flags", icon: "flag" },
  { page: "badges", href: "/static/badges.html", key: "nav.badges", icon: "badge" },
  { page: "archive", href: "/static/archive.html", key: "nav.archive", icon: "archive" },
  { page: "changelog", href: "/static/changelog.html", key: "nav.changelog", icon: "changelog" },
  { page: "settings", href: "/static/settings.html", key: "nav.settings", icon: "settings" },
];

const iconPaths = {
  dashboard: ["M4 4h6v6H4z", "M14 4h6v10h-6z", "M4 14h6v6H4z", "M14 18h6v2h-6z"],
  today: ["M7 3v3M17 3v3M4 9h16", "M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z", "M8 13h3v3H8z"],
  map: ["m3 6 5-3 8 3 5-3v15l-5 3-8-3-5 3Z", "M8 3v15M16 6v15"],
  signal: ["M5 20v-4M10 20v-8M15 20V8M20 20V4"],
  globe: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M3 12h18M12 3c2.5 2.5 3.5 5.5 3.5 9S14.5 18.5 12 21M12 3c-2.5 2.5-3.5 5.5-3.5 9s1 6.5 3.5 9"],
  history: ["M3 12a9 9 0 1 0 3-6.7L3 8", "M3 3v5h5M12 7v5l3 2"],
  data: ["M4 5h16v14H4z", "M8 9h2M8 13h2M8 17h2M13 9h3M13 13h3M13 17h3"],
  flag: ["M5 3v18", "M5 4h13l-2.5 3.5L18 11H5"],
  badge: ["M12 3l2.2 4.6 5 .7-3.6 3.6.9 5-4.5-2.4-4.5 2.4.9-5-3.6-3.6 5-.7Z"],
  archive: ["M4 4h16v4H4z", "M5 8h14v12H5z", "M9.5 12h5"],
  changelog: ["M5 4h14v16H5z", "M8 8h8M8 12h8M8 16h5"],
  settings: ["M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z", "M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1 1.56V20h-3v-.08a1.7 1.7 0 0 0-1-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7.08 15a1.7 1.7 0 0 0-1.56-1H5v-3h.52a1.7 1.7 0 0 0 1.56-1 1.7 1.7 0 0 0-.34-1.88l-.06-.06L8.8 5.94l.06.06a1.7 1.7 0 0 0 1.88.34 1.7 1.7 0 0 0 1-1.56V4h3v.78a1.7 1.7 0 0 0 1 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06A1.7 1.7 0 0 0 19.4 10a1.7 1.7 0 0 0 1.56 1H21v3h-.04a1.7 1.7 0 0 0-1.56 1Z"],
  more: ["M5 12h.01M12 12h.01M19 12h.01"],
  close: ["m6 6 12 12M18 6 6 18"],
};

function createIcon(name) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.classList.add("nav-icon");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.75");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  for (const d of iconPaths[name]) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

function makeNavLink(item, className) {
  const link = document.createElement("a");
  link.className = className;
  link.href = item.href;
  link.dataset.page = item.page;
  link.append(createIcon(item.icon));
  const label = document.createElement("span");
  label.className = `${className}__label`;
  label.dataset.i18n = item.key;
  label.textContent = t(item.key);
  link.append(label);
  if (document.body.dataset.page === item.page) link.setAttribute("aria-current", "page");
  return link;
}

function enhanceRail() {
  const nav = document.querySelector(".app-nav");
  if (!nav) return;

  const brand = document.createElement("a");
  brand.className = "app-nav__brand";
  brand.href = "/";
  brand.dataset.i18nAriaLabel = "nav.homeAriaLabel";
  brand.setAttribute("aria-label", t("nav.homeAriaLabel"));
  const mark = document.createElement("span");
  mark.className = "app-nav__mark";
  mark.textContent = "A";
  const name = document.createElement("span");
  name.className = "app-nav__brand-name";
  name.textContent = "ADS-B Analytics";
  brand.append(mark, name);

  const list = document.createElement("div");
  list.className = "app-nav__list";
  for (const link of nav.querySelectorAll(":scope > a")) {
    const item = navItems.find(({ href }) => link.getAttribute("href") === href);
    if (!item) continue;
    // The original <a> carried its own data-i18n (translating the whole
    // element's textContent) -- that would fight with the icon we're
    // about to insert, since applyStaticTranslations() would wipe out
    // the <svg> along with the text. Move the i18n binding onto the new
    // label span instead, which is the only text node left in the link.
    link.removeAttribute("data-i18n");
    link.className = "app-nav__link";
    link.dataset.page = item.page;
    link.textContent = "";
    link.append(createIcon(item.icon));
    const label = document.createElement("span");
    label.className = "app-nav__label";
    label.dataset.i18n = item.key;
    label.textContent = t(item.key);
    link.append(label);
    list.append(link);
  }
  nav.prepend(brand);
  nav.append(list);
}

function createMobileNavigation() {
  const nav = document.createElement("nav");
  nav.className = "mobile-nav";
  nav.dataset.i18nAriaLabel = "nav.mobileAriaLabel";
  nav.setAttribute("aria-label", t("nav.mobileAriaLabel"));

  for (const item of navItems.filter(({ primary }) => primary)) {
    nav.append(makeNavLink(item, "mobile-nav__link"));
  }

  const moreButton = document.createElement("button");
  moreButton.type = "button";
  moreButton.className = "mobile-nav__link";
  moreButton.id = "mobile-more-toggle";
  moreButton.setAttribute("aria-haspopup", "dialog");
  moreButton.setAttribute("aria-controls", "mobile-more-dialog");
  moreButton.setAttribute("aria-expanded", "false");
  moreButton.append(createIcon("more"));
  const moreLabel = document.createElement("span");
  moreLabel.className = "mobile-nav__link__label";
  moreLabel.dataset.i18n = "nav.more";
  moreLabel.textContent = t("nav.more");
  moreButton.append(moreLabel);
  if (navItems.some(({ page, primary }) => !primary && page === document.body.dataset.page)) {
    moreButton.classList.add("is-current");
    moreButton.setAttribute("aria-current", "page");
  }
  nav.append(moreButton);

  const dialog = document.createElement("dialog");
  dialog.className = "mobile-more";
  dialog.id = "mobile-more-dialog";
  dialog.setAttribute("aria-labelledby", "mobile-more-title");

  const panel = document.createElement("div");
  panel.className = "mobile-more__panel";
  const header = document.createElement("div");
  header.className = "mobile-more__header";
  const title = document.createElement("h2");
  title.id = "mobile-more-title";
  title.dataset.i18n = "nav.morePagesHeading";
  title.textContent = t("nav.morePagesHeading");
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "mobile-more__close";
  closeButton.dataset.i18nAriaLabel = "nav.closeMenu";
  closeButton.setAttribute("aria-label", t("nav.closeMenu"));
  closeButton.append(createIcon("close"));
  header.append(title, closeButton);

  // Same global search as the desktop rail (nav-search in the page's own
  // markup) -- the rail hides entirely below 600px, so without this the
  // mobile view would have no way to reach the archive search at all.
  const searchForm = document.createElement("form");
  searchForm.className = "nav-search mobile-more__search";
  searchForm.action = "/static/archive.html";
  searchForm.method = "get";
  searchForm.setAttribute("role", "search");
  const searchInput = document.createElement("input");
  searchInput.type = "search";
  searchInput.name = "q";
  searchInput.className = "nav-search__input";
  searchInput.dataset.i18nPlaceholder = "nav.searchPlaceholder";
  searchInput.placeholder = t("nav.searchPlaceholder");
  searchForm.append(searchInput);

  const links = document.createElement("div");
  links.className = "mobile-more__list";
  for (const item of navItems.filter(({ primary }) => !primary)) {
    links.append(makeNavLink(item, "mobile-more__link"));
  }
  panel.append(header, searchForm, links);
  dialog.append(panel);
  document.body.append(nav, dialog);

  let returnFocus = null;
  const open = () => {
    returnFocus = document.activeElement;
    moreButton.setAttribute("aria-expanded", "true");
    document.body.classList.add("has-modal-open");
    dialog.showModal();
    const currentLink = dialog.querySelector("[aria-current='page']");
    if (currentLink instanceof HTMLElement) currentLink.focus();
    else closeButton.focus();
  };
  const close = () => {
    if (dialog.open) dialog.close();
  };
  const restore = () => {
    moreButton.setAttribute("aria-expanded", "false");
    document.body.classList.remove("has-modal-open");
    if (returnFocus instanceof HTMLElement) returnFocus.focus();
    returnFocus = null;
  };

  moreButton.addEventListener("click", open);
  closeButton.addEventListener("click", close);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) close();
  });
  dialog.addEventListener("close", restore);
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    close();
  });
}

enhanceRail();
createMobileNavigation();
// Covers the handful of data-i18n-aria-label/-placeholder attributes this
// module just set on brand-new nodes (search input, dialog) in one pass,
// consistent with how every page's own main() applies translations once.
applyStaticTranslations();
