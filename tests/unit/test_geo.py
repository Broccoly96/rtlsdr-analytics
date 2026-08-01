import math

import pytest

from app.domain.geo import EARTH_RADIUS_KM, bearing_deg, haversine_distance_km


def test_haversine_distance_one_degree_longitude_at_equator():
    distance = haversine_distance_km(0.0, 0.0, 0.0, 1.0)
    expected = 2 * math.pi * EARTH_RADIUS_KM / 360
    assert distance == pytest.approx(expected, rel=1e-6)


def test_haversine_distance_same_point_is_zero():
    assert haversine_distance_km(35.6, 139.7, 35.6, 139.7) == pytest.approx(0.0, abs=1e-9)


def test_haversine_distance_known_city_pair():
    # Tokyo Station area to Osaka Station area, ~400 km apart.
    distance = haversine_distance_km(35.6812, 139.7671, 34.7024, 135.4959)
    assert 390 < distance < 410


def test_bearing_due_east():
    assert bearing_deg(0.0, 0.0, 0.0, 1.0) == pytest.approx(90.0, abs=0.01)


def test_bearing_due_north():
    assert bearing_deg(0.0, 0.0, 1.0, 0.0) == pytest.approx(0.0, abs=0.01)


def test_bearing_due_south():
    assert bearing_deg(1.0, 0.0, 0.0, 0.0) == pytest.approx(180.0, abs=0.01)


def test_bearing_due_west():
    assert bearing_deg(0.0, 1.0, 0.0, 0.0) == pytest.approx(270.0, abs=0.01)
