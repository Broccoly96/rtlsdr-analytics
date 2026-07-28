from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.retention import compute_cutoff


def test_compute_cutoff_is_utc_and_subtracts_whole_days():
    now = datetime(2026, 7, 28, 12, 30, 0, tzinfo=UTC)
    cutoff = compute_cutoff(now, retention_days=30)
    assert cutoff == now - timedelta(days=30)
    assert cutoff.tzinfo is UTC


def test_compute_cutoff_one_day():
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    cutoff = compute_cutoff(now, retention_days=1)
    assert cutoff == datetime(2025, 12, 31, 0, 0, 0, tzinfo=UTC)
