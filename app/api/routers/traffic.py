"""GET /api/traffic."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_pool
from app.api.schemas import TrafficBucketResponse, TrafficResponse
from app.db.queries.traffic import get_traffic

router = APIRouter(prefix="/api", tags=["traffic"])


@router.get("/traffic", response_model=TrafficResponse)
async def get_traffic_endpoint(
    hours: int = Query(24, ge=1, le=168),
    pool=Depends(get_pool),
) -> TrafficResponse:
    buckets, unique_count = await get_traffic(pool, hours)
    return TrafficResponse(
        hours=hours,
        buckets=[TrafficBucketResponse(**asdict(bucket)) for bucket in buckets],
        unique_aircraft_count=unique_count,
    )
