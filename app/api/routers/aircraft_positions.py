"""WS /ws/aircraft-positions -- one shared broadcast of every currently-
live aircraft's position (icao/callsign/lat/lon/altitude/track/speed),
backing the 3D flight globe's default "show everything" view. Unlike
app/api/routers/aircraft_live.py's WS /ws/aircraft/{icao} (one
independent readsb poll per connected client, fine for a single selected
aircraft), showing many aircraft at once would mean many redundant polls
of the same readsb snapshot -- so this uses a single background task,
started/stopped via the app lifespan (app/api/main.py), that polls
READSB_AIRCRAFT_URL once per POLL_INTERVAL_SECONDS by default -- same
cadence the collector and the per-aircraft WS already use -- and fans
the same snapshot out to every connected client. Nothing here is
persisted.

Any connected client may opt into a faster FAST_POLL_INTERVAL_SECONDS
(1s) cadence by sending {"fast": true} over the (otherwise inbound-only)
WebSocket; the broadcaster polls at the fastest cadence any currently-
connected client has requested, reverting to the default once none do.
This is safe to offer as a per-page opt-in because it only affects how
often *this* page re-reads readsb's already-decoded in-memory state --
app/collector/service.py's own poll loop (which controls what actually
gets written to Postgres) is a fully separate process, completely
unaffected by this broadcaster's interval. It's also cheap: a local
aircraft.json fetch measures ~10ms in this deployment's own environment
report, and readsb's aircraft.json genuinely refreshes at roughly 1Hz on
real hardware (confirmed empirically against this deployment: consecutive
1s-apart polls show readsb's own `now`/`messages` fields advancing every
single poll) -- so 1Hz is a meaningful, not wasteful, improvement over
the 5s default.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["aircraft-live"])

FETCH_TIMEOUT_SECONDS = 5.0
FAST_POLL_INTERVAL_SECONDS = 1.0


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

    # Both equipage-dependent (most aircraft omit one or both) -- used
    # client-side to orient the 3D globe's aircraft model (roll = bank
    # angle; vertical rate approximates pitch there, readsb has no pitch
    # field). baro_rate preferred over geom_rate, same precedence
    # app/collector/normalize.py uses for the stored vertical_rate_fpm.
    roll_deg = raw.get("roll")
    if not isinstance(roll_deg, int | float):
        roll_deg = None

    vertical_rate_fpm = raw.get("baro_rate")
    if not isinstance(vertical_rate_fpm, int | float):
        vertical_rate_fpm = raw.get("geom_rate")
    if not isinstance(vertical_rate_fpm, int | float):
        vertical_rate_fpm = None

    return {
        "icao": icao,
        "callsign": callsign or None,
        "lat": lat,
        "lon": lon,
        "altitude_ft": altitude_ft,
        "track_deg": raw.get("track"),
        "ground_speed_kt": raw.get("gs"),
        "roll_deg": roll_deg,
        "vertical_rate_fpm": vertical_rate_fpm,
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
        self._fast_clients: set[WebSocket] = set()
        self._latest: dict = {"aircraft": []}
        self._task: asyncio.Task | None = None

    @property
    def latest(self) -> dict:
        return self._latest

    def register(self, websocket: WebSocket) -> None:
        self._clients.add(websocket)

    def unregister(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        self._fast_clients.discard(websocket)

    def set_fast(self, websocket: WebSocket, enabled: bool) -> None:
        if enabled:
            self._fast_clients.add(websocket)
        else:
            self._fast_clients.discard(websocket)

    @property
    def current_interval(self) -> float:
        """FAST_POLL_INTERVAL_SECONDS while any connected client has opted
        in via set_fast(), otherwise the configured default."""
        return FAST_POLL_INTERVAL_SECONDS if self._fast_clients else self._interval

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
                await asyncio.sleep(self.current_interval)

    async def _broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in list(self._clients):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self._clients.discard(websocket)
            self._fast_clients.discard(websocket)


@router.websocket("/ws/aircraft-positions")
async def aircraft_positions_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    broadcaster: PositionBroadcaster = websocket.app.state.position_broadcaster
    broadcaster.register(websocket)
    try:
        await websocket.send_json(broadcaster.latest)
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except ValueError:
                continue  # malformed client message -- ignore, never drop the connection over it
            if isinstance(message, dict) and "fast" in message:
                broadcaster.set_fast(websocket, bool(message["fast"]))
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("aircraft_positions: stream error")
    finally:
        broadcaster.unregister(websocket)
