"""Unit tests for app.domain.basemap (the reception-dome ground-plane
basemap compositor), with the upstream OSM tile fetch mocked via
httpx.MockTransport -- same technique as tests/unit/test_aircraft_photo.py
-- never hits the real tile server in tests.
"""

from __future__ import annotations

import io
import math

import httpx
import pytest
from PIL import Image

import app.domain.basemap as basemap

TOKYO_LAT = 35.6812
TOKYO_LON = 139.7671


@pytest.fixture(autouse=True)
def _clear_cache():
    basemap._cache.clear()
    yield
    basemap._cache.clear()


def _solid_tile_png(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    img = Image.new("RGB", (basemap.TILE_SIZE_PX, basemap.TILE_SIZE_PX), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --- bucket_radius_km -------------------------------------------------


def test_bucket_radius_rounds_up_to_step():
    # clamped to MIN_RADIUS_KM first, then rounded up to the next bucket step
    assert basemap.bucket_radius_km(1.0) == basemap.RADIUS_BUCKET_KM
    assert basemap.bucket_radius_km(26.0) == 50.0
    assert basemap.bucket_radius_km(50.0) == 50.0
    assert basemap.bucket_radius_km(9999.0) == basemap.MAX_RADIUS_KM


# --- _choose_zoom / _lat_lon_to_pixel ----------------------------------


def test_choose_zoom_decreases_as_radius_grows():
    small = basemap._choose_zoom(TOKYO_LAT, 25.0, basemap.OUTPUT_PX)
    large = basemap._choose_zoom(TOKYO_LAT, 400.0, basemap.OUTPUT_PX)
    assert large < small
    assert basemap.MIN_ZOOM <= large <= basemap.MAX_ZOOM
    assert basemap.MIN_ZOOM <= small <= basemap.MAX_ZOOM


def test_lat_lon_to_pixel_is_monotonic_in_longitude():
    zoom = 8
    x1, _ = basemap._lat_lon_to_pixel(TOKYO_LAT, TOKYO_LON, zoom)
    x2, _ = basemap._lat_lon_to_pixel(TOKYO_LAT, TOKYO_LON + 1.0, zoom)
    assert x2 > x1


def test_choose_zoom_rounding_would_misrepresent_scale_without_a_final_resize():
    # Regression guard for the exact bug that caused a real, user-visible
    # scale mismatch between the basemap and the reception dome's distance
    # rings: _choose_zoom only ever returns an integer zoom, and each zoom
    # differs from its neighbor by exactly 2x, so *some* radius is
    # guaranteed to land far enough from an integer zoom that the naive
    # "crop output_px pixels at the rounded zoom" approach would be off by
    # a large, visible margin. This asserts that gap is real (i.e. this
    # test would fail to find a bad case if _choose_zoom's rounding error
    # were ever made negligible some other way), so _render_basemap_png's
    # final-resize correction has something real to correct.
    worst_ratio = 1.0
    for radius_km in range(5, 500, 3):
        zoom = basemap._choose_zoom(TOKYO_LAT, float(radius_km), basemap.OUTPUT_PX)
        lat_rad = math.radians(TOKYO_LAT)
        actual_meters_per_px = 156543.03392 * math.cos(lat_rad) / (2**zoom)
        naive_crop_km = (actual_meters_per_px * basemap.OUTPUT_PX) / 1000.0
        ratio = naive_crop_km / (radius_km * 2.0)
        worst_ratio = max(worst_ratio, ratio, 1.0 / ratio)
    assert worst_ratio > 1.2  # a >20% scale error is easily visible


async def test_render_basemap_output_size_is_exact_regardless_of_zoom_rounding():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_solid_tile_png())

    # Try enough radii to hit cases on both sides of an integer zoom
    # boundary -- output_px must come out exact every time, via the
    # final resize, not just when radius_km happens to line up neatly.
    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        for radius_km in (12.0, 40.0, 77.0, 150.0, 310.0):
            png_bytes = await basemap._render_basemap_png(
                TOKYO_LAT, TOKYO_LON, radius_km, output_px=200, client=client
            )
            img = Image.open(io.BytesIO(png_bytes))
            assert img.size == (200, 200)


# --- _render_basemap_png / get_basemap_png -----------------------------


async def test_render_basemap_returns_requested_output_size():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_solid_tile_png())

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        png_bytes = await basemap._render_basemap_png(
            TOKYO_LAT, TOKYO_LON, 50.0, output_px=128, client=client
        )

    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (128, 128)


async def test_render_basemap_survives_tile_fetch_failure():
    def _raise(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network failure", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_raise)) as client:
        png_bytes = await basemap._render_basemap_png(
            TOKYO_LAT, TOKYO_LON, 50.0, output_px=64, client=client
        )

    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (64, 64)


async def test_render_basemap_survives_non_200_response():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        png_bytes = await basemap._render_basemap_png(
            TOKYO_LAT, TOKYO_LON, 50.0, output_px=64, client=client
        )

    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (64, 64)


async def test_get_basemap_png_caches_by_bucket_and_does_not_refetch():
    call_count = 0

    def _respond(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, content=_solid_tile_png())

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        first_bytes, first_radius = await basemap.get_basemap_png(
            TOKYO_LAT, TOKYO_LON, 40.0, client=client
        )
        first_call_count = call_count
        second_bytes, second_radius = await basemap.get_basemap_png(
            TOKYO_LAT, TOKYO_LON, 40.0, client=client
        )

    assert first_radius == second_radius == 50.0  # both bucket to the same 25km step
    assert first_bytes == second_bytes
    assert call_count == first_call_count  # second call served from cache, no refetch


async def test_get_basemap_png_different_buckets_do_not_share_cache_entry():
    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_solid_tile_png())

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        _, radius_a = await basemap.get_basemap_png(TOKYO_LAT, TOKYO_LON, 10.0, client=client)
        _, radius_b = await basemap.get_basemap_png(TOKYO_LAT, TOKYO_LON, 200.0, client=client)

    assert radius_a != radius_b
    assert len(basemap._cache) == 2
