"""GET /api/receiver/* -- receiver performance: max range by compass
bearing and altitude band, and message-count/position-rate over time."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse

from app.api.dependencies import get_pool, get_settings
from app.api.schemas import (
    AltitudeBandRangeEntryResponse,
    AltitudeRangeResponse,
    BearingRangeEntryResponse,
    BearingRangeResponse,
    DayNightRangeResponse,
    ReceptionBucketResponse,
    ReceptionDomeCellResponse,
    ReceptionDomeResponse,
    ReceptionResponse,
    RssiByDistanceResponse,
    RssiDistanceCellResponse,
    WeeklyTrendEntryResponse,
    WeeklyTrendResponse,
)
from app.db.queries.receiver import (
    DEFAULT_DISTANCE_BUCKET_KM,
    DEFAULT_DOME_ALTITUDE_BUCKET_FT,
    DEFAULT_RSSI_BUCKET_DB,
    SECTOR_WIDTH_DEG,
    BearingRangeEntry,
    altitude_band_range,
    bearing_range,
    day_night_range,
    reception_dome,
    reception_timeseries,
    rssi_by_distance,
    weekly_trend,
)
from app.domain.basemap import MAX_RADIUS_KM, MIN_RADIUS_KM, get_basemap_png

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


def _bearing_range_csv_rows(entries: list[BearingRangeEntry]) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["sector_center_deg", "max_distance_km", "sample_count"])
    yield buffer.getvalue()
    for entry in entries:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow([entry.sector_center_deg, entry.max_distance_km, entry.sample_count])
        yield buffer.getvalue()


@router.get("/bearing-range.csv", include_in_schema=False)
async def get_bearing_range_csv(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
) -> StreamingResponse:
    entries = await bearing_range(pool, hours)
    return StreamingResponse(
        _bearing_range_csv_rows(entries),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="bearing_range_{hours}h.csv"'},
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


@router.get("/reception-dome", response_model=ReceptionDomeResponse)
async def get_reception_dome(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
) -> ReceptionDomeResponse:
    cells = await reception_dome(pool, hours)
    return ReceptionDomeResponse(
        hours=hours,
        distance_bucket_km=DEFAULT_DISTANCE_BUCKET_KM,
        altitude_bucket_ft=DEFAULT_DOME_ALTITUDE_BUCKET_FT,
        sector_width_deg=SECTOR_WIDTH_DEG,
        cells=[ReceptionDomeCellResponse(**asdict(cell)) for cell in cells],
    )


@router.get("/basemap.png", include_in_schema=False)
async def get_receiver_basemap(
    radius_km: float = Query(..., ge=MIN_RADIUS_KM, le=MAX_RADIUS_KM),
    settings=Depends(get_settings),
) -> Response:
    png_bytes, actual_radius_km = await get_basemap_png(
        settings.receiver_lat, settings.receiver_lon, radius_km
    )
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Basemap-Radius-Km": str(actual_radius_km),
        },
    )


@router.get("/day-night-range", response_model=DayNightRangeResponse)
async def get_day_night_range(
    hours: int = Query(24, ge=1, le=720),
    pool=Depends(get_pool),
    settings=Depends(get_settings),
) -> DayNightRangeResponse:
    result = await day_night_range(pool, hours, settings.display_timezone)
    return DayNightRangeResponse(hours=hours, **asdict(result))


@router.get("/weekly-trend", response_model=WeeklyTrendResponse)
async def get_weekly_trend(
    weeks: int = Query(12, ge=1, le=104),
    pool=Depends(get_pool),
) -> WeeklyTrendResponse:
    entries = await weekly_trend(pool, weeks)
    return WeeklyTrendResponse(
        weeks=weeks,
        trend=[WeeklyTrendEntryResponse(**asdict(entry)) for entry in entries],
    )
