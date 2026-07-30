"""Minimal Beast binary-format frame parsing and a *simple* Mode-S decode
-- downlink format (DF), ICAO24 address, capability (CA), and, for ADS-B
extended squitters (DF17/18), the ME-field type-code (TC) category label.

Deliberately not a full decoder: no CPR position decode, no altitude/
velocity/identification field decode. readsb already does that correctly
(it's what feeds this whole app's `observations` table) and re-implementing
it here would be significant, error-prone duplication for a feature whose
purpose is letting someone see and learn the raw frame structure, not
replace readsb. See app/api/routers/rawdata.py for the live WebSocket
relay this backs, and CLAUDE.md for why this exists despite the project's
original "no raw Beast storage/decoder" scope: display-only, never
persisted, added at the user's explicit request.

Beast format reference (public, widely documented -- e.g. dump1090's
README-beast.md): each frame is `0x1A <type> <6-byte timestamp>
<1-byte signal> <message bytes>`, with any literal 0x1A byte within the
timestamp/signal/message fields escaped as 0x1A 0x1A. Type '1' = Mode A/C
(2-byte message), '2' = Mode-S short (7-byte message), '3' = Mode-S long
(14-byte message).
"""

from __future__ import annotations

from dataclasses import dataclass

ESC = 0x1A

_MESSAGE_LENGTH_BY_TYPE: dict[int, int] = {
    0x31: 2,  # Mode A/C
    0x32: 7,  # Mode-S short
    0x33: 14,  # Mode-S long
}
_FRAME_TYPE_LABELS: dict[int, str] = {
    0x31: "mode_ac",
    0x32: "mode_s_short",
    0x33: "mode_s_long",
}


@dataclass(frozen=True, slots=True)
class BeastFrame:
    frame_type: str  # "mode_ac" | "mode_s_short" | "mode_s_long"
    signal: int
    message: bytes


def parse_beast_frames(buffer: bytes) -> tuple[list[BeastFrame], bytes]:
    """Parses as many complete frames as `buffer` contains, returning
    (frames, leftover_unconsumed_bytes) -- the leftover is meant to be
    prepended to the next chunk read from the socket, since a frame can
    arrive split across TCP reads. Unrecognized bytes (resync noise, an
    unknown frame type) are skipped, never raise."""
    frames: list[BeastFrame] = []
    i = 0
    n = len(buffer)

    while i < n:
        if buffer[i] != ESC:
            i += 1
            continue
        if i + 1 >= n:
            break  # incomplete: need more data to even see the type byte

        msg_type = buffer[i + 1]
        payload_len = _MESSAGE_LENGTH_BY_TYPE.get(msg_type)
        if payload_len is None:
            i += 2  # unknown/unsupported type -- skip header, resync
            continue

        field_len = 6 + 1 + payload_len  # timestamp + signal + message, unstuffed
        collected = bytearray()
        j = i + 2
        while len(collected) < field_len and j < n:
            b = buffer[j]
            if b == ESC:
                if j + 1 < n and buffer[j + 1] == ESC:
                    collected.append(ESC)
                    j += 2
                else:
                    # 0x1A not followed by 0x1A mid-frame means either the
                    # next frame started early (truncated/corrupt frame) or
                    # we need more data -- either way, this frame isn't
                    # decodable yet from what we have.
                    break
            else:
                collected.append(b)
                j += 1

        if len(collected) < field_len:
            break  # incomplete frame -- wait for more data from the socket

        signal = collected[6]
        message = bytes(collected[7:])
        frames.append(BeastFrame(_FRAME_TYPE_LABELS[msg_type], signal, message))
        i = j

    return frames, buffer[i:]


# ADS-B (DF17/18) ME-field type-code ranges -> a short category label.
# Public ADS-B spec knowledge (ICAO Annex 10 Vol IV / RTCA DO-260B).
_TC_CATEGORY_RANGES: tuple[tuple[range, str], ...] = (
    (range(1, 5), "識別 (aircraft identification)"),
    (range(5, 9), "地上位置 (surface position)"),
    (range(9, 19), "気圧高度位置 (airborne position, baro altitude)"),
    (range(19, 20), "対気速度 (airborne velocity)"),
    (range(20, 23), "GNSS高度位置 (airborne position, GNSS altitude)"),
    (range(23, 28), "予約/テスト (reserved/test)"),
    (range(28, 29), "航空機状態 (aircraft status)"),
    (range(29, 30), "目標状態 (target state and status)"),
    (range(31, 32), "運用状態 (aircraft operation status)"),
)

_DF_LABELS: dict[int, str] = {
    0: "短距離空対空監視 (short air-air surveillance)",
    4: "高度応答 (surveillance altitude reply)",
    5: "識別応答 (surveillance identity reply)",
    11: "オールコール応答 (all-call reply)",
    16: "長距離空対空監視 (long air-air surveillance)",
    17: "ADS-B (extended squitter)",
    18: "TIS-B/ADS-R (extended squitter)",
    19: "軍用拡張スキッター (military extended squitter)",
    20: "高度応答+Comm-B (Comm-B altitude reply)",
    21: "識別応答+Comm-B (Comm-B identity reply)",
    24: "拡張長メッセージ (Comm-D extended length)",
}


def _tc_category(tc: int) -> str | None:
    for tc_range, label in _TC_CATEGORY_RANGES:
        if tc in tc_range:
            return label
    return None


@dataclass(frozen=True, slots=True)
class DecodedMessage:
    df: int
    df_label: str
    icao24: str | None
    ca: int | None
    tc: int | None
    tc_label: str | None


def decode_message(message: bytes) -> DecodedMessage | None:
    """Simple decode only -- see module docstring. None if `message` is
    too short to even contain a DF (shouldn't happen for mode_s_short/long
    frames from parse_beast_frames, but Mode A/C messages have no DF at
    all and are never passed here)."""
    if len(message) < 1:
        return None

    df = message[0] >> 3
    df_label = _DF_LABELS.get(df, f"DF{df}")

    icao24: str | None = None
    ca: int | None = None
    if df in (0, 4, 5, 11, 16, 17, 18, 20, 21) and len(message) >= 4:
        # These DFs all place the ICAO24 address at bits 8-31 (bytes 1-3).
        icao24 = message[1:4].hex()
        ca = message[0] & 0x07

    tc: int | None = None
    tc_label: str | None = None
    if df in (17, 18) and len(message) >= 5:
        tc = message[4] >> 3
        tc_label = _tc_category(tc)

    return DecodedMessage(df=df, df_label=df_label, icao24=icao24, ca=ca, tc=tc, tc_label=tc_label)
