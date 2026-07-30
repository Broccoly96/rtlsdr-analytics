"""GET /api/aircraft/{icao}/history, /positions, /photo, GET /api/aircraft/frequent."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.dependencies import get_pool
from app.api.schemas import (
    AircraftHistoryResponse,
    AircraftPhotoResponse,
    AircraftPositionsResponse,
    CallsignHistoryEntryResponse,
    FrequentAircraftEntryResponse,
    FrequentAircraftResponse,
    LatestObservationResponse,
    TrackPointResponse,
)
from app.db.queries.aircraft_history import (
    aircraft_summary,
    callsign_history,
    latest_observation,
    most_frequent,
)
from app.db.queries.tracks import get_aircraft_track
from app.version import get_user_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["aircraft-history"])

# Planespotters.net's own /pub/ API requires a descriptive User-Agent with a
# contact URL and rejects generic library/browser strings -- a browser's own
# fetch() can never send a custom User-Agent (forbidden header), so this
# lookup is a server-side proxy rather than the direct-from-browser call
# Milestone Q originally shipped (discovered via real-browser testing: the
# direct-from-browser version was silently non-functional for everyone,
# always falling back to "photo not found"). Never persisted -- same
# "display-only, not cached" rule as before, the only change is *where*
# the HTTP call happens. See README Security & Privacy: unlike the
# registration/type lookup (still direct from the browser, still works
# fine), the server now sees which aircraft's photo you requested (not
# stored anywhere) -- a deliberate, narrower privacy trade-off than before,
# approved by the user in exchange for the feature actually working.
PLANESPOTTERS_URL = "https://api.planespotters.net/pub/photos/hex/"
PLANESPOTTERS_TIMEOUT_SECONDS = 6.0

_EMPTY_PHOTO = AircraftPhotoResponse(
    thumbnail_url=None, thumbnail_width=None, thumbnail_height=None, photographer=None, link=None
)

# Matches the DB's own aircraft_icao_format CHECK constraint
# (migrations/versions/62c3f8022564_initial_schema.py): 6 hex digits, with
# an optional leading `~` (readsb's convention for a non-ICAO/undetermined
# address). Checked here too so a malformed icao is a clean 422 rather
# than silently falling through to a 404 that looks identical to "a
# well-formed but unknown aircraft".
_ICAO_PATTERN = re.compile(r"^~?[0-9a-f]{6}$")


@router.get("/aircraft/{icao}/history", response_model=AircraftHistoryResponse)
async def get_aircraft_history(
    icao: str = Path(...),
    pool=Depends(get_pool),
) -> AircraftHistoryResponse:
    if not _ICAO_PATTERN.match(icao):
        raise HTTPException(status_code=422, detail="invalid icao format")

    summary = await aircraft_summary(pool, icao)
    if summary is None:
        raise HTTPException(status_code=404, detail="aircraft not found")

    callsigns = await callsign_history(pool, icao)
    latest = await latest_observation(pool, icao)
    return AircraftHistoryResponse(
        **asdict(summary),
        callsign_history=[CallsignHistoryEntryResponse(**asdict(entry)) for entry in callsigns],
        latest_observation=LatestObservationResponse(**asdict(latest)) if latest else None,
    )


@router.get("/aircraft/{icao}/positions", response_model=AircraftPositionsResponse)
async def get_aircraft_positions(
    icao: str = Path(...),
    hours: int = Query(6, ge=1, le=720),
    pool=Depends(get_pool),
) -> AircraftPositionsResponse:
    if not _ICAO_PATTERN.match(icao):
        raise HTTPException(status_code=422, detail="invalid icao format")

    track = await get_aircraft_track(pool, icao, hours)
    segments = track.segments if track else []
    return AircraftPositionsResponse(
        icao=icao,
        hours=hours,
        segments=[
            [TrackPointResponse(**asdict(point)) for point in segment] for segment in segments
        ],
    )


async def _fetch_photo(
    icao: str, *, client: httpx.AsyncClient | None = None
) -> AircraftPhotoResponse:
    """Split out from the route handler so tests can inject a mocked
    client (same pattern as app/notify.py/app/aircraft_lookup.py) rather
    than needing to intercept a real httpx.AsyncClient construction."""
    owns_client = client is None
    http_client = client or httpx.AsyncClient(headers={"User-Agent": get_user_agent()})
    try:
        response = await http_client.get(
            f"{PLANESPOTTERS_URL}{icao}", timeout=PLANESPOTTERS_TIMEOUT_SECONDS
        )
        if response.status_code != 200:
            return _EMPTY_PHOTO
        data = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("aircraft photo lookup failed for %s", icao, exc_info=True)
        return _EMPTY_PHOTO
    finally:
        if owns_client:
            await http_client.aclose()

    photos = data.get("photos") if isinstance(data, dict) else None
    if not photos:
        return _EMPTY_PHOTO

    photo = photos[0]
    thumbnail = photo.get("thumbnail") or {}
    thumbnail_size = thumbnail.get("size") or {}
    return AircraftPhotoResponse(
        thumbnail_url=thumbnail.get("src"),
        thumbnail_width=thumbnail_size.get("width"),
        thumbnail_height=thumbnail_size.get("height"),
        photographer=photo.get("photographer"),
        link=photo.get("link"),
    )


@router.get("/aircraft/{icao}/photo", response_model=AircraftPhotoResponse)
async def get_aircraft_photo(icao: str = Path(...)) -> AircraftPhotoResponse:
    if not _ICAO_PATTERN.match(icao):
        raise HTTPException(status_code=422, detail="invalid icao format")
    return await _fetch_photo(icao)


@router.get("/aircraft/frequent", response_model=FrequentAircraftResponse)
async def get_aircraft_frequent(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=100),
    pool=Depends(get_pool),
) -> FrequentAircraftResponse:
    entries = await most_frequent(pool, days, limit)
    return FrequentAircraftResponse(
        days=days,
        limit=limit,
        aircraft=[FrequentAircraftEntryResponse(**asdict(entry)) for entry in entries],
    )
