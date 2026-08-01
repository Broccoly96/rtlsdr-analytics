from __future__ import annotations

from datetime import UTC, datetime

from app.domain.celestial import angular_separation_deg, solar_position

TOKYO_LAT = 35.6812
TOKYO_LON = 139.7671


def test_solar_position_elevation_within_valid_range():
    pos = solar_position(datetime(2026, 3, 20, 12, 0, tzinfo=UTC), TOKYO_LAT, TOKYO_LON)
    assert -90.0 <= pos.elevation_deg <= 90.0
    assert 0.0 <= pos.azimuth_deg < 360.0


def test_sun_is_below_horizon_at_tokyo_midnight():
    # 15:00 UTC = 00:00 JST (UTC+9) the next day -- the middle of the
    # night in Tokyo any time of year.
    pos = solar_position(datetime(2026, 6, 21, 15, 0, tzinfo=UTC), TOKYO_LAT, TOKYO_LON)
    assert pos.elevation_deg < 0


def test_sun_is_above_horizon_at_tokyo_midday():
    # 03:00 UTC = 12:00 JST -- roughly solar noon in Tokyo.
    pos = solar_position(datetime(2026, 6, 21, 3, 0, tzinfo=UTC), TOKYO_LAT, TOKYO_LON)
    assert pos.elevation_deg > 0


def test_sun_is_roughly_southward_at_tokyo_midday():
    # Tokyo (35.68N) is well north of the Tropic of Cancer, so the sun
    # sits to the south at local solar noon year-round -- a robust
    # invariant regardless of exact date.
    pos = solar_position(datetime(2026, 6, 21, 3, 0, tzinfo=UTC), TOKYO_LAT, TOKYO_LON)
    assert 135.0 <= pos.azimuth_deg <= 225.0


def test_summer_midday_sun_is_higher_than_winter_midday_sun():
    summer = solar_position(datetime(2026, 6, 21, 3, 0, tzinfo=UTC), TOKYO_LAT, TOKYO_LON)
    winter = solar_position(datetime(2026, 12, 21, 3, 0, tzinfo=UTC), TOKYO_LAT, TOKYO_LON)
    assert summer.elevation_deg > winter.elevation_deg


def test_solar_position_accepts_non_utc_timezone_aware_datetime():
    from datetime import timedelta, timezone

    jst = timezone(timedelta(hours=9))
    utc_time = datetime(2026, 6, 21, 3, 0, tzinfo=UTC)
    jst_time = utc_time.astimezone(jst)
    assert solar_position(utc_time, TOKYO_LAT, TOKYO_LON) == solar_position(
        jst_time, TOKYO_LAT, TOKYO_LON
    )


def test_angular_separation_zero_for_identical_points():
    assert angular_separation_deg(123.0, 45.0, 123.0, 45.0) == 0.0


def test_angular_separation_is_180_for_opposite_horizon_points():
    assert angular_separation_deg(0.0, 0.0, 180.0, 0.0) == 180.0


def test_angular_separation_is_zero_at_zenith_regardless_of_azimuth():
    assert angular_separation_deg(10.0, 90.0, 200.0, 90.0) == 0.0


def test_angular_separation_is_symmetric():
    a = angular_separation_deg(10.0, 20.0, 200.0, -30.0)
    b = angular_separation_deg(200.0, -30.0, 10.0, 20.0)
    assert a == b
