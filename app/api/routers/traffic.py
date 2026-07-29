"""GET /api/traffic, GET /api/traffic.csv."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_pool
from app.api.schemas import TrafficBucketResponse, TrafficResponse
from app.db.queries.traffic import TrafficBucket, get_traffic

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
