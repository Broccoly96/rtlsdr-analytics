"""GET /api/distribution/* -- hour-of-day traffic pattern and altitude/
speed histograms."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_pool
from app.api.schemas import (
    AltitudeHistogramResponse,
    HistogramBucketResponse,
    HourOfDayEntryResponse,
    HourOfDayResponse,
    SpeedHistogramResponse,
)
from app.db.queries.distribution import altitude_histogram, hour_of_day_unique, speed_histogram

router = APIRouter(prefix="/api/distribution", tags=["distribution"])

DEFAULT_ALTITUDE_BUCKET_FT = 1000
DEFAULT_SPEED_BUCKET_KT = 50


@router.get("/hour-of-day", response_model=HourOfDayResponse)
async def get_hour_of_day(
    days: int = Query(7, ge=1, le=30),
    pool=Depends(get_pool),
) -> HourOfDayResponse:
    entries = await hour_of_day_unique(pool, days)
    return HourOfDayResponse(
        days=days,
        hours=[HourOfDayEntryResponse(**asdict(entry)) for entry in entries],
    )


@router.get("/altitude", response_model=AltitudeHistogramResponse)
async def get_altitude_histogram(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
) -> AltitudeHistogramResponse:
    buckets = await altitude_histogram(pool, hours, DEFAULT_ALTITUDE_BUCKET_FT)
    return AltitudeHistogramResponse(
        hours=hours,
        bucket_ft=DEFAULT_ALTITUDE_BUCKET_FT,
        buckets=[HistogramBucketResponse(**asdict(bucket)) for bucket in buckets],
    )


@router.get("/speed", response_model=SpeedHistogramResponse)
async def get_speed_histogram(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
) -> SpeedHistogramResponse:
    buckets = await speed_histogram(pool, hours, DEFAULT_SPEED_BUCKET_KT)
    return SpeedHistogramResponse(
        hours=hours,
        bucket_kt=DEFAULT_SPEED_BUCKET_KT,
        buckets=[HistogramBucketResponse(**asdict(bucket)) for bucket in buckets],
    )
