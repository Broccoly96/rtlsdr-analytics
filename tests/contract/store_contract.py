"""Shared behavioral contract that any Store implementation (InMemoryStore,
PostgresStore) must satisfy. Each check_* function is run against both
backends by tests/contract/test_in_memory_store.py and
tests/contract/test_postgres_store.py.

The Store Protocol is write-only, so each check also takes a StoreReader --
a small, backend-specific helper that reads back what the write calls
should have produced (InMemoryStore's reader inspects its public dict
fields directly; PostgresStore's reader runs read-only SQL over a separate
connection, since PostgresStore itself exposes no read methods).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.collector.aggregator import TrafficMinute
from app.collector.store import IngestionStatus, Store
from app.domain.models import AircraftObservation, ReceptionState

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
T1 = datetime(2026, 1, 1, 12, 0, 5, tzinfo=UTC)


@dataclass
class AircraftRow:
    icao: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_callsign: str | None


class StoreReader(Protocol):
    async def get_aircraft(self, icao: str) -> AircraftRow | None: ...
    async def count_observations(self) -> int: ...
    async def get_observation(
        self, icao: str, observed_at: datetime
    ) -> AircraftObservation | None: ...
    async def get_traffic_minute(self, bucket_at: datetime) -> TrafficMinute | None: ...
    async def list_ingestion_status(self) -> list[IngestionStatus]: ...


def _observation(**overrides) -> AircraftObservation:
    fields = {
        "icao": "aaaaaa",
        "observed_at": T0,
        "callsign": "TEST001",
        "lat": 35.0,
        "lon": 139.0,
        "altitude_ft": 10000.0,
        "ground_speed_kt": 400.0,
        "track_deg": 90.0,
        "vertical_rate_fpm": 0.0,
        "rssi": -20.0,
        "distance_km": 50.0,
        "bearing_deg": 45.0,
        "source_age_seconds": 0.5,
        "reception_state": ReceptionState.POSITION_ACQUIRED,
    }
    fields.update(overrides)
    return AircraftObservation(**fields)


async def check_aircraft_created_on_first_seen(store: Store, reader: StoreReader) -> None:
    await store.upsert_aircraft("aaaaaa", T0, "TEST001")
    row = await reader.get_aircraft("aaaaaa")
    assert row is not None
    assert row.first_seen_at == T0
    assert row.last_seen_at == T0
    assert row.last_callsign == "TEST001"


async def check_last_seen_updates_on_subsequent_poll(store: Store, reader: StoreReader) -> None:
    await store.upsert_aircraft("aaaaaa", T0, "TEST001")
    await store.upsert_aircraft("aaaaaa", T1, "TEST001")
    row = await reader.get_aircraft("aaaaaa")
    assert row is not None
    assert row.first_seen_at == T0  # unchanged
    assert row.last_seen_at == T1  # advanced


async def check_blank_callsign_does_not_clear_existing_callsign(
    store: Store, reader: StoreReader
) -> None:
    await store.upsert_aircraft("aaaaaa", T0, "TEST001")
    await store.upsert_aircraft("aaaaaa", T1, None)
    row = await reader.get_aircraft("aaaaaa")
    assert row is not None
    assert row.last_callsign == "TEST001"


async def check_observation_insert(store: Store, reader: StoreReader) -> None:
    await store.upsert_aircraft("aaaaaa", T0, "TEST001")
    await store.insert_observation(_observation())
    stored = await reader.get_observation("aaaaaa", T0)
    assert stored is not None
    assert stored.lat == 35.0
    assert stored.distance_km == 50.0


async def check_duplicate_observation_reprocessing_is_idempotent(
    store: Store, reader: StoreReader
) -> None:
    await store.upsert_aircraft("aaaaaa", T0, "TEST001")
    await store.insert_observation(_observation())
    await store.insert_observation(_observation())  # reprocess the same poll
    assert await reader.count_observations() == 1


async def check_traffic_minute_upsert(store: Store, reader: StoreReader) -> None:
    minute = TrafficMinute(
        bucket_at=T0, active_aircraft_count=3, position_aircraft_count=2, message_count_delta=100
    )
    await store.upsert_traffic_minute(minute)
    updated = TrafficMinute(
        bucket_at=T0, active_aircraft_count=5, position_aircraft_count=2, message_count_delta=150
    )
    await store.upsert_traffic_minute(updated)
    stored = await reader.get_traffic_minute(T0)
    assert stored is not None
    assert stored.active_aircraft_count == 5
    assert stored.message_count_delta == 150


async def check_ingestion_status_success_and_failure_recorded(
    store: Store, reader: StoreReader
) -> None:
    await store.record_ingestion_status(IngestionStatus(T0, True, 12.5, 5, None))
    await store.record_ingestion_status(IngestionStatus(T1, False, None, None, "HTTPError"))
    statuses = await reader.list_ingestion_status()
    assert len(statuses) == 2
    assert statuses[0].success is True
    assert statuses[1].success is False
    assert statuses[1].error_code == "HTTPError"


async def check_timestamps_round_trip_as_utc(store: Store, reader: StoreReader) -> None:
    await store.upsert_aircraft("aaaaaa", T0, "TEST001")
    row = await reader.get_aircraft("aaaaaa")
    assert row is not None
    assert row.last_seen_at.utcoffset().total_seconds() == 0
    assert row.last_seen_at == T0


async def check_close_is_safe_and_idempotent(store: Store, reader: StoreReader) -> None:
    await store.close()
    await store.close()  # must not raise the second time either


CONTRACT_CHECKS = [
    check_aircraft_created_on_first_seen,
    check_last_seen_updates_on_subsequent_poll,
    check_blank_callsign_does_not_clear_existing_callsign,
    check_observation_insert,
    check_duplicate_observation_reprocessing_is_idempotent,
    check_traffic_minute_upsert,
    check_ingestion_status_success_and_failure_recorded,
    check_timestamps_round_trip_as_utc,
    check_close_is_safe_and_idempotent,
]
