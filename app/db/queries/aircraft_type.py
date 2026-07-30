"""Read query backing GET /api/distribution/aircraft-type -- top aircraft
types (by distinct-aircraft count) observed on a given calendar day.

Always computed live from `observations` (not `aircraft_day`): unlike the
traffic-summary tables, `aircraft_type_cache` isn't day-scoped -- it's a
static per-icao lookup -- so there's no separate "past day" precomputed
path needed, the same query works for today or any day still within
RAW_RETENTION_DAYS. Aircraft with no cached type yet (or a failed lookup)
are excluded, not shown as an "unknown" bucket -- see
app/aircraft_lookup.py for how/when the cache is populated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class AircraftTypeCount:
    type_code: str
    type_name: str | None
    aircraft_count: int


async def top_aircraft_types(
    pool: asyncpg.Pool, start_utc: datetime, end_utc: datetime, limit: int
) -> list[AircraftTypeCount]:
    rows = await pool.fetch(
        """
        SELECT
            c.type_code,
            max(c.type_name) AS type_name,
            count(DISTINCT o.icao) AS aircraft_count
        FROM observations o
        JOIN aircraft_type_cache c ON c.icao = o.icao
        WHERE o.observed_at >= $1 AND o.observed_at < $2
          AND c.type_code IS NOT NULL
        GROUP BY c.type_code
        ORDER BY aircraft_count DESC, c.type_code
        LIMIT $3
        """,
        start_utc,
        end_utc,
        limit,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [
        AircraftTypeCount(row["type_code"], row["type_name"], row["aircraft_count"]) for row in rows
    ]
