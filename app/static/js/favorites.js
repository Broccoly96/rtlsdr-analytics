// favorites.js -- server-backed favorites (GET/POST/DELETE /api/favorites),
// replacing the previous pure-localStorage design (Milestone JJ of the
// 2026-08 feature roadmap; see app/api/routers/favorites.py's docstring for
// why this app now has mutating endpoints at all). A one-time migration
// copies any pre-existing localStorage favorites to the server on first
// load, then clears the old key, so nobody's existing favorites are lost.
//
// isFavorite() stays synchronous (an in-memory Set loaded once via
// loadFavorites(), same "read once at load" contract as this app's other
// settings modules) so callers that used to check localStorage
// synchronously don't all need to become async -- only the actual
// add/remove calls hit the network.

import { api } from "./api.js";

const LEGACY_FAVORITES_KEY = "adsb-analytics:favorites";

let favoritesCache = new Set();

async function migrateLegacyFavorites() {
  let legacy = [];
  try {
    const raw = localStorage.getItem(LEGACY_FAVORITES_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    legacy = Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.error("failed to read legacy favorites from localStorage", err);
  }
  if (legacy.length === 0) return;

  for (const icao of legacy) {
    try {
      await api.addFavorite(icao);
    } catch (err) {
      // A 404 here means the aircraft no longer exists server-side (it
      // was purged, or never really existed) -- either way, dropping it
      // silently is correct; anything else just logs and moves on so one
      // bad entry can't block migrating the rest.
      console.error(`failed to migrate legacy favorite ${icao}`, err);
    }
  }
  try {
    localStorage.removeItem(LEGACY_FAVORITES_KEY);
  } catch (err) {
    console.error("failed to clear legacy favorites from localStorage", err);
  }
}

// Called once, early, in history.js's main() -- must resolve before any
// isFavorite()/toggleFavorite() call.
export async function loadFavorites() {
  await migrateLegacyFavorites();
  try {
    const response = await api.getFavorites();
    favoritesCache = new Set(response.favorites.map((entry) => entry.icao));
  } catch (err) {
    console.error("failed to load favorites", err);
    favoritesCache = new Set();
  }
}

export function isFavorite(icao) {
  return favoritesCache.has(icao);
}

export async function toggleFavorite(icao) {
  if (favoritesCache.has(icao)) {
    await api.removeFavorite(icao);
    favoritesCache.delete(icao);
  } else {
    await api.addFavorite(icao);
    favoritesCache.add(icao);
  }
}
