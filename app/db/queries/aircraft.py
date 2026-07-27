"""Read queries backing /api/aircraft/recent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class RecentAircraft:
    icao: str
    callsign: str | None
    first_seen_at: datetime
    last_seen_at: datetime


async def get_recent_aircraft(
    pool: asyncpg.Pool, hours: int, limit: int, offset: int
) -> list[RecentAircraft]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        "SELECT icao, last_callsign AS callsign, first_seen_at, last_seen_at "
        "FROM aircraft WHERE last_seen_at >= $1 ORDER BY last_seen_at DESC LIMIT $2 OFFSET $3",
        since,
        limit,
        offset,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [RecentAircraft(**dict(row)) for row in rows]
