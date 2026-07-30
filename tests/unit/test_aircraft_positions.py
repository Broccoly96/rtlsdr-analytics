from app.api.routers.aircraft_positions import extract_position


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
    }


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
