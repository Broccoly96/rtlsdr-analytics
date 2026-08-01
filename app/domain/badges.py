"""Badge catalog for Milestone MM's "achievements" feature.

Every badge is a pure function of BadgeStats (app/db/queries/badges.py) --
GET /api/badges recomputes earned/locked from scratch on every call rather
than storing a "you earned this on <date>" record anywhere (see that
router's docstring for why: it keeps the read-only/GET-only API invariant,
matching CLAUDE.md's stance that favorites' mutating endpoints are a
narrow, deliberate exception, not a precedent to extend casually).

Every badge below is deliberately scoped to data that's kept *permanently*
(`aircraft`, `aircraft_day`, `aircraft_callsign_history`, `traffic_day`,
`aircraft_type_cache`, `favorites`) rather than raw `observations` (purged
after RAW_RETENTION_DAYS) -- an "achievement" that could silently un-earn
itself after 30 days would be a correctness bug, not a quirky feature.
That ruled out anything requiring per-observation timing (e.g. a
"deep-night observer" badge), not just an oversight.

Thresholds are deliberately round numbers, not derived from any formula --
this is a gamification feature, not a measurement; tune freely.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BadgeStats:
    """Raw counters app/db/queries/badges.py computes from the permanent
    tables; badges.py's BADGES catalog is a pure function of this."""

    total_aircraft: int
    total_types: int
    max_farthest_km: float | None
    max_total_pass_count: int | None
    max_distinct_callsigns: int | None
    favorites_count: int
    days_running: int
    max_concurrent_ever: int | None


@dataclass(frozen=True, slots=True)
class Badge:
    key: str
    icon: str  # single emoji, rendered client-side -- no image asset
    is_earned: Callable[[BadgeStats], bool]
    # Value shown alongside the badge once earned (e.g. "1234機"), None if
    # the badge has no natural single number to show.
    progress: Callable[[BadgeStats], int | None] = lambda stats: None  # noqa: E731


BADGES: tuple[Badge, ...] = (
    Badge("first_contact", "🛫", lambda s: s.total_aircraft >= 1, lambda s: s.total_aircraft),
    Badge("aircraft_100", "✈️", lambda s: s.total_aircraft >= 100, lambda s: s.total_aircraft),
    Badge("aircraft_500", "🛩️", lambda s: s.total_aircraft >= 500, lambda s: s.total_aircraft),
    Badge("aircraft_1000", "🌐", lambda s: s.total_aircraft >= 1000, lambda s: s.total_aircraft),
    Badge("types_10", "🔎", lambda s: s.total_types >= 10, lambda s: s.total_types),
    Badge("types_50", "📚", lambda s: s.total_types >= 50, lambda s: s.total_types),
    Badge("types_100", "🏆", lambda s: s.total_types >= 100, lambda s: s.total_types),
    Badge(
        "far_catch",
        "📡",
        lambda s: s.max_farthest_km is not None and s.max_farthest_km >= 300,
        lambda s: int(s.max_farthest_km) if s.max_farthest_km is not None else None,
    ),
    Badge(
        "frequent_flyer",
        "🔁",
        lambda s: s.max_total_pass_count is not None and s.max_total_pass_count >= 50,
        lambda s: s.max_total_pass_count,
    ),
    Badge(
        "callsign_collector",
        "🏷️",
        lambda s: s.max_distinct_callsigns is not None and s.max_distinct_callsigns >= 5,
        lambda s: s.max_distinct_callsigns,
    ),
    Badge(
        "favorite_collector",
        "⭐",
        lambda s: s.favorites_count >= 5,
        lambda s: s.favorites_count,
    ),
    Badge("veteran_month", "📅", lambda s: s.days_running >= 30, lambda s: s.days_running),
    Badge("veteran_year", "🗓️", lambda s: s.days_running >= 365, lambda s: s.days_running),
    Badge(
        "busy_sky",
        "🚦",
        lambda s: s.max_concurrent_ever is not None and s.max_concurrent_ever >= 20,
        lambda s: s.max_concurrent_ever,
    ),
)
