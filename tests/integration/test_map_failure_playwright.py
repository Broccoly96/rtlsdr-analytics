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
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.main import create_app
from app.collector.store import IngestionStatus
from app.config import Settings
from app.db.postgres_store import PostgresStore
from app.domain.models import AircraftObservation, ReceptionState

try:
    from playwright.async_api import async_playwright, expect

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

FAKE_MAP_STYLE_URL = "https://example-tiles.invalid/styles/broken"
STATIC_ROOT = Path(__file__).resolve().parents[2] / "app" / "static"
UI_PATHS = (
    "/",
    "/static/daily.html",
    "/static/receiver.html",
    "/static/fullmap.html",
    "/static/globe.html",
    "/static/history.html",
    "/static/rawdata.html",
    "/static/settings.html",
)
RESPONSIVE_VIEWPORTS = (
    (360, 800),
    (390, 844),
    (430, 932),
    (412, 960),
    (768, 1024),
    (832, 750),
    (834, 1194),
    (1024, 768),
    (1440, 900),
)


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


@pytest.fixture
async def static_ui_server():
    """Serve the real static UI without starting the database-backed app."""
    app = FastAPI()

    @app.get("/")
    async def index():
        return FileResponse(STATIC_ROOT / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
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


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright is not installed")
async def test_aircraft_detail_drawer_keyboard_and_focus_contract(static_ui_server):
    """The shared detail surface behaves as a modal drawer, not a visual-only aside."""
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Chromium is not available in this environment: {exc}")

            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.route("https://api.adsbdb.com/**", lambda route: route.abort("failed"))
            await page.route("**/api/**", lambda route: route.abort("failed"))
            await page.goto(static_ui_server, wait_until="load", timeout=20000)

            # Use the public trigger factory so this remains independent of
            # asynchronous ranking data while exercising the production module.
            await page.evaluate(
                """async () => {
                    const module = await import('/static/js/aircraftinfo.js');
                    const trigger = module.createAircraftInfoTrigger('abcdef', 'MAPTEST1');
                    trigger.id = 'drawer-test-trigger';
                    document.body.prepend(trigger);
                }"""
            )
            trigger = page.locator("#drawer-test-trigger")
            await trigger.click()

            drawer = page.locator("#aircraft-detail-drawer")
            await drawer.wait_for(state="visible")
            assert await drawer.get_attribute("role") == "dialog"
            assert await drawer.get_attribute("aria-modal") == "true"
            assert await drawer.get_attribute("aria-labelledby") == "aircraft-detail-title"
            assert await page.locator("body").evaluate(
                "element => element.classList.contains('aircraft-drawer-open')"
            )
            assert await page.locator(".aircraft-sidebar__close").evaluate(
                "element => element === document.activeElement"
            )

            # With the close control as the only immediately available target,
            # Tab must remain inside the dialog rather than entering the page.
            await page.keyboard.press("Tab")
            assert await drawer.evaluate("element => element.contains(document.activeElement)")

            await page.keyboard.press("Escape")
            assert await drawer.is_hidden()
            assert not await page.locator("body").evaluate(
                "element => element.classList.contains('aircraft-drawer-open')"
            )
            assert await trigger.evaluate("element => element === document.activeElement")

            await browser.close()
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip(f"Chromium browser binary is not installed: {exc}")
        raise


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright is not installed")
async def test_responsive_shell_contract_and_no_document_overflow(static_ui_server):
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Chromium is not available in this environment: {exc}")

            page = await browser.new_page()
            await page.route("**/api/**", lambda route: route.abort("failed"))

            for width, height in RESPONSIVE_VIEWPORTS:
                await page.set_viewport_size({"width": width, "height": height})
                expected_rail_width = (
                    None if width < 600 else ((64, 72) if width < 1024 else (208, 224))
                )

                for path in UI_PATHS:
                    await page.goto(
                        f"{static_ui_server}{path}",
                        wait_until="domcontentloaded",
                        timeout=20000,
                    )
                    await page.locator(".mobile-nav").wait_for(state="attached")

                    layout = await page.evaluate(
                        """() => ({
                            overflow: document.documentElement.scrollWidth
                                > document.documentElement.clientWidth + 1,
                            duplicateIds: [...document.querySelectorAll('[id]')]
                                .map((element) => element.id)
                                .filter((id, index, ids) => ids.indexOf(id) !== index),
                            hasMain: Boolean(document.querySelector('main.page-content')),
                        })"""
                    )
                    context = f"{path} at {width}x{height}"
                    assert not layout["overflow"], f"document overflows horizontally: {context}"
                    assert not layout["duplicateIds"], f"duplicate IDs: {context}"
                    assert layout["hasMain"], f"main content missing: {context}"

                    mobile_nav = page.locator(".mobile-nav")
                    rail = page.locator(".app-nav")
                    if expected_rail_width is None:
                        assert await mobile_nav.is_visible()
                        assert await rail.is_hidden()
                    else:
                        assert await mobile_nav.is_hidden()
                        assert await rail.is_visible()
                        rail_width = (await rail.bounding_box())["width"]
                        assert expected_rail_width[0] <= rail_width <= expected_rail_width[1]

                    if path in ("/static/fullmap.html", "/static/globe.html"):
                        canvas_box = await page.locator(".workspace__canvas").bounding_box()
                        panel_box = await page.locator(".panel--workspace").bounding_box()
                        inner_selector = "#map" if "fullmap" in path else "#cesium-container"
                        inner_box = await page.locator(inner_selector).bounding_box()
                        assert panel_box["width"] >= canvas_box["width"] - 4, context
                        assert inner_box["width"] >= canvas_box["width"] - 4, context
                        assert inner_box["height"] >= canvas_box["height"] * 0.9, context

                if width < 600:
                    await page.goto(static_ui_server, wait_until="domcontentloaded", timeout=20000)
                    toggle = page.locator("#mobile-more-toggle")
                    await toggle.click()
                    assert await toggle.get_attribute("aria-expanded") == "true"
                    dialog = page.locator("#mobile-more-dialog")
                    assert await dialog.evaluate("element => element.open")
                    await page.keyboard.press("Escape")
                    await expect(toggle).to_have_attribute("aria-expanded", "false")
                    assert await toggle.evaluate("element => element === document.activeElement")

            await browser.close()
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip(f"Chromium browser binary is not installed: {exc}")
        raise
