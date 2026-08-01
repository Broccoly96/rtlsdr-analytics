"""Smoke test for the receiver-performance page's "reception dome" 3D
chart (echarts-gl grid3D/scatter3D) -- the 3rd attempt at a 3D reception
visualization on this page, after two prior attempts were built and removed
(see README's Receiver performance section, PLAN.md). Kept in its own file,
separate from test_map_failure_playwright.py, so the whole feature -- this
test included -- stays a single, clean diff to remove if it's rejected a
third time.

Runs a real uvicorn server against a disposable, migrated Postgres instance
(never compose.yaml's adsb-db) and drives it with a real Chromium engine
(Playwright). Skipped (not failed) if Playwright's browser binaries aren't
installed, matching this app's existing convention for optional
real-environment dependencies.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
import uvicorn
from fastapi import FastAPI

from app.api.main import create_app
from app.config import Settings
from app.db.postgres_store import PostgresStore
from app.domain.models import AircraftObservation, ReceptionState

try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def _free_tcp_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _seed(postgres_url: str) -> None:
    store = await PostgresStore.connect(postgres_url)
    try:
        now = datetime.now(UTC)
        await store.upsert_aircraft("abcdef", now, "DOMETEST")
        await store.insert_observation(
            AircraftObservation(
                icao="abcdef",
                observed_at=now,
                callsign="DOMETEST",
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
    )
    app: FastAPI = create_app(settings=settings)
    try:
        port = _free_tcp_port()
    except PermissionError as exc:
        pytest.skip(f"Local sockets are unavailable in this environment: {exc}")
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
async def test_reception_dome_renders_without_console_errors(live_server):
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium is not available in this environment: {exc}")
        try:
            page = await browser.new_page()
            console_errors: list[str] = []
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            page.on("pageerror", lambda exc: console_errors.append(str(exc)))

            await page.goto(f"{live_server}/static/receiver.html", wait_until="load", timeout=20000)
            await page.wait_for_selector("#reception-dome-chart canvas", timeout=10000)

            error_el = page.locator("#reception-dome-chart-error")
            assert await error_el.get_attribute("hidden") is not None

            assert console_errors == []
        finally:
            await browser.close()
