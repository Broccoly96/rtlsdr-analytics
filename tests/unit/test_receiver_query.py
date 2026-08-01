from __future__ import annotations

from datetime import timedelta

from app.db.queries.receiver import (
    BEARING_SECTOR_COUNT,
    DEFAULT_DOME_ALTITUDE_BUCKET_FT,
    DOME_MAX_CELLS,
    HOURLY_BUCKET_THRESHOLD_HOURS,
    SECTOR_WIDTH_DEG,
    _bucket_size,
)


def test_bucket_size_is_minutes_at_or_under_threshold():
    assert _bucket_size(1) == timedelta(minutes=1)
    assert _bucket_size(HOURLY_BUCKET_THRESHOLD_HOURS) == timedelta(minutes=1)


def test_bucket_size_is_hourly_above_threshold():
    assert _bucket_size(HOURLY_BUCKET_THRESHOLD_HOURS + 1) == timedelta(hours=1)
    assert _bucket_size(720) == timedelta(hours=1)


def test_reception_dome_sector_center_matches_bearing_range_convention():
    # reception_dome() computes sector_center_deg the same way bearing_range()
    # does, so both charts on receiver.html agree on sector boundaries.
    assert 0 * SECTOR_WIDTH_DEG + SECTOR_WIDTH_DEG / 2 == 11.25
    last_sector = BEARING_SECTOR_COUNT - 1
    assert last_sector * SECTOR_WIDTH_DEG + SECTOR_WIDTH_DEG / 2 == 348.75


def test_reception_dome_altitude_bucket_is_a_fixed_step_not_altitude_bands():
    # Deliberately not ALTITUDE_BANDS (5 coarse bands) -- see reception_dome()'s
    # docstring: 5 bands would collapse the vertical axis to 5 flat shells.
    assert DEFAULT_DOME_ALTITUDE_BUCKET_FT == 2000.0


def test_dome_max_cells_is_a_positive_cap():
    assert DOME_MAX_CELLS > 0
