from __future__ import annotations

from app.domain.bands import ALTITUDE_BANDS, band_case_sql, band_key_for_altitude


def test_band_key_for_altitude_covers_every_band():
    assert band_key_for_altitude(-500) == "ground"
    assert band_key_for_altitude(0) == "ground"
    assert band_key_for_altitude(5000) == "low"
    assert band_key_for_altitude(10000) == "low"
    assert band_key_for_altitude(20000) == "mid"
    assert band_key_for_altitude(30000) == "high"
    assert band_key_for_altitude(90000) == "very_high"


def test_band_key_for_altitude_none_is_none():
    assert band_key_for_altitude(None) is None


def test_band_case_sql_has_one_branch_per_band_and_a_null_guard():
    sql = band_case_sql("altitude_ft")
    assert sql.startswith("CASE WHEN altitude_ft IS NULL THEN NULL")
    assert sql.strip().endswith("END")
    for band in ALTITUDE_BANDS:
        assert f"'{band.key}'" in sql
