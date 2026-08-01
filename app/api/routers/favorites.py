"""GET/POST/DELETE /api/favorites -- this app's first mutating
endpoints.

Every other route in this app is GET-only and unauthenticated
(app/static/js/history.js used to keep favorites purely in
client-side localStorage specifically to avoid becoming the exception).
Milestone JJ of the 2026-08 feature roadmap moves favorites server-side
instead, at the user's explicit choice, because it unblocks server-side
features that need to know what's favorited (a "favorite aircraft seen"
webhook, future badges). This is a deliberate, narrow exception, not a
general shift toward a writable API -- justified by this app being
tailnet-only/single-user by design (see CLAUDE.md), so there's no
multi-user state to corrupt and no auth boundary being papered over.

POST is an idempotent upsert (re-favoriting an already-favorited aircraft
doesn't reset its added_at) and DELETE is an idempotent removal (deleting
an aircraft that isn't favorited is a no-op, not an error) -- both so the
frontend's toggle button never needs to track which state it's already in
before calling.
"""

from __future__ import annotations

import re
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Path, Response

from app.api.dependencies import get_pool
from app.api.schemas import FavoriteEntryResponse, FavoritesResponse
from app.db.queries.favorites import (
    add_favorite,
    aircraft_exists,
    list_favorites,
    remove_favorite,
)

router = APIRouter(prefix="/api", tags=["favorites"])

# Matches the DB's own aircraft_icao_format CHECK constraint, same as
# aircraft_history.py/aircraft_live.py -- duplicated by design (see those
# files) rather than sharing a helper across otherwise-independent routers.
_ICAO_PATTERN = re.compile(r"^~?[0-9a-f]{6}$")


@router.get("/favorites", response_model=FavoritesResponse)
async def get_favorites(pool=Depends(get_pool)) -> FavoritesResponse:
    entries = await list_favorites(pool)
    return FavoritesResponse(
        favorites=[FavoriteEntryResponse(**asdict(entry)) for entry in entries]
    )


@router.post("/favorites/{icao}", response_model=FavoriteEntryResponse, status_code=201)
async def post_favorite(icao: str = Path(...), pool=Depends(get_pool)) -> FavoriteEntryResponse:
    if not _ICAO_PATTERN.match(icao):
        raise HTTPException(status_code=422, detail="invalid icao format")
    if not await aircraft_exists(pool, icao):
        raise HTTPException(status_code=404, detail="aircraft not found")
    entry = await add_favorite(pool, icao)
    return FavoriteEntryResponse(**asdict(entry))


@router.delete("/favorites/{icao}", status_code=204)
async def delete_favorite(icao: str = Path(...), pool=Depends(get_pool)) -> Response:
    if not _ICAO_PATTERN.match(icao):
        raise HTTPException(status_code=422, detail="invalid icao format")
    await remove_favorite(pool, icao)
    return Response(status_code=204)
