"""Read queries backing /api/receiver/* -- max reception range by compass
sector and altitude band, and message-count/position-rate over time.
Modeled on tracks.py's "one broad query + Python post-processing" shape
and traffic.py's zero-filled-bucket convention (every sector/band/bucket
is always present in the result, even with zero samples).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

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


@dataclass(frozen=True, slots=True)
class RssiDistanceCell:
    distance_bucket_km: float
    rssi_bucket_db: float
    count: int


DEFAULT_DISTANCE_BUCKET_KM = 20.0
DEFAULT_RSSI_BUCKET_DB = 5.0
DAY_START_HOUR = 6
DAY_END_HOUR = 18  # local hour range [6, 18) counts as "day", else "night"


@dataclass(frozen=True, slots=True)
class DayNightRange:
    day_max_distance_km: float | None
    day_sample_count: int
    night_max_distance_km: float | None
    night_sample_count: int


@dataclass(frozen=True, slots=True)
class WeeklyTrendEntry:
    week_start: date
    message_count_total: int
    max_concurrent_count: int
    unique_aircraft_count: int


DEFAULT_DOME_ALTITUDE_BUCKET_FT = 2000.0
# 16 sectors x ~19 distance buckets (364km max / 20km) x ~24 altitude buckets
# (47,000ft max / 2000ft) is a worst-case ~7,300 cells; the result is sparse
# (occupied cells only, see reception_dome()'s docstring) so this is rarely
# reached today, but caps it defensively as RAW_RETENTION_DAYS fills toward
# 30 days of raw observations.
DOME_MAX_CELLS = 5000


@dataclass(frozen=True, slots=True)
class ReceptionDomeCell:
    sector_index: int
    sector_center_deg: float
    distance_bucket_km: float
    altitude_bucket_ft: float
    avg_rssi: float
    count: int


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


async def rssi_by_distance(
    pool: asyncpg.Pool,
    hours: int,
    distance_bucket_km: float = DEFAULT_DISTANCE_BUCKET_KM,
    rssi_bucket_db: float = DEFAULT_RSSI_BUCKET_DB,
) -> list[RssiDistanceCell]:
    """Sparse (distance, RSSI) bucket counts -- like distribution.py's
    histograms, only occupied cells are returned rather than zero-filling a
    fixed grid, since a client-side heatmap plots a sparse cell list fine."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        """
        SELECT
            floor(distance_km / $2) * $2 AS distance_bucket,
            floor(rssi / $3) * $3 AS rssi_bucket,
            count(*) AS cell_count
        FROM observations
        WHERE observed_at >= $1 AND distance_km IS NOT NULL AND rssi IS NOT NULL
        GROUP BY distance_bucket, rssi_bucket
        ORDER BY distance_bucket, rssi_bucket
        """,
        since,
        distance_bucket_km,
        rssi_bucket_db,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [
        RssiDistanceCell(row["distance_bucket"], row["rssi_bucket"], row["cell_count"])
        for row in rows
    ]


async def reception_dome(
    pool: asyncpg.Pool,
    hours: int,
    distance_bucket_km: float = DEFAULT_DISTANCE_BUCKET_KM,
    altitude_bucket_ft: float = DEFAULT_DOME_ALTITUDE_BUCKET_FT,
) -> list[ReceptionDomeCell]:
    """Sparse (bearing sector, distance, altitude) bucket cells with average
    RSSI and observation count -- the 3D generalization of rssi_by_distance's
    2D (distance, RSSI) bucketing above, reusing BEARING_SECTOR_COUNT/
    SECTOR_WIDTH_DEG from bearing_range so both charts agree on sector
    boundaries. A fixed altitude step (not ALTITUDE_BANDS' 5 coarse bands)
    is used deliberately: 5 bands would collapse the vertical axis to 5 flat
    shells rather than a continuous point cloud.

    Capped at DOME_MAX_CELLS (ORDER BY count DESC LIMIT, then re-sorted for a
    deterministic response body) -- at the cap boundary, denser cells win,
    same bias as the dashboard heatmap's own grid cap.
    """
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        f"""
        SELECT
            ((width_bucket(bearing_deg, 0, 360, {BEARING_SECTOR_COUNT}) - 1)
                % {BEARING_SECTOR_COUNT}) AS sector_index,
            floor(distance_km / $2) * $2 AS distance_bucket,
            floor(altitude_ft / $3) * $3 AS altitude_bucket,
            avg(rssi) AS avg_rssi,
            count(*) AS cell_count
        FROM observations
        WHERE observed_at >= $1
          AND bearing_deg IS NOT NULL AND distance_km IS NOT NULL
          AND altitude_ft IS NOT NULL AND rssi IS NOT NULL
        GROUP BY sector_index, distance_bucket, altitude_bucket
        ORDER BY cell_count DESC
        LIMIT {DOME_MAX_CELLS}
        """,
        since,
        distance_bucket_km,
        altitude_bucket_ft,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    cells = [
        ReceptionDomeCell(
            sector_index=row["sector_index"],
            sector_center_deg=row["sector_index"] * SECTOR_WIDTH_DEG + SECTOR_WIDTH_DEG / 2,
            distance_bucket_km=row["distance_bucket"],
            altitude_bucket_ft=row["altitude_bucket"],
            avg_rssi=row["avg_rssi"],
            count=row["cell_count"],
        )
        for row in rows
    ]
    cells.sort(key=lambda c: (c.sector_index, c.distance_bucket_km, c.altitude_bucket_ft))
    return cells


async def day_night_range(pool: asyncpg.Pool, hours: int, tz_name: str) -> DayNightRange:
    """Max reception distance split into "day" ([DAY_START_HOUR,
    DAY_END_HOUR) local time) vs. "night" (everything else) -- a rough
    day/night comparison, not a sunrise/sunset-precise one. Scans
    `observations` like bearing_range/altitude_band_range above, so it's
    bounded by RAW_RETENTION_DAYS the same way."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    row = await pool.fetchrow(
        """
        SELECT
            max(distance_km) FILTER (
                WHERE extract(hour FROM observed_at AT TIME ZONE $2) >= $3
                  AND extract(hour FROM observed_at AT TIME ZONE $2) < $4
            ) AS day_max_distance_km,
            count(*) FILTER (
                WHERE extract(hour FROM observed_at AT TIME ZONE $2) >= $3
                  AND extract(hour FROM observed_at AT TIME ZONE $2) < $4
            ) AS day_sample_count,
            max(distance_km) FILTER (
                WHERE extract(hour FROM observed_at AT TIME ZONE $2) < $3
                   OR extract(hour FROM observed_at AT TIME ZONE $2) >= $4
            ) AS night_max_distance_km,
            count(*) FILTER (
                WHERE extract(hour FROM observed_at AT TIME ZONE $2) < $3
                   OR extract(hour FROM observed_at AT TIME ZONE $2) >= $4
            ) AS night_sample_count
        FROM observations
        WHERE observed_at >= $1 AND distance_km IS NOT NULL
        """,
        since,
        tz_name,
        DAY_START_HOUR,
        DAY_END_HOUR,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return DayNightRange(
        day_max_distance_km=row["day_max_distance_km"],
        day_sample_count=row["day_sample_count"] or 0,
        night_max_distance_km=row["night_max_distance_km"],
        night_sample_count=row["night_sample_count"] or 0,
    )


async def weekly_trend(pool: asyncpg.Pool, weeks: int) -> list[WeeklyTrendEntry]:
    """Weekly trend over `traffic_day`/`aircraft_day` (kept long-term), not
    raw `observations` -- same reasoning as period.py's monthly/yearly
    rollups. `unique_aircraft_count` comes from `aircraft_day` (true
    distinct count per week) rather than summing `traffic_day`'s daily
    counts, which would double-count repeat visitors within a week."""
    since_day = date.today() - timedelta(weeks=weeks)
    traffic_rows = await pool.fetch(
        """
        SELECT date_trunc('week', day)::date AS week_start,
               coalesce(sum(message_count_total), 0) AS message_count_total,
               coalesce(max(max_concurrent_count), 0) AS max_concurrent_count
        FROM traffic_day WHERE day >= $1
        GROUP BY week_start ORDER BY week_start
        """,
        since_day,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    unique_rows = await pool.fetch(
        """
        SELECT date_trunc('week', day)::date AS week_start,
               count(DISTINCT icao) AS unique_aircraft_count
        FROM aircraft_day WHERE day >= $1
        GROUP BY week_start
        """,
        since_day,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    unique_by_week = {r["week_start"]: r["unique_aircraft_count"] for r in unique_rows}
    return [
        WeeklyTrendEntry(
            week_start=r["week_start"],
            message_count_total=r["message_count_total"],
            max_concurrent_count=r["max_concurrent_count"],
            unique_aircraft_count=unique_by_week.get(r["week_start"], 0),
        )
        for r in traffic_rows
    ]
