"""Unit tests for app.api.routers.aircraft_history._fetch_photo (the
server-side Planespotters.net proxy), with the upstream call mocked via
httpx.MockTransport -- same technique as tests/unit/test_notify.py --
never hits the real service in tests.
"""

from __future__ import annotations

import httpx

from app.api.routers.aircraft_history import _fetch_photo
from app.version import get_user_agent

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
