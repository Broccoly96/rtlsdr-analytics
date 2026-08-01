"""GET /api/rankings, GET /api/rankings.csv."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_pool
from app.api.schemas import RankingEntryResponse, RankingsResponse
from app.db.queries.rankings import RankingEntry, get_closest, get_farthest

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


def _rankings_csv_rows(
    farthest: list[RankingEntry], closest: list[RankingEntry]
) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["category", "icao", "callsign", "distance_km", "bearing_deg", "altitude_ft", "observed_at"]
    )
    yield buffer.getvalue()
    for category, entries in (("farthest", farthest), ("closest", closest)):
        for entry in entries:
            buffer.seek(0)
            buffer.truncate(0)
            writer.writerow(
                [
                    category,
                    entry.icao,
                    entry.callsign or "",
                    entry.distance_km,
                    entry.bearing_deg,
                    entry.altitude_ft,
                    entry.observed_at.isoformat(),
                ]
            )
            yield buffer.getvalue()


@router.get("/rankings.csv", include_in_schema=False)
async def get_rankings_csv(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=100),
    pool=Depends(get_pool),
) -> StreamingResponse:
    farthest = await get_farthest(pool, hours, limit)
    closest = await get_closest(pool, hours, limit)
    return StreamingResponse(
        _rankings_csv_rows(farthest, closest),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="rankings_{hours}h.csv"'},
    )
