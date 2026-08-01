"""GET /api/badges -- recomputed fresh on every call from permanent tables
(app/db/queries/badges.py), not stored anywhere. Deliberately GET-only:
adding a "you earned this on <date>" record would need a write path, and
the whole point of computing earned/locked from current data each time is
that it doesn't need one -- see app/domain/badges.py's docstring for the
full rationale (favorites' mutating endpoints, Milestone JJ, are meant to
stay the one narrow exception, not a precedent).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_pool
from app.api.schemas import BadgeResponse, BadgesResponse
from app.db.queries.badges import get_badge_stats
from app.domain.badges import BADGES

router = APIRouter(prefix="/api", tags=["badges"])


@router.get("/badges", response_model=BadgesResponse)
async def get_badges(pool=Depends(get_pool)) -> BadgesResponse:
    stats = await get_badge_stats(pool)
    return BadgesResponse(
        badges=[
            BadgeResponse(
                key=badge.key,
                icon=badge.icon,
                earned=badge.is_earned(stats),
                progress=badge.progress(stats),
            )
            for badge in BADGES
        ]
    )
