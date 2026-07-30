"""WS /ws/aircraft/{icao} -- live pass-through of readsb's current entry
for one aircraft: squawk, NAC/SIL/NIC accuracy fields, FMS-selected
altitude/heading, wind, TAT/OAT, mach, magnetic heading, and other fields
`observations` never stores (see migrations/versions/62c3f8022564 -- the
stored schema is deliberately narrow). Backs the aircraft-detail sidebar
(app/static/js/aircraftinfo.js) and the 3D flight globe
(app/static/globe.html).

CLAUDE.md's "no real-time tracking" stance is about not replacing
tar1090's live map of *everything*; this is a deliberate, narrow
exception for one explicitly-selected aircraft. Same trust boundary and
"never persisted" rule as app/api/routers/rawdata.py's Beast relay --
one independent upstream poll of READSB_AIRCRAFT_URL per connected
browser client, at the same POLL_INTERVAL_SECONDS cadence the collector
already uses (never faster -- readsb's own data doesn't change any
faster than that either).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["aircraft-live"])

FETCH_TIMEOUT_SECONDS = 5.0
# Matches aircraft_history.py's _ICAO_PATTERN (kept local -- a WebSocket
# route can't share FastAPI's HTTPException-based 422 convention, so this
# validates independently before ever touching readsb).
_ICAO_PATTERN = re.compile(r"^~?[0-9a-f]{6}$")

# Fields tar1090's sidebar shows that this app's own `observations` table
# doesn't store. Every aircraft omits most of these (they depend on
# equipage/broadcast capability) -- all optional, never validated/ranged,
# since this is a display-only pass-through, not something this app
# relies on for its own metrics.
_LIVE_FIELDS: tuple[str, ...] = (
    "squawk",
    "alt_baro",
    "alt_geom",
    "gs",
    "ias",
    "tas",
    "mach",
    "track",
    "mag_heading",
    "roll",
    "baro_rate",
    "geom_rate",
    "nav_qnh",
    "nav_altitude_mcp",
    "nav_heading",
    "nic",
    "nic_baro",
    "rc",
    "nac_p",
    "nac_v",
    "sil",
    "sil_type",
    "category",
    "messages",
    "seen",
    "seen_pos",
    "version",
    "wd",
    "ws",
    "oat",
    "tat",
)


def _extract_live_fields(raw: dict) -> dict:
    fields = {name: raw.get(name) for name in _LIVE_FIELDS}
    # readsb represents these as a list of field names sourced via MLAT/
    # TIS-B (e.g. ["altitude"]) rather than a plain boolean -- non-empty
    # means "yes, at least one field came from there".
    fields["mlat"] = bool(raw.get("mlat"))
    fields["tisb"] = bool(raw.get("tisb"))
    return fields


@router.websocket("/ws/aircraft/{icao}")
async def aircraft_live_stream(websocket: WebSocket, icao: str) -> None:
    await websocket.accept()

    if not _ICAO_PATTERN.match(icao):
        with contextlib.suppress(Exception):
            await websocket.send_json({"error": "invalid icao format"})
        await websocket.close()
        return

    settings = websocket.app.state.settings

    try:
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    response = await client.get(
                        settings.readsb_aircraft_url, timeout=FETCH_TIMEOUT_SECONDS
                    )
                    response.raise_for_status()
                    payload = response.json()
                except (httpx.HTTPError, ValueError) as exc:
                    logger.warning("aircraft_live: readsb fetch failed for %s: %s", icao, exc)
                    await websocket.send_json({"icao": icao, "received": False})
                else:
                    aircraft_list = payload.get("aircraft", []) if isinstance(payload, dict) else []
                    match = next((a for a in aircraft_list if a.get("hex") == icao), None)
                    if match is None:
                        await websocket.send_json({"icao": icao, "received": False})
                    else:
                        await websocket.send_json(
                            {"icao": icao, "received": True, **_extract_live_fields(match)}
                        )

                await asyncio.sleep(settings.poll_interval_seconds)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("aircraft_live: stream error for %s", icao)
