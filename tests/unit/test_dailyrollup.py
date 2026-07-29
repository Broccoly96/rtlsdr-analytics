from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.dailyrollup import MAX_PASS_GAP_SECONDS, count_passes, next_run_at

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_count_passes_empty_is_zero():
    assert count_passes([]) == 0


def test_count_passes_single_observation_is_one_pass():
    assert count_passes([T0]) == 1


def test_count_passes_continuous_observations_are_one_pass():
    times = [T0, T0 + timedelta(seconds=30), T0 + timedelta(seconds=60)]
    assert count_passes(times) == 1


def test_count_passes_splits_on_long_gap():
    times = [T0, T0 + timedelta(seconds=30), T0 + timedelta(seconds=MAX_PASS_GAP_SECONDS + 60)]
    assert count_passes(times) == 2


def test_count_passes_gap_exactly_at_threshold_does_not_split():
    times = [T0, T0 + timedelta(seconds=MAX_PASS_GAP_SECONDS)]
    assert count_passes(times) == 1


def test_count_passes_multiple_gaps():
    times = [
        T0,
        T0 + timedelta(seconds=MAX_PASS_GAP_SECONDS + 1),
        T0 + timedelta(seconds=2 * (MAX_PASS_GAP_SECONDS + 1)),
    ]
    assert count_passes(times) == 3


def test_next_run_at_later_today():
    now_utc = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)  # 09:00 JST
    result = next_run_at(now_utc, "Asia/Tokyo", hour=10, minute=0)
    # 10:00 JST == 01:00 UTC, same day.
    assert result == datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)


def test_next_run_at_rolls_to_tomorrow_when_time_has_passed():
    now_utc = datetime(2026, 1, 1, 2, 0, 0, tzinfo=UTC)  # 11:00 JST
    result = next_run_at(now_utc, "Asia/Tokyo", hour=10, minute=0)
    # 10:00 JST already passed today -- next occurrence is tomorrow.
    assert result == datetime(2026, 1, 2, 1, 0, 0, tzinfo=UTC)


def test_next_run_at_exactly_now_rolls_to_tomorrow():
    now_utc = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)  # exactly 10:00 JST
    result = next_run_at(now_utc, "Asia/Tokyo", hour=10, minute=0)
    assert result == datetime(2026, 1, 2, 1, 0, 0, tzinfo=UTC)
