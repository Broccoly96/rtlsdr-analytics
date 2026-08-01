"""Drives CollectorService.poll_once() against a real PostgresStore, reusing
the same httpx.MockTransport + fixture pattern as
tests/integration/test_collector_service.py -- the only thing that changes
is swapping InMemoryStore for a real, ephemeral, migrated PostgreSQL
instance (tests/contract/pg_container.py). Never touches compose.yaml's
adsb-db, and never a live network call.
"""

from __future__ import annotations

import asyncpg
import httpx
import pytest

from app.collector.service import CollectorService
from app.db.postgres_store import PostgresStore

SAMPLE_PAYLOAD = {
    "now": 1700000000.0,
    "messages": 1000,
    "aircraft": [
        {
            "hex": "aaaaaa",
            "flight": "TEST001",
            "seen": 0.5,
            "seen_pos": 0.5,
            "lat": 35.0,
            "lon": 139.0,
            "alt_baro": 1000,
        }
    ],
}


def _client_with_response(response: httpx.Response) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return response

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://readsb.test")


@pytest.fixture
async def postgres_store(postgres_url, clean_db):
    store = await PostgresStore.connect(postgres_url)
    yield store
    await store.close()


async def test_poll_once_persists_fixture_data_into_real_postgres(
    postgres_url, clean_db, postgres_store
):
    client = _client_with_response(httpx.Response(200, json=SAMPLE_PAYLOAD))
    service = CollectorService(
        client=client,
        url="/aircraft.json",
        store=postgres_store,
        receiver_lat=35.0,
        receiver_lon=139.0,
        poll_interval_seconds=5.0,
        track_sample_seconds=30.0,
    )

    interval = await service.poll_once()
    await client.aclose()

    assert interval == 5.0

    conn = await asyncpg.connect(postgres_url)
    try:
        aircraft_count = await conn.fetchval("SELECT count(*) FROM aircraft WHERE icao = 'aaaaaa'")
        observation_count = await conn.fetchval(
            "SELECT count(*) FROM observations WHERE icao = 'aaaaaa'"
        )
        status_row = await conn.fetchrow(
            "SELECT success, aircraft_count FROM ingestion_status ORDER BY id DESC LIMIT 1"
        )
    finally:
        await conn.close()

    assert aircraft_count == 1
    assert observation_count == 1
    assert status_row["success"] is True
    assert status_row["aircraft_count"] == 1


async def test_get_favorite_icaos_reads_real_favorites_table(
    postgres_url, clean_db, postgres_store
):
    conn = await asyncpg.connect(postgres_url)
    try:
        await conn.execute(
            "INSERT INTO aircraft (icao, first_seen_at, last_seen_at) VALUES ($1, now(), now())",
            "aaaaaa",
        )
        await conn.execute("INSERT INTO favorites (icao) VALUES ($1)", "aaaaaa")
    finally:
        await conn.close()

    assert await postgres_store.get_favorite_icaos() == {"aaaaaa"}


async def test_favorite_seen_notification_fires_against_real_postgres(
    postgres_url, clean_db, postgres_store
):
    conn = await asyncpg.connect(postgres_url)
    try:
        await conn.execute(
            "INSERT INTO aircraft (icao, first_seen_at, last_seen_at) VALUES ($1, now(), now())",
            "aaaaaa",
        )
        await conn.execute("INSERT INTO favorites (icao) VALUES ($1)", "aaaaaa")
    finally:
        await conn.close()

    calls = []

    async def notify(icao, callsign):
        calls.append((icao, callsign))

    client = _client_with_response(httpx.Response(200, json=SAMPLE_PAYLOAD))
    service = CollectorService(
        client=client,
        url="/aircraft.json",
        store=postgres_store,
        receiver_lat=35.0,
        receiver_lon=139.0,
        poll_interval_seconds=5.0,
        track_sample_seconds=30.0,
        favorite_seen_enabled=True,
        notify_favorite_seen=notify,
    )

    await service.poll_once()
    await client.aclose()

    assert calls == [("aaaaaa", "TEST001")]
