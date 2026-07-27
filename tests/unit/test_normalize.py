import json
from datetime import UTC, datetime
from pathlib import Path

from app.collector.normalize import normalize_poll
from app.domain.models import ReceptionState

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
NOW = datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC)  # matches fixtures' "now": 1700000000.0
RECEIVER_LAT, RECEIVER_LON = 35.0, 139.0  # arbitrary test receiver, distinct from the real one


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def _normalize(name: str):
    return normalize_poll(_load(name), NOW, RECEIVER_LAT, RECEIVER_LON)


def test_sample_fixture_all_position_acquired():
    result = _normalize("aircraft_sample.json")
    assert result.received_count == 5
    assert result.position_acquired_count == 5
    for obs in result.observations:
        assert obs.reception_state == ReceptionState.POSITION_ACQUIRED
        assert obs.distance_km is not None
        assert obs.bearing_deg is not None


def test_empty_fixture():
    result = _normalize("aircraft_empty.json")
    assert result.received_count == 0
    assert result.observations == []


def test_missing_fields_fixture_excludes_entry_without_hex():
    result = _normalize("aircraft_missing_fields.json")
    assert result.received_count == 2
    assert result.excluded_reasons.get("missing_hex") == 1
    icaos = {o.icao for o in result.observations}
    assert icaos == {"bbbbb1", "bbbbb2"}
    for obs in result.observations:
        assert obs.reception_state == ReceptionState.RECEIVED
        assert obs.lat is None


def test_lat_only_fixture_has_no_usable_position():
    result = _normalize("aircraft_lat_only.json")
    assert result.received_count == 2
    assert result.position_acquired_count == 0
    for obs in result.observations:
        assert obs.lat is None
        assert obs.lon is None


def test_ground_altitude_fixture_maps_to_zero_feet():
    result = _normalize("aircraft_ground_altitude.json")
    assert result.observations[0].altitude_ft == 0.0
    assert result.observations[0].reception_state == ReceptionState.POSITION_ACQUIRED


def test_future_time_fixture_excluded_as_invalid_seen():
    result = _normalize("aircraft_future_time.json")
    assert result.received_count == 0
    assert result.excluded_reasons.get("invalid_seen") == 1


def test_out_of_range_coords_fixture_position_rejected():
    result = _normalize("aircraft_out_of_range_coords.json")
    assert result.received_count == 2
    assert result.position_acquired_count == 0
    for obs in result.observations:
        assert obs.lat is None
        assert obs.lon is None


def test_duplicate_icao_fixture_keeps_freshest():
    result = _normalize("aircraft_duplicate_icao.json")
    assert result.received_count == 1
    obs = result.observations[0]
    assert obs.icao == "12ab34"
    assert obs.source_age_seconds == 0.1  # the fresher of the two duplicate entries


def test_invalid_payload_shape_does_not_crash():
    result = normalize_poll({"aircraft": "not-a-list"}, NOW, RECEIVER_LAT, RECEIVER_LON)
    assert result.observations == []
    assert result.excluded_reasons.get("invalid_payload") == 1


def test_handles_large_aircraft_count_without_crashing():
    payload = {"aircraft": [{"hex": f"a{i:05x}", "seen": 0.1} for i in range(5000)]}
    result = normalize_poll(payload, NOW, RECEIVER_LAT, RECEIVER_LON)
    assert result.received_count == 5000


def test_stale_entry_excluded():
    payload = {
        "aircraft": [{"hex": "aaaaaa", "seen": 20.0, "lat": 35.0, "lon": 139.0, "seen_pos": 1.0}]
    }
    result = normalize_poll(payload, NOW, RECEIVER_LAT, RECEIVER_LON)
    assert result.received_count == 0
    assert result.excluded_reasons.get("stale") == 1


def test_position_stale_but_aircraft_still_received():
    payload = {
        "aircraft": [{"hex": "aaaaaa", "seen": 1.0, "lat": 35.0, "lon": 139.0, "seen_pos": 45.0}]
    }
    result = normalize_poll(payload, NOW, RECEIVER_LAT, RECEIVER_LON)
    assert result.received_count == 1
    assert result.position_acquired_count == 0
    obs = result.observations[0]
    assert obs.reception_state == ReceptionState.RECEIVED
    assert obs.lat is None


def test_baro_rate_zero_is_not_treated_as_missing():
    payload = {"aircraft": [{"hex": "aaaaaa", "seen": 0.1, "baro_rate": 0}]}
    result = normalize_poll(payload, NOW, RECEIVER_LAT, RECEIVER_LON)
    assert result.observations[0].vertical_rate_fpm == 0.0
