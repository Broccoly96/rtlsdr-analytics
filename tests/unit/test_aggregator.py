from datetime import UTC, datetime

from app.collector.aggregator import MinuteAggregator


def _dt(second: int) -> datetime:
    return datetime(2026, 1, 1, 12, 0, second, tzinfo=UTC)


def test_single_minute_takes_max_counts():
    agg = MinuteAggregator()
    assert agg.record_poll(_dt(0), 3, 1, 100) is None
    assert agg.record_poll(_dt(5), 5, 2, 110) is None
    assert agg.record_poll(_dt(10), 2, 1, 120) is None
    completed = agg.flush()
    assert completed is not None
    assert completed.active_aircraft_count == 5
    assert completed.position_aircraft_count == 2
    assert completed.message_count_delta == 20


def test_minute_rollover_emits_completed_bucket():
    agg = MinuteAggregator()
    agg.record_poll(_dt(0), 3, 1, 100)
    agg.record_poll(_dt(55), 4, 2, 150)
    completed = agg.record_poll(datetime(2026, 1, 1, 12, 1, 5, tzinfo=UTC), 1, 0, 160)
    assert completed is not None
    assert completed.active_aircraft_count == 4
    assert completed.message_count_delta == 50


def test_message_count_delta_never_negative_on_counter_reset():
    agg = MinuteAggregator()
    agg.record_poll(_dt(0), 1, 0, 1000)
    agg.record_poll(_dt(30), 1, 0, 50)  # e.g. readsb restarted, counter reset
    completed = agg.flush()
    assert completed is not None
    assert completed.message_count_delta == 0


def test_flush_with_no_polls_returns_none():
    agg = MinuteAggregator()
    assert agg.flush() is None
