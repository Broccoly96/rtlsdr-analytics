"""GET /api/heatmap -- position-density grid for the map's heatmap
overlay, with optional altitude-band/hour-of-day/day-of-week filters."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_pool
from app.api.schemas import GridCellResponse, HeatmapResponse
from app.db.queries.heatmap import grid_density
from app.domain.bands import ALTITUDE_BANDS

router = APIRouter(prefix="/api", tags=["heatmap"])

_VALID_ALTITUDE_BAND_KEYS = {band.key for band in ALTITUDE_BANDS}


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    hours: int = Query(24, ge=1, le=720),
    altitude_band: str | None = Query(None),
    hour_of_day: int | None = Query(None, ge=0, le=23),
    day_of_week: int | None = Query(None, ge=0, le=6),
    pool=Depends(get_pool),
) -> HeatmapResponse:
    if altitude_band is not None and altitude_band not in _VALID_ALTITUDE_BAND_KEYS:
        raise HTTPException(status_code=422, detail=f"invalid altitude_band: {altitude_band!r}")
    cells = await grid_density(
        pool,
        hours,
        altitude_band=altitude_band,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
    )
    return HeatmapResponse(
        hours=hours,
        cells=[GridCellResponse(**asdict(cell)) for cell in cells],
    )
