"""Read/aggregation queries for calendar-day traffic summaries.

`compute_daily_summary` is the shared aggregation logic called from both
the write path (app/dailyrollup.py, for a finished past day) and the read
path (Milestone N's "today", which isn't rolled up into `traffic_day`
yet) -- same pool-taking, dataclass-returning shape as every other query
module in this package.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class DailyTrafficSummary:
    day: date
    unique_aircraft_count: int
    max_concurrent_count: int
    message_count_total: int
    position_aircraft_count_max: int
    farthest_icao: str | None
    farthest_distance_km: float | None
    closest_icao: str | None
    closest_distance_km: float | None
    most_observed_icao: str | None
    most_observed_count: int | None


async def compute_daily_summary(
    pool: asyncpg.Pool, day: date, start_utc: datetime, end_utc: datetime
) -> DailyTrafficSummary:
    unique_count = await pool.fetchval(
        "SELECT count(DISTINCT icao) FROM observations "
        "WHERE observed_at >= $1 AND observed_at < $2",
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    minute_row = await pool.fetchrow(
        """
        SELECT
            coalesce(max(active_aircraft_count), 0) AS max_concurrent,
            coalesce(sum(message_count_delta), 0) AS message_total,
            coalesce(max(position_aircraft_count), 0) AS position_max
        FROM traffic_minute
        WHERE bucket_at >= $1 AND bucket_at < $2
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    # Same ORDER BY distance_km {ASC,DESC} LIMIT shape rankings.py already
    # uses successfully against ix_observations_distance_observed_at.
    farthest = await pool.fetchrow(
        """
        SELECT icao, distance_km FROM observations
        WHERE observed_at >= $1 AND observed_at < $2 AND distance_km IS NOT NULL
        ORDER BY distance_km DESC LIMIT 1
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    closest = await pool.fetchrow(
        """
        SELECT icao, distance_km FROM observations
        WHERE observed_at >= $1 AND observed_at < $2 AND distance_km IS NOT NULL
        ORDER BY distance_km ASC LIMIT 1
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    most_observed = await pool.fetchrow(
        """
        SELECT icao, count(*) AS observation_count FROM observations
        WHERE observed_at >= $1 AND observed_at < $2
        GROUP BY icao ORDER BY observation_count DESC LIMIT 1
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return DailyTrafficSummary(
        day=day,
        unique_aircraft_count=unique_count,
        max_concurrent_count=minute_row["max_concurrent"],
        message_count_total=minute_row["message_total"],
        position_aircraft_count_max=minute_row["position_max"],
        farthest_icao=farthest["icao"] if farthest else None,
        farthest_distance_km=farthest["distance_km"] if farthest else None,
        closest_icao=closest["icao"] if closest else None,
        closest_distance_km=closest["distance_km"] if closest else None,
        most_observed_icao=most_observed["icao"] if most_observed else None,
        most_observed_count=most_observed["observation_count"] if most_observed else None,
    )


_TRAFFIC_DAY_COLUMNS = """
    day, unique_aircraft_count, max_concurrent_count, message_count_total,
    position_aircraft_count_max, farthest_icao, farthest_distance_km,
    closest_icao, closest_distance_km, most_observed_icao, most_observed_count
"""


async def get_traffic_day(pool: asyncpg.Pool, day: date) -> DailyTrafficSummary | None:
    row = await pool.fetchrow(
        f"SELECT {_TRAFFIC_DAY_COLUMNS} FROM traffic_day WHERE day = $1",
        day,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return DailyTrafficSummary(**dict(row)) if row else None


def _zero_summary(day: date) -> DailyTrafficSummary:
    return DailyTrafficSummary(
        day=day,
        unique_aircraft_count=0,
        max_concurrent_count=0,
        message_count_total=0,
        position_aircraft_count_max=0,
        farthest_icao=None,
        farthest_distance_km=None,
        closest_icao=None,
        closest_distance_km=None,
        most_observed_icao=None,
        most_observed_count=None,
    )


async def list_traffic_days(
    pool: asyncpg.Pool, start_day: date, end_day: date
) -> list[DailyTrafficSummary]:
    """[start_day, end_day] inclusive, zero-filled for days with no
    persisted rollup row yet (matches traffic.py's zero-filled-bucket
    convention)."""
    rows = await pool.fetch(
        f"SELECT {_TRAFFIC_DAY_COLUMNS} FROM traffic_day WHERE day >= $1 AND day <= $2",
        start_day,
        end_day,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    by_day = {row["day"]: row for row in rows}

    summaries: list[DailyTrafficSummary] = []
    cursor = start_day
    while cursor <= end_day:
        row = by_day.get(cursor)
        summaries.append(DailyTrafficSummary(**dict(row)) if row else _zero_summary(cursor))
        cursor += timedelta(days=1)
    return summaries
