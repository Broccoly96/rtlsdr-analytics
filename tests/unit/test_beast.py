from __future__ import annotations

from app.domain.beast import ESC, BeastFrame, decode_message, parse_beast_frames


def _encode_frame(msg_type: int, timestamp: bytes, signal: int, message: bytes) -> bytes:
    """Test-only encoder (inverse of parse_beast_frames) so fixtures are
    built the same way a real Beast stream would produce them, including
    byte-stuffing any literal 0x1A in the timestamp/signal/message."""
    raw = timestamp + bytes([signal]) + message
    stuffed = bytearray()
    for b in raw:
        stuffed.append(b)
        if b == ESC:
            stuffed.append(ESC)
    return bytes([ESC, msg_type]) + bytes(stuffed)


def _df17_message(icao24: bytes, tc: int) -> bytes:
    """A syntactically-shaped (not CRC-valid -- decode_message never
    checks CRC, matching its documented "simple decode" scope) 14-byte
    Mode-S long message: DF=17, CA=5, the given ICAO24, and an ME field
    whose first 5 bits are the given type code."""
    first_byte = (17 << 3) | 5
    me_first_byte = tc << 3
    return bytes([first_byte]) + icao24 + bytes([me_first_byte]) + bytes(9)


def test_parse_single_mode_s_long_frame():
    message = _df17_message(bytes.fromhex("aabbcc"), tc=11)
    raw = _encode_frame(0x33, bytes(6), signal=200, message=message)

    frames, leftover = parse_beast_frames(raw)

    assert leftover == b""
    assert frames == [BeastFrame("mode_s_long", 200, message)]


def test_parse_handles_byte_stuffing():
    # A message that itself contains a literal 0x1A byte partway through.
    message = bytes([17 << 3 | 5]) + b"\xaa\x1a\xcc" + bytes(10)
    raw = _encode_frame(0x33, bytes(6), signal=10, message=message)

    frames, leftover = parse_beast_frames(raw)

    assert leftover == b""
    assert len(frames) == 1
    assert frames[0].message == message


def test_parse_multiple_frames_in_one_buffer():
    msg_a = _df17_message(bytes.fromhex("aaaaaa"), tc=1)
    msg_b = _df17_message(bytes.fromhex("bbbbbb"), tc=9)
    raw = _encode_frame(0x33, bytes(6), 1, msg_a) + _encode_frame(0x33, bytes(6), 2, msg_b)

    frames, leftover = parse_beast_frames(raw)

    assert leftover == b""
    assert [f.message for f in frames] == [msg_a, msg_b]


def test_parse_handles_frame_split_across_reads():
    message = _df17_message(bytes.fromhex("cccccc"), tc=5)
    raw = _encode_frame(0x33, bytes(6), 42, message)
    split_at = len(raw) - 5

    frames1, leftover1 = parse_beast_frames(raw[:split_at])
    assert frames1 == []
    assert leftover1 == raw[:split_at]

    frames2, leftover2 = parse_beast_frames(leftover1 + raw[split_at:])
    assert leftover2 == b""
    assert frames2 == [BeastFrame("mode_s_long", 42, message)]


def test_parse_skips_unknown_frame_type_and_resyncs():
    known = _encode_frame(0x32, bytes(6), 1, bytes(7))
    unknown = bytes([ESC, 0x99])  # not a recognized message type
    raw = unknown + known

    frames, leftover = parse_beast_frames(raw)

    assert leftover == b""
    assert len(frames) == 1
    assert frames[0].frame_type == "mode_s_short"


def test_parse_skips_garbage_bytes_before_first_frame():
    known = _encode_frame(0x31, bytes(6), 1, bytes(2))
    raw = b"\x00\xff\x42" + known

    frames, leftover = parse_beast_frames(raw)

    assert leftover == b""
    assert len(frames) == 1


def test_parse_returns_leftover_for_incomplete_final_frame():
    complete = _encode_frame(0x32, bytes(6), 1, bytes(7))
    incomplete = bytes([ESC, 0x33]) + bytes(5)  # header + partial payload only
    raw = complete + incomplete

    frames, leftover = parse_beast_frames(raw)

    assert len(frames) == 1
    assert leftover == incomplete


def test_decode_message_extracts_df17_icao_ca_and_tc_category():
    message = _df17_message(bytes.fromhex("a1b2c3"), tc=11)

    decoded = decode_message(message)

    assert decoded.df == 17
    assert decoded.icao24 == "a1b2c3"
    assert decoded.ca == 5
    assert decoded.tc == 11
    assert decoded.tc_label == "気圧高度位置 (airborne position, baro altitude)"


def test_decode_message_identification_tc_range():
    message = _df17_message(bytes.fromhex("a1b2c3"), tc=4)
    assert decode_message(message).tc_label == "識別 (aircraft identification)"


def test_decode_message_velocity_tc_range():
    message = _df17_message(bytes.fromhex("a1b2c3"), tc=19)
    assert decode_message(message).tc_label == "対気速度 (airborne velocity)"


def test_decode_message_unassigned_tc_has_no_label():
    message = _df17_message(bytes.fromhex("a1b2c3"), tc=0)
    decoded = decode_message(message)
    assert decoded.tc == 0
    assert decoded.tc_label is None


def test_decode_message_df11_extracts_icao_without_tc():
    first_byte = (11 << 3) | 3
    message = bytes([first_byte]) + bytes.fromhex("112233") + bytes(3)

    decoded = decode_message(message)

    assert decoded.df == 11
    assert decoded.icao24 == "112233"
    assert decoded.ca == 3
    assert decoded.tc is None
    assert decoded.tc_label is None


def test_decode_message_unknown_df_has_no_icao():
    # DF28 isn't one of the DFs that place ICAO24 at bytes 1-3.
    message = bytes([28 << 3]) + bytes(6)
    decoded = decode_message(message)
    assert decoded.df == 28
    assert decoded.icao24 is None
    assert decoded.ca is None


def test_decode_message_empty_returns_none():
    assert decode_message(b"") is None
