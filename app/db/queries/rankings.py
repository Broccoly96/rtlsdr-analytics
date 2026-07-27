"""Read queries backing /api/rankings.

Farthest/closest are computed per aircraft (not per raw observation), so a
single aircraft with many observations can't dominate the ranking: DISTINCT
ON (icao) keeps exactly one row per aircraft -- its most extreme distance in
the window -- before the outer ORDER BY/LIMIT picks the overall top N.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class RankingEntry:
    icao: str
    callsign: str | None
    distance_km: float
    bearing_deg: float | None
    altitude_ft: float | None
    observed_at: datetime


async def get_farthest(pool: asyncpg.Pool, hours: int, limit: int) -> list[RankingEntry]:
    return await _get_ranking(pool, hours, limit, descending=True)


async def get_closest(pool: asyncpg.Pool, hours: int, limit: int) -> list[RankingEntry]:
    return await _get_ranking(pool, hours, limit, descending=False)


async def _get_ranking(
    pool: asyncpg.Pool, hours: int, limit: int, *, descending: bool
) -> list[RankingEntry]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    order = "DESC" if descending else "ASC"  # internal literal, never user input
    rows = await pool.fetch(
        f"""
        SELECT icao, callsign, distance_km, bearing_deg, altitude_ft, observed_at
        FROM (
            SELECT DISTINCT ON (icao)
                icao, callsign, distance_km, bearing_deg, altitude_ft, observed_at
            FROM observations
            WHERE observed_at >= $1 AND distance_km IS NOT NULL
            ORDER BY icao, distance_km {order}
        ) per_aircraft
        ORDER BY distance_km {order}
        LIMIT $2
        """,
        since,
        limit,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [RankingEntry(**dict(row)) for row in rows]
