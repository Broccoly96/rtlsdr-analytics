from __future__ import annotations

from datetime import timedelta

from app.db.queries.receiver import (
    HOURLY_BUCKET_THRESHOLD_HOURS,
    _bucket_size,
)


def test_bucket_size_is_minutes_at_or_under_threshold():
    assert _bucket_size(1) == timedelta(minutes=1)
    assert _bucket_size(HOURLY_BUCKET_THRESHOLD_HOURS) == timedelta(minutes=1)


def test_bucket_size_is_hourly_above_threshold():
    assert _bucket_size(HOURLY_BUCKET_THRESHOLD_HOURS + 1) == timedelta(hours=1)
    assert _bucket_size(720) == timedelta(hours=1)
