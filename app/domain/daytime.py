"""Calendar-day <-> UTC boundary conversion for a configured display
timezone. Used wherever a *calendar day* boundary matters: the daily
rollup job (app/dailyrollup.py) and Milestone N's "today"/"yesterday"/
"same weekday last week" views. Computed in Python via zoneinfo, not
SQL's AT TIME ZONE, matching this app's existing convention that
time-window boundaries are computed in Python (see traffic.py,
rankings.py) rather than pushed into SQL.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]:
    """Returns [start_utc, end_utc) covering the given calendar `day` in
    the `tz_name` timezone."""
    tz = ZoneInfo(tz_name)
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def today_in_tz(tz_name: str, *, now: datetime | None = None) -> date:
    now = now if now is not None else datetime.now(UTC)
    return now.astimezone(ZoneInfo(tz_name)).date()


def yesterday_in_tz(tz_name: str, *, now: datetime | None = None) -> date:
    return today_in_tz(tz_name, now=now) - timedelta(days=1)
