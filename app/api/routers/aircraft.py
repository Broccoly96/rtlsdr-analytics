"""GET /api/aircraft/recent."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_pool
from app.api.schemas import RecentAircraftResponse
from app.db.queries.aircraft import get_recent_aircraft

router = APIRouter(prefix="/api", tags=["aircraft"])


@router.get("/aircraft/recent", response_model=list[RecentAircraftResponse])
async def get_recent(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_pool),
) -> list[RecentAircraftResponse]:
    rows = await get_recent_aircraft(pool, hours, limit, offset)
    return [RecentAircraftResponse(**asdict(row)) for row in rows]
