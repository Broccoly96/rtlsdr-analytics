"""GET /api/aircraft/recent, GET /api/aircraft/nationalities."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_pool, get_settings
from app.api.schemas import (
    ArchiveEntryResponse,
    ArchiveResponse,
    NationalityCountResponse,
    NationalitySummaryResponse,
    OnThisDayEntryResponse,
    OnThisDayResponse,
    OnThisDayYearResponse,
    RecentAircraftResponse,
)
from app.db.queries.aircraft import (
    get_archive_page,
    get_archive_total,
    get_nationality_summary,
    get_on_this_day,
    get_recent_aircraft,
)
from app.domain.daytime import today_in_tz

_ARCHIVE_SORT_VALUES = {
    "last_seen_at",
    "first_seen_at",
    "days_observed",
    "total_pass_count",
    "icao",
}

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


@router.get("/aircraft/archive", response_model=ArchiveResponse)
async def get_archive(
    q: str | None = Query(None, max_length=20),
    sort: str = Query("last_seen_at"),
    descending: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_pool),
) -> ArchiveResponse:
    if sort not in _ARCHIVE_SORT_VALUES:
        sort = "last_seen_at"
    query = q.strip() if q and q.strip() else None
    total = await get_archive_total(pool, query)
    rows = await get_archive_page(
        pool, query=query, sort=sort, descending=descending, limit=limit, offset=offset
    )
    return ArchiveResponse(
        total=total,
        limit=limit,
        offset=offset,
        sort=sort,
        descending=descending,
        aircraft=[ArchiveEntryResponse(**asdict(row)) for row in rows],
    )


@router.get("/aircraft/on-this-day", response_model=OnThisDayResponse)
async def get_on_this_day_endpoint(
    pool=Depends(get_pool), settings=Depends(get_settings)
) -> OnThisDayResponse:
    today = today_in_tz(settings.display_timezone)
    years = await get_on_this_day(pool, today.month, today.day, today.year)
    return OnThisDayResponse(
        month=today.month,
        day=today.day,
        years=[
            OnThisDayYearResponse(
                year=year.year,
                aircraft=[OnThisDayEntryResponse(**asdict(entry)) for entry in year.aircraft],
            )
            for year in years
        ],
    )


@router.get("/aircraft/nationalities", response_model=NationalitySummaryResponse)
async def get_nationalities(pool=Depends(get_pool)) -> NationalitySummaryResponse:
    rows = await get_nationality_summary(pool)
    return NationalitySummaryResponse(
        countries=[NationalityCountResponse(**asdict(row)) for row in rows]
    )
