"""PostgresStore: a Store Protocol implementation backed by asyncpg.

Each of the four Protocol methods executes exactly one parameterized SQL
statement per call, relying on PostgreSQL's own per-statement atomicity --
no explicit transactions are used. This matches the collector's existing
resilience design (app/collector/service.py's _safe_store_call wraps each
Store call independently so one bad write never aborts a whole poll); a
poll-wide transaction would silently defeat that guarantee by rolling back
already-good writes alongside a single bad one.

DB-outage resilience needs no special handling here either: asyncpg's pool
raises on a broken connection rather than buffering, so a failed write is
simply dropped (by the caller's own catch-and-log wrapper) and the very next
call transparently reconnects once the database returns.
"""

from __future__ import annotations

from datetime import datetime

import asyncpg

from app.collector.aggregator import TrafficMinute
from app.collector.store import IngestionStatus
from app.db.pool import close_pool, create_pool
from app.domain.models import AircraftObservation

_UPSERT_AIRCRAFT_SQL = """
    INSERT INTO aircraft (icao, first_seen_at, last_seen_at, last_callsign)
    VALUES ($1, $2, $2, NULLIF($3, ''))
    ON CONFLICT (icao) DO UPDATE SET
        last_seen_at = EXCLUDED.last_seen_at,
        last_callsign = COALESCE(EXCLUDED.last_callsign, aircraft.last_callsign)
"""

_INSERT_OBSERVATION_SQL = """
    INSERT INTO observations (
        observed_at, icao, callsign, lat, lon, altitude_ft, ground_speed_kt,
        track_deg, vertical_rate_fpm, rssi, distance_km, bearing_deg, source_age_seconds
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
    ON CONFLICT (icao, observed_at) DO UPDATE SET
        callsign = EXCLUDED.callsign,
        lat = EXCLUDED.lat,
        lon = EXCLUDED.lon,
        altitude_ft = EXCLUDED.altitude_ft,
        ground_speed_kt = EXCLUDED.ground_speed_kt,
        track_deg = EXCLUDED.track_deg,
        vertical_rate_fpm = EXCLUDED.vertical_rate_fpm,
        rssi = EXCLUDED.rssi,
        distance_km = EXCLUDED.distance_km,
        bearing_deg = EXCLUDED.bearing_deg,
        source_age_seconds = EXCLUDED.source_age_seconds
"""

_UPSERT_TRAFFIC_MINUTE_SQL = """
    INSERT INTO traffic_minute (
        bucket_at, active_aircraft_count, position_aircraft_count, message_count_delta
    )
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (bucket_at) DO UPDATE SET
        active_aircraft_count = EXCLUDED.active_aircraft_count,
        position_aircraft_count = EXCLUDED.position_aircraft_count,
        message_count_delta = EXCLUDED.message_count_delta
"""

_INSERT_INGESTION_STATUS_SQL = """
    INSERT INTO ingestion_status (checked_at, success, latency_ms, aircraft_count, error_code)
    VALUES ($1, $2, $3, $4, $5)
"""


class PostgresStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, database_url: str) -> PostgresStore:
        return cls(await create_pool(database_url))

    async def close(self) -> None:
        await close_pool(self._pool)

    async def upsert_aircraft(self, icao: str, seen_at: datetime, callsign: str | None) -> None:
        await self._pool.execute(_UPSERT_AIRCRAFT_SQL, icao, seen_at, callsign or "")

    async def insert_observation(self, observation: AircraftObservation) -> None:
        await self._pool.execute(
            _INSERT_OBSERVATION_SQL,
            observation.observed_at,
            observation.icao,
            observation.callsign,
            observation.lat,
            observation.lon,
            observation.altitude_ft,
            observation.ground_speed_kt,
            observation.track_deg,
            observation.vertical_rate_fpm,
            observation.rssi,
            observation.distance_km,
            observation.bearing_deg,
            observation.source_age_seconds,
        )

    async def upsert_traffic_minute(self, minute: TrafficMinute) -> None:
        await self._pool.execute(
            _UPSERT_TRAFFIC_MINUTE_SQL,
            minute.bucket_at,
            minute.active_aircraft_count,
            minute.position_aircraft_count,
            minute.message_count_delta,
        )

    async def record_ingestion_status(self, status: IngestionStatus) -> None:
        await self._pool.execute(
            _INSERT_INGESTION_STATUS_SQL,
            status.checked_at,
            status.success,
            status.latency_ms,
            status.aircraft_count,
            status.error_code,
        )
