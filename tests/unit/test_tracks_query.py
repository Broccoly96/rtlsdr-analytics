from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.queries.tracks import (
    AircraftTrack,
    TrackPoint,
    _build_track,
    _decimate_to_budget,
)

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _row(offset_seconds, lat, lon, callsign="TEST001", altitude_ft=10000.0, gs=400.0):
    return {
        "icao": "aaaaaa",
        "callsign": callsign,
        "observed_at": T0 + timedelta(seconds=offset_seconds),
        "lat": lat,
        "lon": lon,
        "altitude_ft": altitude_ft,
        "ground_speed_kt": gs,
    }


def test_build_track_single_segment_for_continuous_points():
    rows = [_row(0, 35.0, 139.0), _row(30, 35.01, 139.0), _row(60, 35.02, 139.0)]
    track = _build_track("aaaaaa", rows)
    assert len(track.segments) == 1
    assert len(track.segments[0]) == 3
    assert track.last_observed_at == rows[-1]["observed_at"]
    assert track.callsign == "TEST001"


def test_build_track_splits_on_long_time_gap():
    rows = [_row(0, 35.0, 139.0), _row(30, 35.01, 139.0), _row(600, 35.02, 139.0)]
    track = _build_track("aaaaaa", rows)
    assert len(track.segments) == 2
    assert len(track.segments[0]) == 2
    assert len(track.segments[1]) == 1


def test_build_track_splits_on_implausible_position_jump():
    # ~2 degrees latitude in 5 seconds is far beyond any real aircraft speed.
    rows = [_row(0, 35.0, 139.0), _row(5, 37.0, 139.0)]
    track = _build_track("aaaaaa", rows)
    assert len(track.segments) == 2
    assert all(len(segment) == 1 for segment in track.segments)


def test_decimate_to_budget_noop_when_under_budget():
    tracks = [
        AircraftTrack(
            icao="aaaaaa",
            callsign=None,
            last_altitude_ft=None,
            last_ground_speed_kt=None,
            last_observed_at=T0,
            segments=[[TrackPoint(T0, 35.0, 139.0, None)] * 5],
        )
    ]
    result = _decimate_to_budget(tracks, max_points=100)
    assert result is tracks


def test_decimate_to_budget_reduces_point_count_and_keeps_last_point():
    points = [
        TrackPoint(T0 + timedelta(seconds=i), 35.0 + i * 0.001, 139.0, None) for i in range(100)
    ]
    last_point = points[-1]
    tracks = [
        AircraftTrack(
            icao="aaaaaa",
            callsign=None,
            last_altitude_ft=None,
            last_ground_speed_kt=None,
            last_observed_at=T0,
            segments=[points],
        )
    ]
    result = _decimate_to_budget(tracks, max_points=10)
    total_points = sum(len(segment) for track in result for segment in track.segments)
    assert total_points <= 11  # budget plus the always-kept last point
    assert result[0].segments[0][-1] is last_point
