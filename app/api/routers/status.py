"""GET /api/status."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.dependencies import get_pool, get_settings
from app.api.schemas import StatusResponse
from app.db.queries.status import (
    INGESTION_STALE_THRESHOLD_SECONDS,
    get_current_counts,
    get_latest_ingestion,
)

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status", response_model=StatusResponse)
async def get_status(pool=Depends(get_pool), settings=Depends(get_settings)) -> StatusResponse:
    now = datetime.now(UTC)
    latest = await get_latest_ingestion(pool)
    active_count, position_count = await get_current_counts(pool)

    if latest is None:
        ingestion_state = "no_data"
        data_age_seconds = None
    else:
        data_age_seconds = (now - latest.checked_at).total_seconds()
        if not latest.success:
            ingestion_state = "error"
        elif data_age_seconds > INGESTION_STALE_THRESHOLD_SECONDS:
            ingestion_state = "stale"
        else:
            ingestion_state = "ok"

    # Never report current-looking counts alongside a stale/error/no_data
    # state (PLAN.md C-3: "staleデータを正常表示しない").
    if ingestion_state != "ok":
        active_count = 0
        position_count = 0

    return StatusResponse(
        generated_at=now,
        last_ingestion_at=latest.checked_at if latest else None,
        ingestion_state=ingestion_state,
        active_aircraft_count=active_count,
        position_aircraft_count=position_count,
        data_age_seconds=data_age_seconds,
        display_timezone=settings.display_timezone,
    )
