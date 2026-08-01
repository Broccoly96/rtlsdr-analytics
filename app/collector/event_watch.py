"""Collector-side event watchers for Milestone KK's two webhook alert
types (emergency squawk, favorite aircraft seen).

Both check the *raw* per-poll aircraft list -- not the normalized/sampled
observations app/collector/sampling.py produces -- because an aircraft can
squawk an emergency code (or a favorited aircraft can appear) between
persisted position samples (PositionSampler only samples ~every 30s or on
significant change); checking the raw poll is the only way not to miss a
transition that happens to fall in that gap. Neither watcher persists
anything -- both are purely in-memory, notify-only, reset on collector
restart, matching this milestone's deliberately narrow v1 scope.

Both are stateful across polls so a webhook fires once per *transition*
into the event (not-active -> active), never once per poll while the
event continues -- otherwise a lingering emergency squawk would re-fire a
notification every ~5s for as long as it's squawked.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

EMERGENCY_SQUAWKS = frozenset({"7500", "7600", "7700"})
FAVORITES_REFRESH_INTERVAL_SECONDS = 60.0

NotifySquawkFn = Callable[[str, str, str | None], Awaitable[None]]
NotifyFavoriteFn = Callable[[str, str | None], Awaitable[None]]
LoadFavoriteIcaosFn = Callable[[], Awaitable[set[str]]]


def _extract_callsign(raw: dict[str, Any]) -> str | None:
    value = raw.get("flight")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _iter_raw_entries(raw_aircraft: list[Any]):
    for raw in raw_aircraft:
        if isinstance(raw, dict) and isinstance(raw.get("hex"), str):
            yield raw


class EmergencySquawkWatcher:
    def __init__(self, *, enabled: bool, notify: NotifySquawkFn) -> None:
        self._enabled = enabled
        self._notify = notify
        self._active: set[str] = set()

    async def check(self, raw_aircraft: list[Any]) -> None:
        if not self._enabled:
            return
        seen_now: set[str] = set()
        for raw in _iter_raw_entries(raw_aircraft):
            squawk = raw.get("squawk")
            if squawk not in EMERGENCY_SQUAWKS:
                continue
            icao = raw["hex"]
            seen_now.add(icao)
            if icao not in self._active:
                logger.warning("emergency squawk detected: icao=%s squawk=%s", icao, squawk)
                await self._notify(icao, squawk, _extract_callsign(raw))
        self._active = seen_now


class FavoriteSeenWatcher:
    def __init__(
        self,
        *,
        enabled: bool,
        notify: NotifyFavoriteFn,
        load_favorite_icaos: LoadFavoriteIcaosFn,
    ) -> None:
        self._enabled = enabled
        self._notify = notify
        self._load_favorite_icaos = load_favorite_icaos
        self._favorites: set[str] = set()
        self._active: set[str] = set()
        self._last_refresh_monotonic: float | None = None

    async def _refresh_favorites_if_stale(self) -> None:
        now = time.monotonic()
        if (
            self._last_refresh_monotonic is not None
            and now - self._last_refresh_monotonic < FAVORITES_REFRESH_INTERVAL_SECONDS
        ):
            return
        try:
            self._favorites = await self._load_favorite_icaos()
        except Exception:
            logger.exception("failed to refresh favorites list; keeping previous list")
        self._last_refresh_monotonic = now

    async def check(self, raw_aircraft: list[Any]) -> None:
        if not self._enabled:
            return
        await self._refresh_favorites_if_stale()
        if not self._favorites:
            self._active = set()
            return

        seen_now: set[str] = set()
        for raw in _iter_raw_entries(raw_aircraft):
            icao = raw["hex"]
            if icao not in self._favorites:
                continue
            seen_now.add(icao)
            if icao not in self._active:
                logger.info("favorite aircraft seen: icao=%s", icao)
                await self._notify(icao, _extract_callsign(raw))
        self._active = seen_now
