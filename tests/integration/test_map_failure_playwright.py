"""Milestone F-5 "地図障害" (map failure): style-URL failure must not take
down the rest of the dashboard. Runs a real uvicorn server against a
disposable, migrated Postgres instance (never compose.yaml's adsb-db) and
drives it with a real Chromium engine (Playwright), intercepting the
MAP_STYLE_URL request to force exactly the failure mode this checklist item
is about -- a genuinely unreachable/failing style URL, not a code mock.

Skipped (not failed) if Playwright's browser binaries aren't installed,
matching tests/contract/pg_container.py's "skip, don't fail, when the
optional real-environment dependency isn't available" convention.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
import uvicorn

from app.api.main import create_app
from app.collector.store import IngestionStatus
from app.config import Settings
from app.db.postgres_store import PostgresStore
from app.domain.models import AircraftObservation, ReceptionState

try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

FAKE_MAP_STYLE_URL = "https://example-tiles.invalid/styles/broken"


def _free_tcp_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _seed(postgres_url: str) -> None:
    store = await PostgresStore.connect(postgres_url)
    try:
        now = datetime.now(UTC)
        await store.upsert_aircraft("abcdef", now, "MAPTEST1")
        await store.insert_observation(
            AircraftObservation(
                icao="abcdef",
                observed_at=now,
                callsign="MAPTEST1",
                lat=35.5,
                lon=139.5,
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
        await store.record_ingestion_status(IngestionStatus(now, True, 10.0, 1, None))
    finally:
        await store.close()


@pytest.fixture
async def live_server(postgres_url, clean_db):
    await _seed(postgres_url)
    settings = Settings(
        readsb_aircraft_url="http://readsb.test/aircraft.json",
        receiver_lat=35.0,
        receiver_lon=139.0,
        database_url=postgres_url,
        map_style_url=FAKE_MAP_STYLE_URL,
    )
    app = create_app(settings=settings)
    port = _free_tcp_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    for _ in range(50):
        if server.started:
            break
        await asyncio.sleep(0.1)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright is not installed")
async def test_map_style_failure_does_not_break_other_panels(live_server):
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Chromium is not available in this environment: {exc}")

            page = await browser.new_page()

            async def fail_map_style(route):
                await route.abort("failed")

            await page.route(f"{FAKE_MAP_STYLE_URL}**", fail_map_style)

            await page.goto(live_server, wait_until="load", timeout=20000)
            await page.wait_for_timeout(3000)

            # The map panel shows an error instead of silently hanging...
            map_error_text = await page.locator("#map-error").inner_text()
            assert map_error_text != ""

            # ...but the rest of the dashboard is unaffected: status cards
            # reflect the seeded data, not stuck on the initial "--".
            active_text = await page.locator("#card-active").inner_text()
            assert active_text == "1"

            await browser.close()
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip(f"Chromium browser binary is not installed: {exc}")
        raise
