"""GET /api/config -- non-secret UI configuration the frontend needs at
load time (map style URL, display timezone, receiver-marker privacy
controls). Never includes DATABASE_URL, READSB_AIRCRAFT_URL, or receiver
coordinates.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_settings
from app.api.schemas import AltitudeBandResponse, ConfigResponse, NationalityBlockResponse
from app.domain.bands import ALTITUDE_BANDS
from app.domain.nationality import NATIONALITY_BLOCKS
from app.version import get_git_revision, get_version

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=ConfigResponse)
async def get_config(settings=Depends(get_settings)) -> ConfigResponse:
    return ConfigResponse(
        map_style_url=settings.map_style_url,
        map_show_receiver_marker=settings.map_show_receiver_marker,
        map_receiver_marker_precision=settings.map_receiver_marker_precision,
        display_timezone=settings.display_timezone,
        altitude_bands=[
            AltitudeBandResponse(key=b.key, label=b.label_ja, max_ft=b.max_ft, color=b.color)
            for b in ALTITUDE_BANDS
        ],
        nationality_blocks=[
            NationalityBlockResponse(start=b.start, end=b.end, code=b.code, name=b.name)
            for b in NATIONALITY_BLOCKS
        ],
        version=get_version(),
        git_revision=get_git_revision(),
    )
