"""Read queries backing /api/aircraft/{icao}/history and
/api/aircraft/frequent -- per-aircraft summary/callsign history from the
daily rollup tables (Milestone L: aircraft_day, aircraft_callsign_history),
and a "most frequently seen in the last N days" ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class LatestObservation:
    observed_at: datetime
    lat: float | None
    lon: float | None
    altitude_ft: float | None
    ground_speed_kt: float | None
    track_deg: float | None
    vertical_rate_fpm: float | None
    rssi: float | None
    distance_km: float | None
    bearing_deg: float | None


@dataclass(frozen=True, slots=True)
class AircraftSummary:
    icao: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_callsign: str | None
    days_observed: int
    total_pass_count: int
    total_observation_count: int


@dataclass(frozen=True, slots=True)
class CallsignHistoryEntry:
    callsign: str
    first_seen_at: datetime
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class FrequentAircraftEntry:
    icao: str
    last_callsign: str | None
    days_observed: int
    total_pass_count: int


async def aircraft_summary(pool: asyncpg.Pool, icao: str) -> AircraftSummary | None:
    aircraft_row = await pool.fetchrow(
        "SELECT icao, first_seen_at, last_seen_at, last_callsign FROM aircraft WHERE icao = $1",
        icao,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    if aircraft_row is None:
        return None

    agg_row = await pool.fetchrow(
        """
        SELECT
            count(*) AS days_observed,
            coalesce(sum(pass_count), 0) AS total_pass_count,
            coalesce(sum(observation_count), 0) AS total_observation_count
        FROM aircraft_day WHERE icao = $1
        """,
        icao,
        timeout=QUERY_TIMEOUT_SECONDS,
    )

    return AircraftSummary(
        icao=aircraft_row["icao"],
        first_seen_at=aircraft_row["first_seen_at"],
        last_seen_at=aircraft_row["last_seen_at"],
        last_callsign=aircraft_row["last_callsign"],
        days_observed=agg_row["days_observed"],
        total_pass_count=agg_row["total_pass_count"],
        total_observation_count=agg_row["total_observation_count"],
    )


async def latest_observation(pool: asyncpg.Pool, icao: str) -> LatestObservation | None:
    """Our own most recent stored observation for one aircraft -- backs
    the aircraft-detail sidebar's instant, DB-backed section (as opposed
    to the live readsb pass-through in app/api/routers/aircraft_live.py,
    which is fresher but not persisted). None if retention has already
    pruned every observation for this aircraft."""
    row = await pool.fetchrow(
        """
        SELECT observed_at, lat, lon, altitude_ft, ground_speed_kt, track_deg,
               vertical_rate_fpm, rssi, distance_km, bearing_deg
        FROM observations
        WHERE icao = $1
        ORDER BY observed_at DESC
        LIMIT 1
        """,
        icao,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return LatestObservation(**dict(row)) if row else None


async def callsign_history(pool: asyncpg.Pool, icao: str) -> list[CallsignHistoryEntry]:
    rows = await pool.fetch(
        """
        SELECT callsign, first_seen_at, last_seen_at
        FROM aircraft_callsign_history
        WHERE icao = $1
        ORDER BY last_seen_at DESC
        """,
        icao,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [CallsignHistoryEntry(**dict(row)) for row in rows]


async def most_frequent(pool: asyncpg.Pool, days: int, limit: int) -> list[FrequentAircraftEntry]:
    # A statistical ranking, not a calendar-day report -- a UTC-date-based
    # rolling window is precise enough (same precedent as
    # distribution.py's hour_of_day_unique), avoiding a DISPLAY_TIMEZONE
    # dependency in the query layer.
    since_day = (datetime.now(UTC) - timedelta(days=days)).date()
    rows = await pool.fetch(
        """
        SELECT
            ad.icao,
            a.last_callsign,
            count(*) AS days_observed,
            coalesce(sum(ad.pass_count), 0) AS total_pass_count
        FROM aircraft_day ad
        JOIN aircraft a ON a.icao = ad.icao
        WHERE ad.day >= $1
        GROUP BY ad.icao, a.last_callsign
        ORDER BY days_observed DESC, total_pass_count DESC
        LIMIT $2
        """,
        since_day,
        limit,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [FrequentAircraftEntry(**dict(row)) for row in rows]
