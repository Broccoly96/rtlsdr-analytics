"""GET /api/receiver/* -- receiver performance: max range by compass
bearing and altitude band, and message-count/position-rate over time."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_pool
from app.api.schemas import (
    AltitudeBandRangeEntryResponse,
    AltitudeRangeResponse,
    BearingRangeEntryResponse,
    BearingRangeResponse,
    ReceptionBucketResponse,
    ReceptionResponse,
    RssiByDistanceResponse,
    RssiDistanceCellResponse,
)
from app.db.queries.receiver import (
    DEFAULT_DISTANCE_BUCKET_KM,
    DEFAULT_RSSI_BUCKET_DB,
    altitude_band_range,
    bearing_range,
    reception_timeseries,
    rssi_by_distance,
)

router = APIRouter(prefix="/api/receiver", tags=["receiver"])


@router.get("/bearing-range", response_model=BearingRangeResponse)
async def get_bearing_range(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
) -> BearingRangeResponse:
    entries = await bearing_range(pool, hours)
    return BearingRangeResponse(
        hours=hours,
        sectors=[BearingRangeEntryResponse(**asdict(entry)) for entry in entries],
    )


@router.get("/altitude-range", response_model=AltitudeRangeResponse)
async def get_altitude_range(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
) -> AltitudeRangeResponse:
    entries = await altitude_band_range(pool, hours)
    return AltitudeRangeResponse(
        hours=hours,
        bands=[AltitudeBandRangeEntryResponse(**asdict(entry)) for entry in entries],
    )


@router.get("/reception", response_model=ReceptionResponse)
async def get_reception(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
) -> ReceptionResponse:
    buckets = await reception_timeseries(pool, hours)
    return ReceptionResponse(
        hours=hours,
        buckets=[ReceptionBucketResponse(**asdict(bucket)) for bucket in buckets],
    )


@router.get("/rssi-by-distance", response_model=RssiByDistanceResponse)
async def get_rssi_by_distance(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
) -> RssiByDistanceResponse:
    cells = await rssi_by_distance(pool, hours)
    return RssiByDistanceResponse(
        hours=hours,
        distance_bucket_km=DEFAULT_DISTANCE_BUCKET_KM,
        rssi_bucket_db=DEFAULT_RSSI_BUCKET_DB,
        cells=[RssiDistanceCellResponse(**asdict(cell)) for cell in cells],
    )
