from __future__ import annotations

from datetime import datetime

import asyncpg
import pytest

from app.collector.aggregator import TrafficMinute
from app.collector.store import IngestionStatus
from app.db.postgres_store import PostgresStore
from app.domain.models import AircraftObservation, ReceptionState
from tests.contract.store_contract import CONTRACT_CHECKS, T0, AircraftRow, _observation


class PostgresStoreReader:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get_aircraft(self, icao: str) -> AircraftRow | None:
        row = await self._conn.fetchrow(
            "SELECT icao, first_seen_at, last_seen_at, last_callsign FROM aircraft WHERE icao = $1",
            icao,
        )
        return AircraftRow(**dict(row)) if row else None

    async def count_observations(self) -> int:
        return await self._conn.fetchval("SELECT count(*) FROM observations")

    async def get_observation(self, icao: str, observed_at: datetime) -> AircraftObservation | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM observations WHERE icao = $1 AND observed_at = $2", icao, observed_at
        )
        if row is None:
            return None
        data = dict(row)
        data.pop("id")
        return AircraftObservation(reception_state=ReceptionState.POSITION_ACQUIRED, **data)

    async def get_traffic_minute(self, bucket_at: datetime) -> TrafficMinute | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM traffic_minute WHERE bucket_at = $1", bucket_at
        )
        return TrafficMinute(**dict(row)) if row else None

    async def list_ingestion_status(self) -> list[IngestionStatus]:
        rows = await self._conn.fetch(
            "SELECT checked_at, success, latency_ms, aircraft_count, error_code "
            "FROM ingestion_status ORDER BY id"
        )
        return [IngestionStatus(**dict(row)) for row in rows]


@pytest.fixture
async def store(postgres_url, clean_db):
    instance = await PostgresStore.connect(postgres_url)
    yield instance
    await instance.close()


@pytest.fixture
async def reader(postgres_url, clean_db):
    conn = await asyncpg.connect(postgres_url)
    yield PostgresStoreReader(conn)
    await conn.close()


@pytest.mark.parametrize("check", CONTRACT_CHECKS, ids=lambda f: f.__name__)
async def test_contract(check, store, reader) -> None:
    await check(store, reader)


async def test_earlier_write_survives_a_later_failing_write(postgres_url, clean_db) -> None:
    """Postgres-only: each Store method is its own atomic statement (see
    app/db/postgres_store.py's module docstring), so a later call that
    violates a CHECK constraint must not undo an earlier, already-committed
    write from the same poll. InMemoryStore performs no validation at all,
    so there is no equivalent failure mode to trigger there -- this
    guarantee is Postgres-specific by construction."""
    store = await PostgresStore.connect(postgres_url)
    conn = await asyncpg.connect(postgres_url)
    try:
        await store.upsert_aircraft("aaaaaa", T0, "TEST001")
        with pytest.raises(asyncpg.PostgresError):
            await store.insert_observation(_observation(bearing_deg=999.0))  # violates CHECK
        row = await conn.fetchrow("SELECT * FROM aircraft WHERE icao = 'aaaaaa'")
        assert row is not None
        assert row["last_callsign"] == "TEST001"
    finally:
        await conn.close()
        await store.close()


async def test_close_then_use_fails(postgres_url, clean_db) -> None:
    """Postgres-only: close() actually releases the pool's connections --
    InMemoryStore holds no OS-level resource to make an equivalent
    assertion meaningful for."""
    store = await PostgresStore.connect(postgres_url)
    await store.close()
    with pytest.raises(asyncpg.InterfaceError):
        await store.upsert_aircraft("aaaaaa", T0, "TEST001")
