"""GET /api/aircraft/{icao}/history, GET /api/aircraft/frequent."""

from __future__ import annotations

import re
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.dependencies import get_pool
from app.api.schemas import (
    AircraftHistoryResponse,
    CallsignHistoryEntryResponse,
    FrequentAircraftEntryResponse,
    FrequentAircraftResponse,
)
from app.db.queries.aircraft_history import aircraft_summary, callsign_history, most_frequent

router = APIRouter(prefix="/api", tags=["aircraft-history"])

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
    return AircraftHistoryResponse(
        **asdict(summary),
        callsign_history=[CallsignHistoryEntryResponse(**asdict(entry)) for entry in callsigns],
    )


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
