"""GET /api/traffic, GET /api/traffic.csv, GET /api/traffic/daily,
GET /api/traffic/daily-summary."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import asdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_pool, get_settings
from app.api.schemas import (
    DailyTrafficSummaryResponse,
    TrafficBucketResponse,
    TrafficDailyResponse,
    TrafficResponse,
)
from app.db.queries.period import compute_daily_summary, get_traffic_day, list_traffic_days
from app.db.queries.traffic import TrafficBucket, get_traffic
from app.domain.daytime import day_bounds_utc, today_in_tz, yesterday_in_tz

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


def _traffic_csv_rows(buckets: list[TrafficBucket]) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["bucket_at", "active_aircraft_count", "position_aircraft_count", "message_count_delta"]
    )
    yield buffer.getvalue()
    for bucket in buckets:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(
            [
                bucket.bucket_at.isoformat(),
                bucket.active_aircraft_count,
                bucket.position_aircraft_count,
                bucket.message_count_delta,
            ]
        )
        yield buffer.getvalue()


@router.get("/traffic.csv", include_in_schema=False)
async def get_traffic_csv(
    hours: int = Query(24, ge=1, le=168),
    pool=Depends(get_pool),
) -> StreamingResponse:
    buckets, _ = await get_traffic(pool, hours)
    return StreamingResponse(
        _traffic_csv_rows(buckets),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="traffic_{hours}h.csv"'},
    )


@router.get("/traffic/daily", response_model=TrafficDailyResponse)
async def get_traffic_daily(
    days: int = Query(30, ge=1, le=365),
    pool=Depends(get_pool),
    settings=Depends(get_settings),
) -> TrafficDailyResponse:
    # Ends at yesterday, not today: traffic_day only ever holds *finished*
    # days (the rollup job runs the following day) -- including today
    # would always render as a misleading zero-filled gap, not "no
    # traffic yet".
    end_day = yesterday_in_tz(settings.display_timezone)
    start_day = end_day - timedelta(days=days - 1)
    summaries = await list_traffic_days(pool, start_day, end_day)
    return TrafficDailyResponse(
        days=days,
        daily=[DailyTrafficSummaryResponse(**asdict(summary)) for summary in summaries],
    )


@router.get("/traffic/daily-summary", response_model=DailyTrafficSummaryResponse)
async def get_traffic_daily_summary(
    day: date | None = Query(None),
    pool=Depends(get_pool),
    settings=Depends(get_settings),
) -> DailyTrafficSummaryResponse:
    today = today_in_tz(settings.display_timezone)
    target_day = day if day is not None else today
    if target_day > today:
        raise HTTPException(status_code=422, detail="day cannot be in the future")

    if target_day == today:
        summary = None
    else:
        summary = await get_traffic_day(pool, target_day)

    if summary is None:
        # Either it's today (never rolled up, always computed live) or a
        # past day the rollup job hasn't reached yet -- observations for
        # recent days still exist within RAW_RETENTION_DAYS, so compute
        # live rather than 404.
        start_utc, end_utc = day_bounds_utc(target_day, settings.display_timezone)
        summary = await compute_daily_summary(pool, target_day, start_utc, end_utc)

    return DailyTrafficSummaryResponse(**asdict(summary))
