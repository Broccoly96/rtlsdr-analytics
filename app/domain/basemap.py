"""Server-side basemap image compositing for the reception-dome ground
plane (app/static/js/reception-dome.js), backing GET /api/receiver/
basemap.png (app/api/routers/receiver.py).

Why this exists as a server-side raster composite rather than the more
obvious "just send the receiver's lat/lon to the browser and let
MapLibre (already used on map.js/fullmap.js) draw the base layer": this
app has a firm, previously-established design principle that the
receiver's exact coordinates never reach the browser (see CLAUDE.md's
"What this project is" section) -- no endpoint anywhere in this codebase
does that today, and RECEIVER_LAT/RECEIVER_LON only ever get used
server-side (app/api/main.py, app/domain/celestial.py). Rather than
being the first exception, this endpoint keeps the coordinates
server-side and only ever sends the *pixels* of a map image across the
boundary -- the client asks for a radius (a distance, not a location)
and gets back an opaque PNG.

Tile source: raw OpenStreetMap raster tiles (tile.openstreetmap.org),
not this app's existing MAP_STYLE_URL (OpenFreeMap, vector-tile-only --
rendering a vector style server-side would need a full map-rendering
engine or a headless browser in the production image, which is a much
bigger change than this feature warrants). OSM's tile usage policy
requires a descriptive User-Agent (get_user_agent() already provides
one, used the same way for api.adsbdb.com/api.planespotters.net) and
discourages heavy automated use; this endpoint's own in-memory cache
(keyed by a coarse radius bucket, since the receiver's location is
fixed for the lifetime of the process) means the real tile servers are
only ever hit a handful of times total, not per-request.
"""

from __future__ import annotations

import io
import math
import time

import httpx
from PIL import Image

from app.version import get_user_agent

TILE_SIZE_PX = 256
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE_FETCH_TIMEOUT_SECONDS = 5.0

MIN_RADIUS_KM = 5.0
MAX_RADIUS_KM = 500.0
# Coarse bucketing so a fixed receiver location only ever needs a handful
# of distinct cached images, however many different `hours` selections
# (and therefore data extents) the dome ever gets queried with.
RADIUS_BUCKET_KM = 25.0

OUTPUT_PX = 512
# Defensive cap on tiles fetched for one request, matching this feature's
# other defensive caps (DOME_MAX_CELLS, MAX_GRID_CELLS) -- should never
# actually bind given MIN_ZOOM below, but guards against a future zoom
# calculation bug requesting an unbounded tile grid.
MAX_TILES_PER_AXIS = 12
MIN_ZOOM = 1
MAX_ZOOM = 16

_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days -- basemap imagery barely changes
_cache: dict[float, tuple[float, bytes]] = {}


def bucket_radius_km(radius_km: float) -> float:
    """Rounds up to the nearest RADIUS_BUCKET_KM step, clamped to
    [MIN_RADIUS_KM, MAX_RADIUS_KM]."""
    clamped = max(MIN_RADIUS_KM, min(MAX_RADIUS_KM, radius_km))
    return math.ceil(clamped / RADIUS_BUCKET_KM) * RADIUS_BUCKET_KM


def _choose_zoom(receiver_lat: float, radius_km: float, output_px: int) -> int:
    """Picks the Web Mercator zoom level whose meters-per-pixel most
    closely covers `2 * radius_km` across `output_px` pixels, following
    the standard OSM/Google Maps zoom formula (156543.03392 m/px at the
    equator at zoom 0, scaled by cos(latitude) and halved per zoom
    level -- https://wiki.openstreetmap.org/wiki/Zoom_levels)."""
    target_meters_per_px = (radius_km * 2.0 * 1000.0) / output_px
    lat_rad = math.radians(receiver_lat)
    equatorial_meters_per_px_at_zoom0 = 156543.03392 * math.cos(lat_rad)
    zoom = math.log2(equatorial_meters_per_px_at_zoom0 / target_meters_per_px)
    return max(MIN_ZOOM, min(MAX_ZOOM, round(zoom)))


def _lat_lon_to_pixel(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Global pixel coordinates (origin top-left of the zoom level's full
    map) under the standard Web Mercator projection used by OSM/most XYZ
    tile servers."""
    n = 2**zoom
    lat_rad = math.radians(lat)
    x = n * (lon + 180.0) / 360.0
    y = n * (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0
    return x * TILE_SIZE_PX, y * TILE_SIZE_PX


async def _fetch_tile(
    client: httpx.AsyncClient, zoom: int, tile_x: int, tile_y: int
) -> Image.Image:
    n = 2**zoom
    # OSM tiles don't wrap in Y (poles), but do wrap in X (antimeridian).
    wrapped_x = tile_x % n
    if not (0 <= tile_y < n):
        return Image.new("RGB", (TILE_SIZE_PX, TILE_SIZE_PX), (30, 30, 30))
    url = OSM_TILE_URL.format(z=zoom, x=wrapped_x, y=tile_y)
    try:
        response = await client.get(url, timeout=TILE_FETCH_TIMEOUT_SECONDS)
        if response.status_code != 200:
            return Image.new("RGB", (TILE_SIZE_PX, TILE_SIZE_PX), (30, 30, 30))
        return Image.open(io.BytesIO(response.content)).convert("RGB")
    except (httpx.HTTPError, OSError):
        return Image.new("RGB", (TILE_SIZE_PX, TILE_SIZE_PX), (30, 30, 30))


async def _render_basemap_png(
    receiver_lat: float,
    receiver_lon: float,
    radius_km: float,
    *,
    output_px: int = OUTPUT_PX,
    client: httpx.AsyncClient | None = None,
) -> bytes:
    """Composites OSM raster tiles into a single square PNG, `output_px`
    wide, centered on (receiver_lat, receiver_lon), spanning
    `2 * radius_km` kilometers. Split out from the cached route handler
    so tests can inject a mocked client (same pattern as
    app/api/routers/aircraft_history.py's _fetch_photo)."""
    zoom = _choose_zoom(receiver_lat, radius_km, output_px)
    center_px_x, center_px_y = _lat_lon_to_pixel(receiver_lat, receiver_lon, zoom)

    half = output_px / 2.0
    px_min, px_max = center_px_x - half, center_px_x + half
    py_min, py_max = center_px_y - half, center_px_y + half

    tile_x_min = math.floor(px_min / TILE_SIZE_PX)
    tile_x_max = math.floor((px_max - 1) / TILE_SIZE_PX)
    tile_y_min = math.floor(py_min / TILE_SIZE_PX)
    tile_y_max = math.floor((py_max - 1) / TILE_SIZE_PX)

    tiles_x = min(tile_x_max - tile_x_min + 1, MAX_TILES_PER_AXIS)
    tiles_y = min(tile_y_max - tile_y_min + 1, MAX_TILES_PER_AXIS)

    owns_client = client is None
    http_client = client or httpx.AsyncClient(headers={"User-Agent": get_user_agent()})
    try:
        composite = Image.new("RGB", (tiles_x * TILE_SIZE_PX, tiles_y * TILE_SIZE_PX))
        for row in range(tiles_y):
            for col in range(tiles_x):
                tile = await _fetch_tile(
                    http_client, zoom, tile_x_min + col, tile_y_min + row
                )
                composite.paste(tile, (col * TILE_SIZE_PX, row * TILE_SIZE_PX))
    finally:
        if owns_client:
            await http_client.aclose()

    crop_left = int(round(px_min - tile_x_min * TILE_SIZE_PX))
    crop_top = int(round(py_min - tile_y_min * TILE_SIZE_PX))
    cropped = composite.crop(
        (crop_left, crop_top, crop_left + output_px, crop_top + output_px)
    )

    buffer = io.BytesIO()
    cropped.save(buffer, format="PNG")
    return buffer.getvalue()


async def get_basemap_png(
    receiver_lat: float,
    receiver_lon: float,
    radius_km: float,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[bytes, float]:
    """Cached entry point: returns (png_bytes, actual_bucketed_radius_km).
    The bucketed radius is returned alongside the image (rather than just
    the bytes) so the frontend can size the ground plane to the radius
    that was *actually* rendered, not the one it asked for."""
    bucketed_radius_km = bucket_radius_km(radius_km)
    cached = _cache.get(bucketed_radius_km)
    if cached is not None and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1], bucketed_radius_km

    png_bytes = await _render_basemap_png(
        receiver_lat, receiver_lon, bucketed_radius_km, client=client
    )
    _cache[bucketed_radius_km] = (time.monotonic(), png_bytes)
    return png_bytes, bucketed_radius_km
