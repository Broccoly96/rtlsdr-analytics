"""Read queries backing /api/status and /health/ready.

Deliberately separate from app/collector/store.py's write-side Store --
the API's read path must not be coupled to the collector's write path
(PLAN.md Milestone C-1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import asyncpg

from app.collector.normalize import (
    POSITION_ACQUIRED_MAX_SEEN_POS_SECONDS,
    RECEIVED_MAX_SEEN_SECONDS,
)

QUERY_TIMEOUT_SECONDS = 5.0

# How old the last *successful* ingestion may be before we consider data
# stale / the service not-ready. Generous relative to the default 5s poll
# interval so a couple of backoff retries don't immediately flip readiness.
INGESTION_STALE_THRESHOLD_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class LatestIngestion:
    checked_at: datetime
    success: bool
    error_code: str | None


async def check_db_alive(pool: asyncpg.Pool) -> bool:
    try:
        await pool.fetchval("SELECT 1", timeout=QUERY_TIMEOUT_SECONDS)
        return True
    except Exception:
        return False


async def get_latest_ingestion(pool: asyncpg.Pool) -> LatestIngestion | None:
    row = await pool.fetchrow(
        "SELECT checked_at, success, error_code FROM ingestion_status "
        "ORDER BY checked_at DESC LIMIT 1",
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    if row is None:
        return None
    return LatestIngestion(row["checked_at"], row["success"], row["error_code"])


async def get_current_counts(pool: asyncpg.Pool) -> tuple[int, int]:
    """Returns (active_aircraft_count, position_aircraft_count), using the
    same freshness thresholds as the collector's normalize.py so these
    match the "currently received" / "position acquired" definitions
    exactly (CLAUDE.md's metric definitions)."""
    active = await pool.fetchval(
        "SELECT count(*) FROM aircraft WHERE last_seen_at >= now() - ($1 * interval '1 second')",
        RECEIVED_MAX_SEEN_SECONDS,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    position = await pool.fetchval(
        "SELECT count(DISTINCT icao) FROM observations "
        "WHERE observed_at >= now() - ($1 * interval '1 second')",
        POSITION_ACQUIRED_MAX_SEEN_POS_SECONDS,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return active, position
