"""Converts raw readsb aircraft.json entries into normalized domain models.

Unlike scripts/probe_readsb.py's shallow Phase 0 presence tally, this module
performs full semantic validation: range-checking coordinates, rejecting
future/invalid timestamps, and handling readsb's `alt_baro: "ground"`
sentinel. The same eight fixtures under tests/fixtures/ that define Phase 0's
acceptance criteria are reused here against this stricter validation.

An aircraft with a valid `seen` but no usable position still produces an
observation (with lat/lon/distance/bearing left None) -- PLAN.md requires
position-less aircraft to still count toward "currently received".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.collector.geo import bearing_deg, haversine_distance_km
from app.domain.models import AircraftObservation, ReceptionState

RECEIVED_MAX_SEEN_SECONDS = 15.0
POSITION_ACQUIRED_MAX_SEEN_POS_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class NormalizedPoll:
    polled_at: datetime
    observations: list[AircraftObservation]
    received_count: int
    position_acquired_count: int
    excluded_reasons: dict[str, int]


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _parse_altitude(value: Any) -> float | None:
    if value == "ground":
        return 0.0
    return _as_float(value)


def _valid_coordinate(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def normalize_aircraft_entry(
    raw: dict[str, Any],
    polled_at: datetime,
    receiver_lat: float,
    receiver_lon: float,
) -> tuple[AircraftObservation | None, str | None]:
    """Returns (observation_or_None, exclusion_reason_or_None)."""
    hex_value = raw.get("hex")
    if not isinstance(hex_value, str) or not hex_value:
        return None, "missing_hex"

    seen = _as_float(raw.get("seen"))
    if seen is None or seen < 0:
        return None, "invalid_seen"
    if seen > RECEIVED_MAX_SEEN_SECONDS:
        return None, "stale"

    seen_pos = _as_float(raw.get("seen_pos"))
    lat = _as_float(raw.get("lat"))
    lon = _as_float(raw.get("lon"))
    has_valid_position = _valid_coordinate(lat, lon) and seen_pos is not None and seen_pos >= 0

    reception_state = ReceptionState.RECEIVED
    distance_km: float | None = None
    bearing: float | None = None
    if has_valid_position and seen_pos <= POSITION_ACQUIRED_MAX_SEEN_POS_SECONDS:
        reception_state = ReceptionState.POSITION_ACQUIRED
        distance_km = haversine_distance_km(receiver_lat, receiver_lon, lat, lon)
        bearing = bearing_deg(receiver_lat, receiver_lon, lat, lon)
    else:
        lat = lon = None  # present but unusable this poll -> treat as absent

    callsign_raw = raw.get("flight")
    callsign = callsign_raw.strip() if isinstance(callsign_raw, str) else None

    baro_rate = _as_float(raw.get("baro_rate"))
    vertical_rate_fpm = baro_rate if baro_rate is not None else _as_float(raw.get("geom_rate"))

    observation = AircraftObservation(
        icao=hex_value.lower(),
        observed_at=polled_at,
        callsign=callsign or None,
        lat=lat,
        lon=lon,
        altitude_ft=_parse_altitude(raw.get("alt_baro")),
        ground_speed_kt=_as_float(raw.get("gs")),
        track_deg=_as_float(raw.get("track")),
        vertical_rate_fpm=vertical_rate_fpm,
        rssi=_as_float(raw.get("rssi")),
        distance_km=distance_km,
        bearing_deg=bearing,
        source_age_seconds=seen,
        reception_state=reception_state,
    )
    return observation, None


def normalize_poll(
    payload: dict[str, Any],
    polled_at: datetime,
    receiver_lat: float,
    receiver_lon: float,
) -> NormalizedPoll:
    aircraft = payload.get("aircraft") if isinstance(payload, dict) else None
    if not isinstance(aircraft, list):
        return NormalizedPoll(polled_at, [], 0, 0, {"invalid_payload": 1})

    by_icao: dict[str, AircraftObservation] = {}
    excluded_reasons: dict[str, int] = {}

    for raw in aircraft:
        if not isinstance(raw, dict):
            excluded_reasons["not_a_dict"] = excluded_reasons.get("not_a_dict", 0) + 1
            continue
        observation, reason = normalize_aircraft_entry(raw, polled_at, receiver_lat, receiver_lon)
        if observation is None:
            if reason:
                excluded_reasons[reason] = excluded_reasons.get(reason, 0) + 1
            continue
        # Duplicate ICAOs in one poll: keep the freshest (smallest source_age_seconds).
        existing = by_icao.get(observation.icao)
        if existing is None or observation.source_age_seconds < existing.source_age_seconds:
            by_icao[observation.icao] = observation

    observations = list(by_icao.values())
    position_acquired_count = sum(
        1 for o in observations if o.reception_state == ReceptionState.POSITION_ACQUIRED
    )

    return NormalizedPoll(
        polled_at=polled_at,
        observations=observations,
        received_count=len(observations),
        position_acquired_count=position_acquired_count,
        excluded_reasons=excluded_reasons,
    )
