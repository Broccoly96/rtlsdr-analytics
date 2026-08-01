"""Unit tests for app.api.routers.weather._fetch_metar, with the upstream
call mocked via httpx.MockTransport -- same technique as
tests/unit/test_aircraft_photo.py -- never hits the real service.
"""

from __future__ import annotations

import httpx

from app.api.routers.weather import _fetch_metar

FOUND_BODY = [
    {
        "icaoId": "RJTT",
        "rawOb": "RJTT 011200Z 27010KT 9999 FEW030 22/15 Q1015",
        "obsTime": 1735732800,
        "temp": 22.0,
        "wdir": 270,
        "wspd": 10.0,
        "visib": 10.0,
        "altim": 1015.0,
        "fltCat": "VFR",
    }
]


async def test_found_metar_maps_fields():
    def _respond(request: httpx.Request) -> httpx.Response:
        assert request.url.params["ids"] == "RJTT"
        return httpx.Response(200, json=FOUND_BODY)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        result = await _fetch_metar("RJTT", client=client)

    assert result.station_icao == "RJTT"
    assert result.temperature_c == 22.0
    assert result.wind_dir_deg == 270
    assert result.flight_category == "VFR"
    assert result.observed_at is not None


async def test_empty_list_returns_empty():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        result = await _fetch_metar("RJTT", client=client)

    assert result.station_icao is None
    assert result.raw_text is None


async def test_non_200_returns_empty_not_raises():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        result = await _fetch_metar("RJTT", client=client)

    assert result.station_icao is None


async def test_connection_error_returns_empty_not_raises():
    def _raise(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network failure", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_raise)) as client:
        result = await _fetch_metar("RJTT", client=client)

    assert result.station_icao is None


async def test_malformed_json_returns_empty_not_raises():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        result = await _fetch_metar("RJTT", client=client)

    assert result.station_icao is None
