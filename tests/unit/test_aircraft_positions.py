import math

from app.api.routers.aircraft_positions import (
    FAST_POLL_INTERVAL_SECONDS,
    PositionBroadcaster,
    compute_transit_candidate,
    extract_position,
)
from app.domain.celestial import CelestialPosition
from app.domain.geo import bearing_deg, haversine_distance_km


def test_extracts_position_with_geometric_altitude():
    result = extract_position(
        {
            "hex": "aaaaaa",
            "flight": "ANA64  ",
            "lat": 35.0,
            "lon": 139.0,
            "alt_geom": 5000,
            "alt_baro": 4900,
            "track": 90,
            "gs": 400,
            "roll": -12.5,
            "baro_rate": -800,
            "geom_rate": -750,
            "category": "A3",
            "squawk": "2000",
        }
    )
    assert result == {
        "icao": "aaaaaa",
        "callsign": "ANA64",
        "lat": 35.0,
        "lon": 139.0,
        "altitude_ft": 5000,
        "track_deg": 90,
        "ground_speed_kt": 400,
        "roll_deg": -12.5,
        "vertical_rate_fpm": -800,
        "category": "A3",
        "squawk": "2000",
    }


def test_squawk_absent_becomes_none():
    result = extract_position({"hex": "aaaaad", "lat": 1.0, "lon": 2.0})
    assert result["squawk"] is None


def test_roll_absent_becomes_none():
    result = extract_position({"hex": "aaaaab", "lat": 1.0, "lon": 2.0})
    assert result["roll_deg"] is None


def test_vertical_rate_falls_back_to_geom_rate():
    result = extract_position({"hex": "aaaaac", "lat": 1.0, "lon": 2.0, "geom_rate": 640})
    assert result["vertical_rate_fpm"] == 640


def test_vertical_rate_absent_becomes_none():
    result = extract_position({"hex": "aaaaad", "lat": 1.0, "lon": 2.0})
    assert result["vertical_rate_fpm"] is None


def test_falls_back_to_barometric_altitude():
    result = extract_position({"hex": "bbbbbb", "lat": 1.0, "lon": 2.0, "alt_baro": 4900})
    assert result["altitude_ft"] == 4900


def test_ground_altitude_string_becomes_none():
    result = extract_position({"hex": "cccccc", "lat": 1.0, "lon": 2.0, "alt_baro": "ground"})
    assert result["altitude_ft"] is None


def test_no_position_returns_none():
    assert extract_position({"hex": "dddddd", "alt_baro": 1000}) is None
    assert extract_position({"hex": "eeeeee", "lat": 1.0}) is None


def test_no_icao_returns_none():
    assert extract_position({"lat": 1.0, "lon": 2.0}) is None


def test_blank_callsign_becomes_none():
    result = extract_position({"hex": "ffffff", "lat": 1.0, "lon": 2.0, "flight": "   "})
    assert result["callsign"] is None


# --- PositionBroadcaster fast-mode interval selection --------------------
# Plain objects stand in for WebSocket connections -- register/unregister/
# set_fast only ever add/discard by identity, never call WebSocket methods.


def test_current_interval_defaults_to_configured_value():
    broadcaster = PositionBroadcaster(
        "http://example/aircraft.json",
        poll_interval_seconds=5.0,
        receiver_lat=35.0,
        receiver_lon=139.0,
    )
    assert broadcaster.current_interval == 5.0


def test_current_interval_is_fast_when_any_client_opts_in():
    broadcaster = PositionBroadcaster(
        "http://example/aircraft.json",
        poll_interval_seconds=5.0,
        receiver_lat=35.0,
        receiver_lon=139.0,
    )
    client_a, client_b = object(), object()
    broadcaster.register(client_a)
    broadcaster.register(client_b)
    broadcaster.set_fast(client_a, True)
    assert broadcaster.current_interval == FAST_POLL_INTERVAL_SECONDS


def test_current_interval_reverts_once_no_client_wants_fast():
    broadcaster = PositionBroadcaster(
        "http://example/aircraft.json",
        poll_interval_seconds=5.0,
        receiver_lat=35.0,
        receiver_lon=139.0,
    )
    client = object()
    broadcaster.register(client)
    broadcaster.set_fast(client, True)
    broadcaster.set_fast(client, False)
    assert broadcaster.current_interval == 5.0


def test_unregister_clears_fast_state():
    broadcaster = PositionBroadcaster(
        "http://example/aircraft.json",
        poll_interval_seconds=5.0,
        receiver_lat=35.0,
        receiver_lon=139.0,
    )
    client = object()
    broadcaster.register(client)
    broadcaster.set_fast(client, True)
    broadcaster.unregister(client)
    assert broadcaster.current_interval == 5.0


# --- compute_transit_candidate (Milestone LL) ------------------------------

_RECEIVER_LAT, _RECEIVER_LON = 0.0, 0.0
_AIRCRAFT_LAT, _AIRCRAFT_LON = 0.9, 0.0  # ~100km due north of the receiver
_AIRCRAFT_ALT_FT = 30000
_AZIMUTH = bearing_deg(_RECEIVER_LAT, _RECEIVER_LON, _AIRCRAFT_LAT, _AIRCRAFT_LON)
_GROUND_KM = haversine_distance_km(_RECEIVER_LAT, _RECEIVER_LON, _AIRCRAFT_LAT, _AIRCRAFT_LON)
_ELEVATION = math.degrees(math.atan2(_AIRCRAFT_ALT_FT * 0.3048, _GROUND_KM * 1000.0))
_POSITION = {"lat": _AIRCRAFT_LAT, "lon": _AIRCRAFT_LON, "altitude_ft": _AIRCRAFT_ALT_FT}


def test_transit_candidate_true_when_aligned_with_sun():
    sun = CelestialPosition(azimuth_deg=_AZIMUTH, elevation_deg=_ELEVATION)
    assert compute_transit_candidate(_POSITION, _RECEIVER_LAT, _RECEIVER_LON, sun) is True


def test_transit_candidate_false_when_far_from_sun():
    sun = CelestialPosition(azimuth_deg=(_AZIMUTH + 90) % 360, elevation_deg=_ELEVATION)
    assert compute_transit_candidate(_POSITION, _RECEIVER_LAT, _RECEIVER_LON, sun) is False


def test_transit_candidate_false_when_sun_below_horizon():
    sun = CelestialPosition(azimuth_deg=_AZIMUTH, elevation_deg=-5.0)
    assert compute_transit_candidate(_POSITION, _RECEIVER_LAT, _RECEIVER_LON, sun) is False


def test_transit_candidate_false_when_altitude_missing():
    position_no_alt = {"lat": _AIRCRAFT_LAT, "lon": _AIRCRAFT_LON, "altitude_ft": None}
    sun = CelestialPosition(azimuth_deg=_AZIMUTH, elevation_deg=_ELEVATION)
    assert compute_transit_candidate(position_no_alt, _RECEIVER_LAT, _RECEIVER_LON, sun) is False
