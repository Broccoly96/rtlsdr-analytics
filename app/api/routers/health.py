"""GET /health/live, GET /health/ready.

`live` must return 200 as long as the web process can respond at all -- a
transient DB or readsb outage must not fail liveness (that's what
readiness is for). `ready` checks DB connectivity and ingestion freshness,
and never includes secrets or the readsb URL in its response.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_pool
from app.api.schemas import LiveResponse, ReadyResponse
from app.db.queries.status import (
    INGESTION_STALE_THRESHOLD_SECONDS,
    check_db_alive,
    get_latest_ingestion,
)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    return LiveResponse()


@router.get("/ready", response_model=ReadyResponse)
async def ready(pool=Depends(get_pool)) -> ReadyResponse:
    if not await check_db_alive(pool):
        raise HTTPException(503, "database is not reachable")

    latest = await get_latest_ingestion(pool)
    if latest is None:
        raise HTTPException(503, "no successful data ingestion yet")
    if not latest.success:
        raise HTTPException(503, "most recent ingestion attempt failed")

    age_seconds = (datetime.now(UTC) - latest.checked_at).total_seconds()
    if age_seconds > INGESTION_STALE_THRESHOLD_SECONDS:
        raise HTTPException(503, "ingested data is stale")

    return ReadyResponse()
