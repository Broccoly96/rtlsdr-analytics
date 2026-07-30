"""Unit tests for app.api.routers.rawdata's one piece of non-framework
logic (_frame_to_message). The route itself (WebSocket accept, TCP
connect, read loop) is framework boilerplate around this and
app.domain.beast (already covered by tests/unit/test_beast.py, including
against real captured Beast traffic) -- verified live against the real
deployment instead of a mocked harness, since httpx (this project's test
client) has no WebSocket support and standing up a Postgres-backed +
mocked-TCP + WebSocket test double for a thin relay wouldn't be
proportionate to what it'd actually catch.
"""

from __future__ import annotations

from app.api.routers.rawdata import _frame_to_message
from app.domain.beast import BeastFrame


def test_mode_ac_frame_has_no_decoded_field():
    frame = BeastFrame("mode_ac", signal=50, message=b"\x12\x34")
    payload = _frame_to_message(frame)

    assert payload["frame_type"] == "mode_ac"
    assert payload["signal"] == 50
    assert payload["message_hex"] == "1234"
    assert "decoded" not in payload


def test_mode_s_long_frame_includes_decoded_field():
    message = bytes([17 << 3 | 5]) + bytes.fromhex("aabbcc") + bytes([11 << 3]) + bytes(9)
    frame = BeastFrame("mode_s_long", signal=100, message=message)

    payload = _frame_to_message(frame)

    assert payload["message_hex"] == message.hex()
    assert payload["decoded"]["df"] == 17
    assert payload["decoded"]["icao24"] == "aabbcc"
    assert payload["decoded"]["tc"] == 11


def test_mode_s_short_frame_includes_decoded_field():
    first_byte = (11 << 3) | 3
    message = bytes([first_byte]) + bytes.fromhex("112233") + bytes(3)
    frame = BeastFrame("mode_s_short", signal=10, message=message)

    payload = _frame_to_message(frame)

    assert payload["decoded"]["df"] == 11
    assert payload["decoded"]["icao24"] == "112233"


def test_empty_message_omits_decoded_field():
    frame = BeastFrame("mode_s_short", signal=0, message=b"")
    payload = _frame_to_message(frame)
    assert "decoded" not in payload
