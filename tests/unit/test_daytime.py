from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.domain.daytime import day_bounds_utc, today_in_tz, yesterday_in_tz


def test_day_bounds_utc_jst_no_dst():
    start_utc, end_utc = day_bounds_utc(date(2026, 3, 15), "Asia/Tokyo")
    # JST is UTC+9 with no DST, so 00:00 JST == 15:00 UTC the previous day.
    assert start_utc == datetime(2026, 3, 14, 15, 0, 0, tzinfo=UTC)
    assert end_utc == datetime(2026, 3, 15, 15, 0, 0, tzinfo=UTC)
    assert (end_utc - start_utc).total_seconds() == 86400


def test_day_bounds_utc_dst_timezone_spans_23_or_25_hours():
    # America/New_York observes DST -- the day DST starts is 23 hours long
    # in UTC terms. Exercised specifically because JST (this app's default)
    # has no DST, so this path wouldn't otherwise be covered.
    start_utc, end_utc = day_bounds_utc(date(2026, 3, 8), "America/New_York")
    assert (end_utc - start_utc).total_seconds() == 23 * 3600


def test_today_in_tz_uses_given_now():
    # JST is UTC+9: 2025-12-31 14:59 UTC is 23:59 JST (still Dec 31 JST),
    # 2025-12-31 15:00 UTC is 00:00 JST (already Jan 1 JST).
    before = datetime(2025, 12, 31, 14, 59, 0, tzinfo=UTC)
    after = datetime(2025, 12, 31, 15, 0, 0, tzinfo=UTC)
    assert today_in_tz("Asia/Tokyo", now=before) == date(2025, 12, 31)
    assert today_in_tz("Asia/Tokyo", now=after) == date(2026, 1, 1)


def test_yesterday_in_tz_is_one_day_before_today():
    now = datetime(2026, 6, 15, 3, 0, 0, tzinfo=UTC)
    assert yesterday_in_tz("Asia/Tokyo", now=now) == today_in_tz("Asia/Tokyo", now=now) - timedelta(
        days=1
    )
