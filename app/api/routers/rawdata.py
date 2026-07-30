"""WS /ws/rawdata -- live, display-only relay of readsb's raw Beast-format
TCP stream, decoded with app/domain/beast.py's simple (not full) decoder.

Read-only client of an already-listening port on the existing readsb
instance (confirmed open independently of this app -- never starts,
stops, or reconfigures readsb itself, per CLAUDE.md's "never touch
readsb" rule). One upstream Beast connection per connected browser client
-- Beast servers are designed for multiple simultaneous readers (that's
their whole purpose; tar1090 and other tools already do this), and this
is a low-traffic personal feature, so a shared fan-out hub would be
unwarranted complexity.

Nothing here is ever persisted: no DB writes, no server-side buffering
beyond what's needed to de-stuff one in-flight frame. If the browser
can't keep up, backpressure naturally propagates through the WebSocket
send call to the upstream socket read -- no unbounded queue to overflow.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.domain.beast import BeastFrame, decode_message, parse_beast_frames

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rawdata"])

CONNECT_TIMEOUT_SECONDS = 5.0
READ_CHUNK_BYTES = 4096
# A single frame can never legitimately need more than ~40 raw bytes
# (worst case: a 21-byte mode_s_long frame, fully byte-stuffed). Anything
# beyond that sitting unconsumed means parse_beast_frames is stuck on
# garbage, not a real in-flight frame -- drop it and resync rather than
# growing forever.
MAX_LEFTOVER_BYTES = 256


def _frame_to_message(frame: BeastFrame) -> dict:
    payload: dict = {
        "frame_type": frame.frame_type,
        "signal": frame.signal,
        "message_hex": frame.message.hex(),
    }
    if frame.frame_type in ("mode_s_short", "mode_s_long"):
        decoded = decode_message(frame.message)
        if decoded is not None:
            payload["decoded"] = asdict(decoded)
    return payload


@router.websocket("/ws/rawdata")
async def rawdata_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    settings = websocket.app.state.settings
    host, port = settings.readsb_beast_host, settings.readsb_beast_port

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT_SECONDS
        )
    except Exception as exc:
        logger.warning("rawdata: failed to connect to Beast stream %s:%s: %s", host, port, exc)
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {"error": f"Beastストリーム({host}:{port})への接続に失敗しました"}
            )
        await websocket.close()
        return

    buffer = b""
    try:
        while True:
            chunk = await reader.read(READ_CHUNK_BYTES)
            if not chunk:
                break
            buffer += chunk
            frames, buffer = parse_beast_frames(buffer)
            if len(buffer) > MAX_LEFTOVER_BYTES:
                buffer = b""
            for frame in frames:
                await websocket.send_json(_frame_to_message(frame))
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("rawdata: stream error")
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
