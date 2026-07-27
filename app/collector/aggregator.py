"""Rolls per-poll reception counts up into 1-minute traffic aggregates.

PLAN.md defines the 1-minute concurrent count as the max "currently
received" count observed within that minute, not an average or a sum.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TrafficMinute:
    bucket_at: datetime
    active_aircraft_count: int
    position_aircraft_count: int
    message_count_delta: int


def _minute_bucket(at: datetime) -> datetime:
    return at.replace(second=0, microsecond=0)


class MinuteAggregator:
    def __init__(self) -> None:
        self._bucket_at: datetime | None = None
        self._max_active = 0
        self._max_position = 0
        self._messages_at_bucket_start: int | None = None
        self._last_messages: int | None = None

    def record_poll(
        self,
        polled_at: datetime,
        active_count: int,
        position_count: int,
        messages_total: int | None,
    ) -> TrafficMinute | None:
        """Feed one poll's counts in; returns a completed TrafficMinute when the
        minute rolls over, else None."""
        bucket = _minute_bucket(polled_at)
        completed: TrafficMinute | None = None

        if self._bucket_at is None:
            self._bucket_at = bucket
            self._messages_at_bucket_start = messages_total

        if bucket != self._bucket_at:
            completed = self._finish_bucket()
            self._bucket_at = bucket
            self._max_active = 0
            self._max_position = 0
            self._messages_at_bucket_start = self._last_messages

        self._max_active = max(self._max_active, active_count)
        self._max_position = max(self._max_position, position_count)
        self._last_messages = messages_total

        return completed

    def _finish_bucket(self) -> TrafficMinute:
        delta = 0
        if self._messages_at_bucket_start is not None and self._last_messages is not None:
            delta = max(0, self._last_messages - self._messages_at_bucket_start)
        assert self._bucket_at is not None
        return TrafficMinute(
            bucket_at=self._bucket_at,
            active_aircraft_count=self._max_active,
            position_aircraft_count=self._max_position,
            message_count_delta=delta,
        )

    def flush(self) -> TrafficMinute | None:
        """Force-close the current bucket (e.g. on graceful shutdown)."""
        if self._bucket_at is None:
            return None
        return self._finish_bucket()
