from __future__ import annotations

from datetime import datetime

import pytest

from app.collector.aggregator import TrafficMinute
from app.collector.store import IngestionStatus, InMemoryStore
from app.domain.models import AircraftObservation
from tests.contract.store_contract import CONTRACT_CHECKS, AircraftRow


class InMemoryStoreReader:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_aircraft(self, icao: str) -> AircraftRow | None:
        record = self._store.aircraft.get(icao)
        if record is None:
            return None
        return AircraftRow(icao, record.first_seen_at, record.last_seen_at, record.last_callsign)

    async def count_observations(self) -> int:
        return len(self._store.observations)

    async def get_observation(self, icao: str, observed_at: datetime) -> AircraftObservation | None:
        return self._store.observations.get((icao, observed_at))

    async def get_traffic_minute(self, bucket_at: datetime) -> TrafficMinute | None:
        return self._store.traffic_minutes.get(bucket_at)

    async def list_ingestion_status(self) -> list[IngestionStatus]:
        return list(self._store.ingestion_status_log)


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.mark.parametrize("check", CONTRACT_CHECKS, ids=lambda f: f.__name__)
async def test_contract(check, store: InMemoryStore) -> None:
    await check(store, InMemoryStoreReader(store))
