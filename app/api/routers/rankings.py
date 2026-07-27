"""GET /api/rankings."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_pool
from app.api.schemas import RankingEntryResponse, RankingsResponse
from app.db.queries.rankings import get_closest, get_farthest

router = APIRouter(prefix="/api", tags=["rankings"])


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=100),
    pool=Depends(get_pool),
) -> RankingsResponse:
    farthest = await get_farthest(pool, hours, limit)
    closest = await get_closest(pool, hours, limit)
    return RankingsResponse(
        hours=hours,
        limit=limit,
        farthest=[RankingEntryResponse(**asdict(entry)) for entry in farthest],
        closest=[RankingEntryResponse(**asdict(entry)) for entry in closest],
    )
