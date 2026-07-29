"""Read queries backing /api/receiver/* -- max reception range by compass
sector and altitude band, and message-count/position-rate over time.
Modeled on tracks.py's "one broad query + Python post-processing" shape
and traffic.py's zero-filled-bucket convention (every sector/band/bucket
is always present in the result, even with zero samples).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

from app.domain.bands import ALTITUDE_BANDS, band_case_sql

QUERY_TIMEOUT_SECONDS = 5.0
BEARING_SECTOR_COUNT = 16
SECTOR_WIDTH_DEG = 360.0 / BEARING_SECTOR_COUNT
# hours <= this use per-minute traffic_minute buckets (matches traffic.py);
# above it, per-hour buckets keep the response small (PLAN.md C-8's
# hours=168/1.18MB lesson).
HOURLY_BUCKET_THRESHOLD_HOURS = 24


@dataclass(frozen=True, slots=True)
class BearingRangeEntry:
    sector_index: int  # 0-15; sector covers [index*22.5, (index+1)*22.5) degrees
    sector_center_deg: float
    max_distance_km: float | None
    sample_count: int


@dataclass(frozen=True, slots=True)
class AltitudeBandRangeEntry:
    band_key: str
    max_distance_km: float | None
    sample_count: int


@dataclass(frozen=True, slots=True)
class ReceptionBucket:
    bucket_at: datetime
    message_count: int
    position_rate: float | None  # position_aircraft_count / active_aircraft_count


async def bearing_range(pool: asyncpg.Pool, hours: int) -> list[BearingRangeEntry]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        f"""
        SELECT
            ((width_bucket(bearing_deg, 0, 360, {BEARING_SECTOR_COUNT}) - 1)
                % {BEARING_SECTOR_COUNT}) AS sector_index,
            max(distance_km) AS max_distance_km,
            count(*) AS sample_count
        FROM observations
        WHERE observed_at >= $1 AND bearing_deg IS NOT NULL AND distance_km IS NOT NULL
        GROUP BY sector_index
        """,
        since,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    by_sector = {row["sector_index"]: row for row in rows}

    entries: list[BearingRangeEntry] = []
    for i in range(BEARING_SECTOR_COUNT):
        row = by_sector.get(i)
        entries.append(
            BearingRangeEntry(
                sector_index=i,
                sector_center_deg=i * SECTOR_WIDTH_DEG + SECTOR_WIDTH_DEG / 2,
                max_distance_km=row["max_distance_km"] if row else None,
                sample_count=row["sample_count"] if row else 0,
            )
        )
    return entries


async def altitude_band_range(pool: asyncpg.Pool, hours: int) -> list[AltitudeBandRangeEntry]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        f"""
        SELECT
            {band_case_sql("altitude_ft")} AS band_key,
            max(distance_km) AS max_distance_km,
            count(*) AS sample_count
        FROM observations
        WHERE observed_at >= $1 AND altitude_ft IS NOT NULL AND distance_km IS NOT NULL
        GROUP BY band_key
        """,
        since,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    by_band = {row["band_key"]: row for row in rows}

    entries: list[AltitudeBandRangeEntry] = []
    for band in ALTITUDE_BANDS:
        row = by_band.get(band.key)
        entries.append(
            AltitudeBandRangeEntry(
                band_key=band.key,
                max_distance_km=row["max_distance_km"] if row else None,
                sample_count=row["sample_count"] if row else 0,
            )
        )
    return entries


def _bucket_size(hours: int) -> timedelta:
    return timedelta(minutes=1) if hours <= HOURLY_BUCKET_THRESHOLD_HOURS else timedelta(hours=1)


async def reception_timeseries(pool: asyncpg.Pool, hours: int) -> list[ReceptionBucket]:
    end = datetime.now(UTC).replace(second=0, microsecond=0)
    start = end - timedelta(hours=hours)
    step = _bucket_size(hours)
    hourly = step == timedelta(hours=1)

    if hourly:
        rows = await pool.fetch(
            """
            SELECT
                date_trunc('hour', bucket_at) AS bucket_at,
                sum(active_aircraft_count) AS active_sum,
                sum(position_aircraft_count) AS position_sum,
                sum(message_count_delta) AS message_sum
            FROM traffic_minute
            WHERE bucket_at >= $1 AND bucket_at < $2
            GROUP BY 1
            """,
            start,
            end,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
    else:
        rows = await pool.fetch(
            "SELECT bucket_at, active_aircraft_count, position_aircraft_count, message_count_delta "
            "FROM traffic_minute WHERE bucket_at >= $1 AND bucket_at < $2",
            start,
            end,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
    by_bucket = {row["bucket_at"]: row for row in rows}

    cursor = start.replace(minute=0, second=0, microsecond=0) if hourly else start
    buckets: list[ReceptionBucket] = []
    while cursor < end:
        row = by_bucket.get(cursor)
        if hourly:
            message_count = row["message_sum"] if row else 0
            active_total = row["active_sum"] if row else 0
            position_total = row["position_sum"] if row else 0
        else:
            message_count = row["message_count_delta"] if row else 0
            active_total = row["active_aircraft_count"] if row else 0
            position_total = row["position_aircraft_count"] if row else 0
        position_rate = (position_total / active_total) if active_total else None
        buckets.append(ReceptionBucket(cursor, message_count, position_rate))
        cursor += step
    return buckets
