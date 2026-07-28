"""Full-pipeline test: empty DB -> migration -> collector polls a fixture
readsb response -> API reads the same real, ephemeral PostgreSQL instance
and returns it (PLAN.md Milestone F-4).

Other integration tests already cover collector->Postgres
(test_collector_service_postgres.py) and API->Postgres
(test_api.py) individually, each asserting via direct SQL or seeded rows.
This test is the one place that drives both halves back to back against the
*same* database and asserts through the real FastAPI app, so a mismatch
between what the collector writes and what the API's read queries expect
would actually be caught. `postgres_url` (tests/contract/pg_container.py)
is a disposable container migrated with the real Alembic migration -- never
compose.yaml's adsb-db, and never the production readsb service.
"""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import create_app
from app.collector.service import CollectorService
from app.config import Settings
from app.db.postgres_store import PostgresStore

FIXTURE_PAYLOAD = {
    "now": 1700000000.0,
    "messages": 500,
    "aircraft": [
        {
            "hex": "abcdef",
            "flight": "E2E001",
            "seen": 0.5,
            "seen_pos": 0.5,
            "lat": 35.5,
            "lon": 139.5,
            "alt_baro": 15000,
            "gs": 350.0,
            "track": 90.0,
        },
        {
            "hex": "123456",
            "flight": None,
            "seen": 1.0,
            "seen_pos": None,
            "lat": None,
            "lon": None,
            "alt_baro": "ground",
        },
    ],
}


def _settings(database_url: str) -> Settings:
    return Settings(
        readsb_aircraft_url="http://readsb.test/aircraft.json",
        receiver_lat=35.0,
        receiver_lon=139.0,
        database_url=database_url,
    )


@pytest.fixture
async def api_client(postgres_url):
    app = create_app(settings=_settings(postgres_url))
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as http_client:
            yield http_client


async def test_empty_db_migration_collector_poll_then_api_reads_it_back(
    postgres_url, clean_db, api_client
):
    # 1. Empty, freshly-migrated DB (postgres_url + clean_db): confirm the
    #    API correctly reports "no data" before anything has been ingested.
    status_before = (await api_client.get("/api/status")).json()
    assert status_before["ingestion_state"] == "no_data"
    assert status_before["active_aircraft_count"] == 0

    # 2. Collector polls a fixture readsb response (never a live network
    #    call) and writes into the same real Postgres instance.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=FIXTURE_PAYLOAD)

    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://readsb.test"
    )
    store = await PostgresStore.connect(postgres_url)
    try:
        service = CollectorService(
            client=http_client,
            url="/aircraft.json",
            store=store,
            receiver_lat=35.0,
            receiver_lon=139.0,
            poll_interval_seconds=5.0,
            track_sample_seconds=30.0,
        )
        interval = await service.poll_once()
    finally:
        await http_client.aclose()
        await store.close()

    assert interval == 5.0

    # 3. The real FastAPI app, reading the same database, reflects what the
    #    collector just wrote -- both the aircraft with a position and the
    #    one without (ground/no-position aircraft still count as "received").
    status_after = (await api_client.get("/api/status")).json()
    assert status_after["ingestion_state"] == "ok"
    assert status_after["active_aircraft_count"] == 2
    assert status_after["position_aircraft_count"] == 1

    recent = (await api_client.get("/api/aircraft/recent")).json()
    icaos = {row["icao"] for row in recent}
    assert icaos == {"abcdef", "123456"}

    tracks = (await api_client.get("/api/tracks?hours=1")).json()
    track_icaos = {feature["properties"]["icao"] for feature in tracks["features"]}
    assert track_icaos == {"abcdef"}  # only the aircraft with a valid position
