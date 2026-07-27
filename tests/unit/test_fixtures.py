import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_all_fixtures_are_valid_json():
    fixture_files = list(FIXTURES_DIR.glob("*.json"))
    assert fixture_files, "expected at least one fixture file"
    for path in fixture_files:
        data = json.loads(path.read_text())
        assert "aircraft" in data
        assert isinstance(data["aircraft"], list)


def test_fixtures_do_not_contain_real_receiver_coordinates():
    # The real receiver sits near lat 36.2 / lon 139.5; fixtures intentionally
    # use a different public reference point (Tokyo Station area) so no
    # fixture accidentally leaks real receiver-adjacent coordinates.
    for path in FIXTURES_DIR.glob("*.json"):
        data = json.loads(path.read_text())
        for aircraft in data["aircraft"]:
            lat = aircraft.get("lat")
            lon = aircraft.get("lon")
            if lat is None or lon is None:
                continue
            near_real_receiver = abs(lat - 36.2) < 0.05 and abs(lon - 139.5) < 0.05
            assert not near_real_receiver, f"{path.name} uses a real-receiver-adjacent coordinate"
