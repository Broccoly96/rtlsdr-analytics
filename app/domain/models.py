"""Internal domain models: normalized, in-memory representations of readsb
data. These are the shapes the collector produces and the store persists --
independent of both the raw readsb JSON shape and the eventual DB schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ReceptionState(str, Enum):
    RECEIVED = "received"  # seen <= 15s
    POSITION_ACQUIRED = "position_acquired"  # received + valid lat/lon + seen_pos <= 30s


@dataclass(frozen=True, slots=True)
class AircraftObservation:
    icao: str
    observed_at: datetime  # UTC
    callsign: str | None
    lat: float | None
    lon: float | None
    altitude_ft: float | None
    ground_speed_kt: float | None
    track_deg: float | None
    vertical_rate_fpm: float | None
    rssi: float | None
    distance_km: float | None
    bearing_deg: float | None
    source_age_seconds: float
    reception_state: ReceptionState
