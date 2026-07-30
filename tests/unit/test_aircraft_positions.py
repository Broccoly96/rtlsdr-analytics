from app.api.routers.aircraft_positions import (
    FAST_POLL_INTERVAL_SECONDS,
    PositionBroadcaster,
    extract_position,
)


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
    }


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
    broadcaster = PositionBroadcaster("http://example/aircraft.json", poll_interval_seconds=5.0)
    assert broadcaster.current_interval == 5.0


def test_current_interval_is_fast_when_any_client_opts_in():
    broadcaster = PositionBroadcaster("http://example/aircraft.json", poll_interval_seconds=5.0)
    client_a, client_b = object(), object()
    broadcaster.register(client_a)
    broadcaster.register(client_b)
    broadcaster.set_fast(client_a, True)
    assert broadcaster.current_interval == FAST_POLL_INTERVAL_SECONDS


def test_current_interval_reverts_once_no_client_wants_fast():
    broadcaster = PositionBroadcaster("http://example/aircraft.json", poll_interval_seconds=5.0)
    client = object()
    broadcaster.register(client)
    broadcaster.set_fast(client, True)
    broadcaster.set_fast(client, False)
    assert broadcaster.current_interval == 5.0


def test_unregister_clears_fast_state():
    broadcaster = PositionBroadcaster("http://example/aircraft.json", poll_interval_seconds=5.0)
    client = object()
    broadcaster.register(client)
    broadcaster.set_fast(client, True)
    broadcaster.unregister(client)
    assert broadcaster.current_interval == 5.0
