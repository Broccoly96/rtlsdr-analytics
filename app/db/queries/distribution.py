"""Read queries backing /api/distribution/* -- hour-of-day unique-aircraft
pattern and altitude/speed histograms. Histograms return only occupied
buckets (unlike traffic.py's zero-filled time buckets): there's no fixed
continuous domain to fill against, so a sparse result is the correct shape
for a client-side bar chart to plot directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class HourOfDayEntry:
    hour: int  # 0-23, UTC
    unique_aircraft_count: int


@dataclass(frozen=True, slots=True)
class HistogramBucket:
    bucket_start: float
    count: int


async def hour_of_day_unique(pool: asyncpg.Pool, days: int) -> list[HourOfDayEntry]:
    """Unique-ICAO count per UTC hour-of-day over a rolling `days`-day
    window. A statistical pattern view, not a calendar-day report, so a
    rolling now()-N-days window (no DISPLAY_TIMEZONE conversion) is enough."""
    since = datetime.now(UTC) - timedelta(days=days)
    rows = await pool.fetch(
        """
        SELECT extract(hour FROM observed_at)::int AS hour, count(DISTINCT icao) AS unique_count
        FROM observations
        WHERE observed_at >= $1
        GROUP BY hour
        """,
        since,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    by_hour = {row["hour"]: row["unique_count"] for row in rows}
    return [HourOfDayEntry(hour=h, unique_aircraft_count=by_hour.get(h, 0)) for h in range(24)]


async def altitude_histogram(
    pool: asyncpg.Pool, hours: int, bucket_ft: int = 1000
) -> list[HistogramBucket]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        """
        SELECT floor(altitude_ft / $2) * $2 AS bucket_start, count(*) AS bucket_count
        FROM observations
        WHERE observed_at >= $1 AND altitude_ft IS NOT NULL
        GROUP BY bucket_start
        ORDER BY bucket_start
        """,
        since,
        float(bucket_ft),
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [HistogramBucket(row["bucket_start"], row["bucket_count"]) for row in rows]


async def speed_histogram(
    pool: asyncpg.Pool, hours: int, bucket_kt: int = 50
) -> list[HistogramBucket]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        """
        SELECT floor(ground_speed_kt / $2) * $2 AS bucket_start, count(*) AS bucket_count
        FROM observations
        WHERE observed_at >= $1 AND ground_speed_kt IS NOT NULL
        GROUP BY bucket_start
        ORDER BY bucket_start
        """,
        since,
        float(bucket_kt),
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [HistogramBucket(row["bucket_start"], row["bucket_count"]) for row in rows]
