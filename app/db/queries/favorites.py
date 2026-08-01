"""Read/write queries backing GET/POST/DELETE /api/favorites -- the app's
first mutating endpoints (see app/api/routers/favorites.py's docstring
for why that's a deliberate, narrow exception here)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class FavoriteEntry:
    icao: str
    added_at: datetime
    last_callsign: str | None
    last_seen_at: datetime


async def list_favorites(pool: asyncpg.Pool) -> list[FavoriteEntry]:
    rows = await pool.fetch(
        "SELECT f.icao, f.added_at, a.last_callsign, a.last_seen_at "
        "FROM favorites f JOIN aircraft a ON a.icao = f.icao "
        "ORDER BY f.added_at DESC",
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [FavoriteEntry(**dict(row)) for row in rows]


async def aircraft_exists(pool: asyncpg.Pool, icao: str) -> bool:
    row = await pool.fetchrow(
        "SELECT 1 FROM aircraft WHERE icao = $1", icao, timeout=QUERY_TIMEOUT_SECONDS
    )
    return row is not None


async def add_favorite(pool: asyncpg.Pool, icao: str) -> FavoriteEntry:
    """Caller must check aircraft_exists() first -- the FK constraint
    would reject an unknown icao anyway, but the route wants to return a
    clean 404 rather than translate a Postgres FK-violation error."""
    row = await pool.fetchrow(
        "INSERT INTO favorites (icao) VALUES ($1) "
        "ON CONFLICT (icao) DO UPDATE SET icao = EXCLUDED.icao "
        "RETURNING icao, added_at",
        icao,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    aircraft_row = await pool.fetchrow(
        "SELECT last_callsign, last_seen_at FROM aircraft WHERE icao = $1",
        icao,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return FavoriteEntry(
        icao=row["icao"],
        added_at=row["added_at"],
        last_callsign=aircraft_row["last_callsign"],
        last_seen_at=aircraft_row["last_seen_at"],
    )


async def remove_favorite(pool: asyncpg.Pool, icao: str) -> None:
    await pool.execute(
        "DELETE FROM favorites WHERE icao = $1", icao, timeout=QUERY_TIMEOUT_SECONDS
    )
