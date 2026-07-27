"""Decides whether to persist a position sample for an aircraft this poll.

Position history isn't written every poll -- PLAN.md requires roughly a
30-second cadence per aircraft, or immediately on a significant position or
altitude change, so storage doesn't grow proportional to the 5-second poll
interval.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.collector.geo import haversine_distance_km

SIGNIFICANT_POSITION_CHANGE_KM = 0.5
SIGNIFICANT_ALTITUDE_CHANGE_FT = 500.0


@dataclass
class _AircraftSampleState:
    last_sampled_at: float
    last_lat: float
    last_lon: float
    last_altitude_ft: float | None


class PositionSampler:
    def __init__(self, sample_interval_seconds: float) -> None:
        self._sample_interval_seconds = sample_interval_seconds
        self._state: dict[str, _AircraftSampleState] = {}

    def should_sample(
        self, icao: str, now: float, lat: float, lon: float, altitude_ft: float | None
    ) -> bool:
        state = self._state.get(icao)
        if state is None:
            self._state[icao] = _AircraftSampleState(now, lat, lon, altitude_ft)
            return True

        elapsed = now - state.last_sampled_at
        moved_km = haversine_distance_km(state.last_lat, state.last_lon, lat, lon)
        altitude_delta = (
            abs(altitude_ft - state.last_altitude_ft)
            if altitude_ft is not None and state.last_altitude_ft is not None
            else 0.0
        )

        sample = (
            elapsed >= self._sample_interval_seconds
            or moved_km >= SIGNIFICANT_POSITION_CHANGE_KM
            or altitude_delta >= SIGNIFICANT_ALTITUDE_CHANGE_FT
        )
        if sample:
            self._state[icao] = _AircraftSampleState(now, lat, lon, altitude_ft)
        return sample

    def forget(self, icao: str) -> None:
        """Drop state for an aircraft no longer being received, bounding memory."""
        self._state.pop(icao, None)

    def tracked_icaos(self) -> set[str]:
        return set(self._state.keys())

    def active_count(self) -> int:
        return len(self._state)
