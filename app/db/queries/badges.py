"""Read query backing GET /api/badges -- computes BadgeStats (app/domain/
badges.py) fresh from the permanent tables on every call. Six small scalar
queries rather than one large join: this app's data volume is small
(personal, single-receiver) and these run rarely (one page view), so
clarity wins over shaving round trips.
"""

from __future__ import annotations

import asyncpg

from app.domain.badges import BadgeStats

QUERY_TIMEOUT_SECONDS = 5.0


async def get_badge_stats(pool: asyncpg.Pool) -> BadgeStats:
    total_aircraft = await pool.fetchval(
        "SELECT count(*) FROM aircraft", timeout=QUERY_TIMEOUT_SECONDS
    )
    total_types = await pool.fetchval(
        "SELECT count(DISTINCT type_code) FROM aircraft_type_cache "
        "WHERE lookup_failed = false AND type_code IS NOT NULL",
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    max_farthest_km = await pool.fetchval(
        "SELECT max(farthest_distance_km) FROM traffic_day", timeout=QUERY_TIMEOUT_SECONDS
    )
    max_total_pass_count = await pool.fetchval(
        "SELECT max(total) FROM (SELECT sum(pass_count) AS total FROM aircraft_day "
        "GROUP BY icao) sub",
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    max_distinct_callsigns = await pool.fetchval(
        "SELECT max(cnt) FROM (SELECT count(*) AS cnt FROM aircraft_callsign_history "
        "GROUP BY icao) sub",
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    favorites_count = await pool.fetchval(
        "SELECT count(*) FROM favorites", timeout=QUERY_TIMEOUT_SECONDS
    )
    days_running = await pool.fetchval(
        "SELECT count(*) FROM traffic_day", timeout=QUERY_TIMEOUT_SECONDS
    )
    max_concurrent_ever = await pool.fetchval(
        "SELECT max(max_concurrent_count) FROM traffic_day", timeout=QUERY_TIMEOUT_SECONDS
    )

    return BadgeStats(
        total_aircraft=total_aircraft or 0,
        total_types=total_types or 0,
        max_farthest_km=max_farthest_km,
        max_total_pass_count=max_total_pass_count,
        max_distinct_callsigns=max_distinct_callsigns,
        favorites_count=favorites_count or 0,
        days_running=days_running or 0,
        max_concurrent_ever=max_concurrent_ever,
    )
