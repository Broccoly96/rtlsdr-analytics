"""End-to-end API tests against a real, ephemeral PostgreSQL instance.

Covers PLAN.md Milestone C's explicit test scenarios: health live/ready
(including DB-down and stale/no-data cases), status/traffic/rankings/tracks
bounds, empty-data behavior, and basic OpenAPI-schema consistency.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import create_app
from app.collector.aggregator import TrafficMinute
from app.collector.store import IngestionStatus
from app.config import Settings
from app.db.postgres_store import PostgresStore
from app.domain.models import AircraftObservation, ReceptionState

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _settings(database_url: str) -> Settings:
    return Settings(
        readsb_aircraft_url="http://127.0.0.1/tar1090/data/aircraft.json",
        receiver_lat=35.0,
        receiver_lon=139.0,
        database_url=database_url,
    )


@pytest.fixture
async def client(postgres_url, clean_db):
    app = create_app(settings=_settings(postgres_url))
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as http_client:
            yield http_client


async def _seed_fresh_success(postgres_url: str, *, active=2, position=1) -> None:
    store = await PostgresStore.connect(postgres_url)
    try:
        now = datetime.now(UTC)
        await store.upsert_aircraft("aaaaaa", now, "TEST001")
        await store.upsert_aircraft("bbbbbb", now, "TEST002")
        await store.insert_observation(
            AircraftObservation(
                icao="aaaaaa",
                observed_at=now,
                callsign="TEST001",
                lat=35.0,
                lon=139.0,
                altitude_ft=10000.0,
                ground_speed_kt=400.0,
                track_deg=90.0,
                vertical_rate_fpm=0.0,
                rssi=-20.0,
                distance_km=50.0,
                bearing_deg=45.0,
                source_age_seconds=0.5,
                reception_state=ReceptionState.POSITION_ACQUIRED,
            )
        )
        await store.record_ingestion_status(IngestionStatus(now, True, 10.0, active, None))
    finally:
        await store.close()


async def _seed_stale_success(postgres_url: str) -> None:
    store = await PostgresStore.connect(postgres_url)
    try:
        old = datetime.now(UTC) - timedelta(minutes=10)
        await store.record_ingestion_status(IngestionStatus(old, True, 10.0, 3, None))
    finally:
        await store.close()


async def _seed_failure(postgres_url: str) -> None:
    store = await PostgresStore.connect(postgres_url)
    try:
        now = datetime.now(UTC)
        await store.record_ingestion_status(IngestionStatus(now, False, None, None, "HTTPError"))
    finally:
        await store.close()


# --- health -------------------------------------------------------------


async def test_live_always_ok(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_fails_with_no_data(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert "detail" in response.json()


async def test_ready_ok_after_fresh_success(postgres_url, client: AsyncClient) -> None:
    await _seed_fresh_success(postgres_url)
    response = await client.get("/health/ready")
    assert response.status_code == 200


async def test_ready_fails_on_stale_data(postgres_url, client: AsyncClient) -> None:
    await _seed_stale_success(postgres_url)
    response = await client.get("/health/ready")
    assert response.status_code == 503


async def test_ready_fails_on_ingestion_failure(postgres_url, client: AsyncClient) -> None:
    await _seed_failure(postgres_url)
    response = await client.get("/health/ready")
    assert response.status_code == 503


async def test_ready_recovers_after_a_fresh_success_follows_a_failure(
    postgres_url, client: AsyncClient
) -> None:
    await _seed_failure(postgres_url)
    assert (await client.get("/health/ready")).status_code == 503
    await _seed_fresh_success(postgres_url)
    assert (await client.get("/health/ready")).status_code == 200


# --- status ---------------------------------------------------------------


async def test_status_no_data(client: AsyncClient) -> None:
    response = await client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert body["ingestion_state"] == "no_data"
    assert body["active_aircraft_count"] == 0
    assert body["last_ingestion_at"] is None


async def test_status_ok_with_fresh_data(postgres_url, client: AsyncClient) -> None:
    await _seed_fresh_success(postgres_url)
    response = await client.get("/api/status")
    body = response.json()
    assert body["ingestion_state"] == "ok"
    assert body["active_aircraft_count"] >= 1
    assert body["display_timezone"] == "Asia/Tokyo"


async def test_status_stale_zeroes_counts(postgres_url, client: AsyncClient) -> None:
    await _seed_stale_success(postgres_url)
    response = await client.get("/api/status")
    body = response.json()
    assert body["ingestion_state"] == "stale"
    assert body["active_aircraft_count"] == 0
    assert body["position_aircraft_count"] == 0


# --- traffic ----------------------------------------------------------------


async def test_traffic_default_window_with_no_data(client: AsyncClient) -> None:
    response = await client.get("/api/traffic")
    assert response.status_code == 200
    body = response.json()
    assert body["hours"] == 24
    assert len(body["buckets"]) == 24 * 60
    assert all(b["active_aircraft_count"] == 0 for b in body["buckets"])
    assert body["unique_aircraft_count"] == 0


async def test_traffic_bounds_1_and_168(client: AsyncClient) -> None:
    assert (await client.get("/api/traffic", params={"hours": 1})).status_code == 200
    assert (await client.get("/api/traffic", params={"hours": 168})).status_code == 200


async def test_traffic_out_of_range_hours_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/traffic", params={"hours": 0})).status_code == 422
    assert (await client.get("/api/traffic", params={"hours": 169})).status_code == 422


async def test_traffic_with_seeded_minute(postgres_url, client: AsyncClient) -> None:
    store = await PostgresStore.connect(postgres_url)
    # A few minutes in the past, not the current (still in-progress, and
    # therefore excluded by get_traffic's exclusive upper bound) minute.
    bucket_at = (datetime.now(UTC) - timedelta(minutes=5)).replace(second=0, microsecond=0)
    try:
        await store.upsert_traffic_minute(TrafficMinute(bucket_at, 5, 3, 100))
    finally:
        await store.close()
    response = await client.get("/api/traffic", params={"hours": 1})
    body = response.json()
    matching = [b for b in body["buckets"] if b["active_aircraft_count"] == 5]
    assert len(matching) == 1


# --- rankings ---------------------------------------------------------------


async def test_rankings_empty(client: AsyncClient) -> None:
    response = await client.get("/api/rankings")
    assert response.status_code == 200
    body = response.json()
    assert body["farthest"] == []
    assert body["closest"] == []


async def test_rankings_bounds_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/rankings", params={"limit": 0})).status_code == 422
    assert (await client.get("/api/rankings", params={"limit": 101})).status_code == 422
    assert (await client.get("/api/rankings", params={"hours": 0})).status_code == 422


async def test_rankings_farthest_and_closest_distinct_aircraft(
    postgres_url, client: AsyncClient
) -> None:
    store = await PostgresStore.connect(postgres_url)
    now = datetime.now(UTC)
    try:
        await store.upsert_aircraft("aaaaaa", now, "NEAR001")
        await store.upsert_aircraft("bbbbbb", now, "FAR0001")
        for icao, callsign, distance in (("aaaaaa", "NEAR001", 5.0), ("bbbbbb", "FAR0001", 500.0)):
            await store.insert_observation(
                AircraftObservation(
                    icao=icao,
                    observed_at=now,
                    callsign=callsign,
                    lat=35.0,
                    lon=139.0,
                    altitude_ft=10000.0,
                    ground_speed_kt=400.0,
                    track_deg=90.0,
                    vertical_rate_fpm=0.0,
                    rssi=-20.0,
                    distance_km=distance,
                    bearing_deg=45.0,
                    source_age_seconds=0.5,
                    reception_state=ReceptionState.POSITION_ACQUIRED,
                )
            )
    finally:
        await store.close()

    response = await client.get("/api/rankings", params={"hours": 24, "limit": 10})
    body = response.json()
    assert body["farthest"][0]["icao"] == "bbbbbb"
    assert body["closest"][0]["icao"] == "aaaaaa"


# --- tracks -------------------------------------------------------------


async def test_tracks_empty(client: AsyncClient) -> None:
    response = await client.get("/api/tracks")
    assert response.status_code == 200
    assert response.json() == {"type": "FeatureCollection", "features": []}


async def test_tracks_bounds_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/tracks", params={"hours": 0})).status_code == 422
    assert (await client.get("/api/tracks", params={"hours": 25})).status_code == 422


async def test_tracks_returns_linestring_for_seeded_aircraft(
    postgres_url, client: AsyncClient
) -> None:
    store = await PostgresStore.connect(postgres_url)
    now = datetime.now(UTC)
    try:
        await store.upsert_aircraft("aaaaaa", now, "TEST001")
        for i in range(3):
            await store.insert_observation(
                AircraftObservation(
                    icao="aaaaaa",
                    observed_at=now + timedelta(seconds=i * 30),
                    callsign="TEST001",
                    lat=35.0 + i * 0.01,
                    lon=139.0,
                    altitude_ft=10000.0,
                    ground_speed_kt=400.0,
                    track_deg=0.0,
                    vertical_rate_fpm=0.0,
                    rssi=-20.0,
                    distance_km=50.0,
                    bearing_deg=45.0,
                    source_age_seconds=0.5,
                    reception_state=ReceptionState.POSITION_ACQUIRED,
                )
            )
    finally:
        await store.close()

    response = await client.get("/api/tracks", params={"hours": 6})
    body = response.json()
    assert len(body["features"]) == 1
    feature = body["features"][0]
    assert feature["properties"]["icao"] == "aaaaaa"
    assert feature["properties"]["last_distance_km"] == 50.0
    assert feature["geometry"]["type"] == "MultiLineString"
    assert len(feature["geometry"]["coordinates"][0]) == 3


# --- aircraft/recent ----------------------------------------------------


async def test_recent_aircraft_empty(client: AsyncClient) -> None:
    response = await client.get("/api/aircraft/recent")
    assert response.status_code == 200
    assert response.json() == []


async def test_recent_aircraft_bounds_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/aircraft/recent", params={"limit": 0})).status_code == 422
    assert (await client.get("/api/aircraft/recent", params={"limit": 201})).status_code == 422
    assert (await client.get("/api/aircraft/recent", params={"offset": -1})).status_code == 422


async def test_recent_aircraft_returns_seeded_row(postgres_url, client: AsyncClient) -> None:
    await _seed_fresh_success(postgres_url)
    response = await client.get("/api/aircraft/recent")
    body = response.json()
    icaos = {row["icao"] for row in body}
    assert "aaaaaa" in icaos


# --- config -----------------------------------------------------------------


async def test_config_exposes_no_secrets(client: AsyncClient) -> None:
    response = await client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert body["map_style_url"].startswith("https://")
    assert body["display_timezone"] == "Asia/Tokyo"
    assert body["version"] not in (None, "", "unknown")
    assert "database_url" not in body
    assert "readsb_aircraft_url" not in body
    body_text = response.text
    assert "changeme" not in body_text
    assert "127.0.0.1/tar1090" not in body_text


# --- openapi --------------------------------------------------------------


async def test_openapi_lists_all_endpoints(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = set(response.json()["paths"])
    assert paths == {
        "/health/live",
        "/health/ready",
        "/api/status",
        "/api/traffic",
        "/api/tracks",
        "/api/rankings",
        "/api/aircraft/recent",
        "/api/config",
    }
