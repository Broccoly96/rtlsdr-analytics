// dashboard-layout.js -- optional show/hide of dashboard sections
// (Milestone RR). Pure client-side localStorage, same "read once at load,
// reload to see a change" contract as units.js/track-settings.js -- no
// live re-layout while the dashboard tab itself stays open.

const HIDDEN_SECTIONS_KEY = "adsb-analytics:dashboard-hidden-sections";

export const DASHBOARD_SECTIONS = ["map", "traffic", "distribution", "rankings"];

export function getHiddenSections() {
  try {
    const raw = localStorage.getItem(HIDDEN_SECTIONS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((s) => DASHBOARD_SECTIONS.includes(s)) : [];
  } catch (err) {
    console.error("failed to read dashboard section visibility from localStorage", err);
    return [];
  }
}

export function setHiddenSections(hidden) {
  try {
    localStorage.setItem(HIDDEN_SECTIONS_KEY, JSON.stringify(hidden));
  } catch (err) {
    console.error("failed to persist dashboard section visibility to localStorage", err);
  }
}

// Called once, early, in main.js's main() -- before chart creation isn't
// required (a 0-size ECharts container at creation time is harmless if
// the section is simply never shown this session).
export function applyDashboardLayout(root = document) {
  const hidden = new Set(getHiddenSections());
  for (const section of DASHBOARD_SECTIONS) {
    const el = root.querySelector(`[data-dashboard-section="${section}"]`);
    if (el) el.hidden = hidden.has(section);
  }
}
