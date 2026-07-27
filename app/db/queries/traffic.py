"""Read queries backing /api/traffic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class TrafficBucket:
    bucket_at: datetime
    active_aircraft_count: int
    position_aircraft_count: int
    message_count_delta: int


async def get_traffic(pool: asyncpg.Pool, hours: int) -> tuple[list[TrafficBucket], int]:
    """Returns (minute buckets covering [now-hours, now) with gaps filled as
    explicit zero-valued buckets, total distinct aircraft observed in the
    window)."""
    end = datetime.now(UTC).replace(second=0, microsecond=0)
    start = end - timedelta(hours=hours)

    rows = await pool.fetch(
        "SELECT bucket_at, active_aircraft_count, position_aircraft_count, message_count_delta "
        "FROM traffic_minute WHERE bucket_at >= $1 AND bucket_at < $2 ORDER BY bucket_at",
        start,
        end,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    by_bucket = {row["bucket_at"]: row for row in rows}

    buckets: list[TrafficBucket] = []
    cursor = start
    while cursor < end:
        row = by_bucket.get(cursor)
        if row is None:
            buckets.append(TrafficBucket(cursor, 0, 0, 0))
        else:
            buckets.append(
                TrafficBucket(
                    cursor,
                    row["active_aircraft_count"],
                    row["position_aircraft_count"],
                    row["message_count_delta"],
                )
            )
        cursor += timedelta(minutes=1)

    unique_count = await pool.fetchval(
        "SELECT count(DISTINCT icao) FROM observations "
        "WHERE observed_at >= $1 AND observed_at < $2",
        start,
        end,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return buckets, unique_count
