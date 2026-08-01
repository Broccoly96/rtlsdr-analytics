"""GET /api/weather/metar -- optional server-side proxy to
aviationweather.gov's free, keyless METAR API (Milestone QQ), for
correlating reception range/RSSI with weather on /static/receiver.html.

Same "server-side proxy with a descriptive User-Agent" shape as
aircraft_history.py's Planespotters photo proxy: aviationweather.gov is a
US government service with no published User-Agent requirement, but this
app sends one anyway (consistent, harmless, and good citizenship). Unlike
the photo proxy, this one has an in-process TTL cache from day one (METAR
reports are only issued roughly hourly, so re-fetching more often than
that is pure waste) -- same in-memory-only, cleared-on-restart cache
shape as aircraft_history.py's photo cache (Milestone PP).

Deliberately never 404s or errors when unconfigured or when the upstream
is unreachable/malformed -- returns an all-None response instead, the
same fail-soft rule as every other third-party proxy in this app.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends

from app.api.dependencies import get_settings
from app.api.schemas import MetarResponse
from app.version import get_user_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/weather", tags=["weather"])

AVIATIONWEATHER_URL = "https://aviationweather.gov/api/data/metar"
AVIATIONWEATHER_TIMEOUT_SECONDS = 6.0
METAR_CACHE_TTL_SECONDS = 10 * 60

_EMPTY_METAR = MetarResponse(
    station_icao=None,
    raw_text=None,
    observed_at=None,
    temperature_c=None,
    wind_dir_deg=None,
    wind_speed_kt=None,
    visibility_statute_mi=None,
    altimeter_in_hg=None,
    flight_category=None,
)

_metar_cache: tuple[float, MetarResponse] | None = None


async def _fetch_metar(
    station_icao: str, *, client: httpx.AsyncClient | None = None
) -> MetarResponse:
    """Split out from the route for test injection, same pattern as
    aircraft_history.py's _fetch_photo."""
    owns_client = client is None
    http_client = client or httpx.AsyncClient(headers={"User-Agent": get_user_agent()})
    try:
        response = await http_client.get(
            AVIATIONWEATHER_URL,
            params={"ids": station_icao, "format": "json", "taf": "false"},
            timeout=AVIATIONWEATHER_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            return _EMPTY_METAR
        data = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("METAR lookup failed for %s", station_icao, exc_info=True)
        return _EMPTY_METAR
    finally:
        if owns_client:
            await http_client.aclose()

    if not isinstance(data, list) or not data:
        return _EMPTY_METAR
    report = data[0]
    if not isinstance(report, dict):
        return _EMPTY_METAR

    obs_time_epoch = report.get("obsTime")
    observed_at = None
    if isinstance(obs_time_epoch, int | float):
        observed_at = datetime.fromtimestamp(obs_time_epoch, tz=UTC)

    return MetarResponse(
        station_icao=report.get("icaoId") or station_icao,
        raw_text=report.get("rawOb"),
        observed_at=observed_at,
        temperature_c=report.get("temp"),
        wind_dir_deg=report.get("wdir") if isinstance(report.get("wdir"), int | float) else None,
        wind_speed_kt=report.get("wspd"),
        visibility_statute_mi=report.get("visib")
        if isinstance(report.get("visib"), int | float)
        else None,
        altimeter_in_hg=report.get("altim"),
        flight_category=report.get("fltCat"),
    )


@router.get("/metar", response_model=MetarResponse)
async def get_metar(settings=Depends(get_settings)) -> MetarResponse:
    global _metar_cache
    if not settings.metar_station_icao:
        return _EMPTY_METAR

    if _metar_cache is not None and time.monotonic() - _metar_cache[0] < METAR_CACHE_TTL_SECONDS:
        return _metar_cache[1]

    result = await _fetch_metar(settings.metar_station_icao)
    _metar_cache = (time.monotonic(), result)
    return result
