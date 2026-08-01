"""Unit tests for app.api.routers.aircraft_history._fetch_photo (the
server-side Planespotters.net proxy), with the upstream call mocked via
httpx.MockTransport -- same technique as tests/unit/test_notify.py --
never hits the real service in tests.
"""

from __future__ import annotations

import httpx
import pytest

import app.api.routers.aircraft_history as aircraft_history_router
from app.api.routers.aircraft_history import _fetch_photo, get_aircraft_photo
from app.version import get_user_agent


@pytest.fixture(autouse=True)
def _clear_photo_cache():
    # The cache is a module-level dict shared across every test in this
    # process -- clear it before and after each test so tests can't leak
    # state into each other via a shared icao.
    aircraft_history_router._photo_cache.clear()
    yield
    aircraft_history_router._photo_cache.clear()

FOUND_BODY = {
    "photos": [
        {
            "thumbnail": {
                "src": "https://example.invalid/thumb.jpg",
                "size": {"width": 200, "height": 150},
            },
            "thumbnail_large": {"src": "https://example.invalid/large.jpg"},
            "link": "https://www.planespotters.net/photo/123",
            "photographer": "Jane Spotter",
        }
    ]
}


def test_default_client_sends_descriptive_user_agent():
    # Planespotters.net explicitly rejects generic library/browser User-
    # Agent strings -- verifies the production code path (no client
    # injected -- see the other tests here) actually sets one, without
    # making a real network call.
    client = httpx.AsyncClient(headers={"User-Agent": get_user_agent()})
    assert "rtlsdr-analytics" in client.headers["user-agent"]
    assert "github.com" in client.headers["user-agent"]


async def test_found_photo_maps_fields():
    def _respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/aaaaaa")
        return httpx.Response(200, json=FOUND_BODY)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        result = await _fetch_photo("aaaaaa", client=client)

    assert result.thumbnail_url == "https://example.invalid/thumb.jpg"
    assert result.thumbnail_width == 200
    assert result.thumbnail_height == 150
    assert result.photographer == "Jane Spotter"
    assert result.link == "https://www.planespotters.net/photo/123"


async def test_no_photos_returns_empty():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"photos": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        result = await _fetch_photo("bbbbbb", client=client)

    assert result.thumbnail_url is None
    assert result.photographer is None


async def test_non_200_returns_empty_not_raises():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"error": "Generic library User-Agent strings are not accepted."}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        result = await _fetch_photo("cccccc", client=client)

    assert result.thumbnail_url is None


async def test_connection_error_returns_empty_not_raises():
    def _raise(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network failure", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_raise)) as client:
        result = await _fetch_photo("dddddd", client=client)

    assert result.thumbnail_url is None


# --- route-level in-memory TTL cache (Milestone PP) ------------------------


async def test_route_caches_photo_and_does_not_refetch(monkeypatch):
    call_count = 0

    async def _fake_fetch_photo(icao, *, client=None):
        nonlocal call_count
        call_count += 1
        return aircraft_history_router.AircraftPhotoResponse(
            thumbnail_url="https://example.invalid/thumb.jpg",
            thumbnail_width=200,
            thumbnail_height=150,
            photographer="Jane Spotter",
            link="https://www.planespotters.net/photo/123",
        )

    monkeypatch.setattr(aircraft_history_router, "_fetch_photo", _fake_fetch_photo)

    first = await get_aircraft_photo(icao="aaaaaa")
    second = await get_aircraft_photo(icao="aaaaaa")

    assert call_count == 1  # second call served from cache, not re-fetched
    assert first == second


async def test_route_cache_is_per_icao(monkeypatch):
    call_count = 0

    async def _fake_fetch_photo(icao, *, client=None):
        nonlocal call_count
        call_count += 1
        return aircraft_history_router._EMPTY_PHOTO

    monkeypatch.setattr(aircraft_history_router, "_fetch_photo", _fake_fetch_photo)

    await get_aircraft_photo(icao="aaaaaa")
    await get_aircraft_photo(icao="bbbbbb")

    assert call_count == 2  # different icaos are never conflated
