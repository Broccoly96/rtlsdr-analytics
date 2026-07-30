"""WS /ws/aircraft-positions -- one shared broadcast of every currently-
live aircraft's position (icao/callsign/lat/lon/altitude/track/speed),
backing the 3D flight globe's default "show everything" view (Milestone
Z). Unlike app/api/routers/aircraft_live.py's WS /ws/aircraft/{icao}
(one independent readsb poll per connected client, fine for a single
selected aircraft), showing many aircraft at once would mean many
redundant polls of the same readsb snapshot -- so this uses a single
background task, started/stopped via the app lifespan
(app/api/main.py), that polls READSB_AIRCRAFT_URL once per
POLL_INTERVAL_SECONDS -- same cadence the collector and the per-aircraft
WS already use, never faster -- and fans the same snapshot out to every
connected client. Nothing here is persisted.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["aircraft-live"])

FETCH_TIMEOUT_SECONDS = 5.0


def extract_position(raw: dict) -> dict | None:
    """None if `raw` has no usable icao or position -- readsb's aircraft.json
    entries without a position lock (no lat/lon yet) aren't useful for a
    map of live positions."""
    icao = raw.get("hex")
    lat = raw.get("lat")
    lon = raw.get("lon")
    if not icao or lat is None or lon is None:
        return None

    altitude_ft = raw.get("alt_geom")
    if not isinstance(altitude_ft, int | float):
        altitude_ft = raw.get("alt_baro")
    if not isinstance(altitude_ft, int | float):
        altitude_ft = None

    callsign = raw.get("flight")
    callsign = callsign.strip() if isinstance(callsign, str) else None

    return {
        "icao": icao,
        "callsign": callsign or None,
        "lat": lat,
        "lon": lon,
        "altitude_ft": altitude_ft,
        "track_deg": raw.get("track"),
        "ground_speed_kt": raw.get("gs"),
    }


class PositionBroadcaster:
    """Owns the single background poll task and the set of connected
    WebSocket clients. Constructed once in app/api/main.py's lifespan and
    stored on app.state so the WS route handler (which gets a fresh
    `websocket` per connection, not a shared object) can reach it."""

    def __init__(self, readsb_aircraft_url: str, poll_interval_seconds: float) -> None:
        self._url = readsb_aircraft_url
        self._interval = poll_interval_seconds
        self._clients: set[WebSocket] = set()
        self._latest: dict = {"aircraft": []}
        self._task: asyncio.Task | None = None

    @property
    def latest(self) -> dict:
        return self._latest

    def register(self, websocket: WebSocket) -> None:
        self._clients.add(websocket)

    def unregister(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task

    async def _run(self) -> None:
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    response = await client.get(self._url, timeout=FETCH_TIMEOUT_SECONDS)
                    response.raise_for_status()
                    payload = response.json()
                    aircraft_list = payload.get("aircraft", []) if isinstance(payload, dict) else []
                    positions = [
                        p for p in (extract_position(a) for a in aircraft_list) if p is not None
                    ]
                    self._latest = {"aircraft": positions}
                except asyncio.CancelledError:
                    raise
                except (httpx.HTTPError, ValueError) as exc:
                    logger.warning("aircraft_positions: readsb fetch failed: %s", exc)
                    self._latest = {"aircraft": [], "error": True}
                except Exception:
                    logger.exception("aircraft_positions: unexpected broadcaster error")

                await self._broadcast(self._latest)
                await asyncio.sleep(self._interval)

    async def _broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in list(self._clients):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self._clients.discard(websocket)


@router.websocket("/ws/aircraft-positions")
async def aircraft_positions_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    broadcaster: PositionBroadcaster = websocket.app.state.position_broadcaster
    broadcaster.register(websocket)
    try:
        await websocket.send_json(broadcaster.latest)
        while True:
            # Server-push only, no client->server messages expected --
            # this just blocks until the client disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("aircraft_positions: stream error")
    finally:
        broadcaster.unregister(websocket)
