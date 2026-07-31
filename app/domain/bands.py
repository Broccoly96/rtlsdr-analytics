"""Altitude-band definitions shared by the receiver-performance query
(app/db/queries/receiver.py groups observations by band) and the frontend
(map.js colors tracks by band, receiver.js/heatmap filter by band). Python
is the single source of truth, published to the frontend via GET
/api/config, instead of map.js keeping its own hard-coded copy that could
silently drift from a Python-side definition.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AltitudeBand:
    key: str
    label_ja: str
    max_ft: float | None  # inclusive upper bound; None = unbounded (top band)
    color: str


ALTITUDE_BANDS: tuple[AltitudeBand, ...] = (
    AltitudeBand("ground", "地上/低高度", 0, "#fbbf24"),
    AltitudeBand("low", "低高度", 10000, "#34d399"),
    AltitudeBand("mid", "中高度", 25000, "#60a5fa"),
    AltitudeBand("high", "高高度", 35000, "#c084fc"),
    AltitudeBand("very_high", "超高高度", None, "#ef4444"),
)


def band_key_for_altitude(altitude_ft: float | None) -> str | None:
    if altitude_ft is None:
        return None
    for band in ALTITUDE_BANDS:
        if band.max_ft is None or altitude_ft <= band.max_ft:
            return band.key
    return None


def band_case_sql(column: str = "altitude_ft") -> str:
    """SQL CASE expression assigning each row to a band key, for GROUP BY
    in receiver.py/heatmap.py. Only this module's own fixed numeric
    constants are interpolated into the SQL text -- never user input."""
    lines = [f"CASE WHEN {column} IS NULL THEN NULL"]
    for band in ALTITUDE_BANDS:
        if band.max_ft is None:
            lines.append(f"ELSE '{band.key}'")
        else:
            lines.append(f"WHEN {column} <= {band.max_ft} THEN '{band.key}'")
    lines.append("END")
    return " ".join(lines)
