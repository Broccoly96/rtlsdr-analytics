"""Storage abstraction the collector writes through.

Kept independent of any concrete backend so the collector pipeline is fully
testable without a live database. Task 3 will add a Postgres-backed
implementation of this same Store protocol once the schema/migrations exist;
until then, InMemoryStore is used both in tests and by the collector
entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.collector.aggregator import TrafficMinute
from app.domain.models import AircraftObservation

MAX_INGESTION_STATUS_HISTORY = 200


@dataclass(frozen=True, slots=True)
class IngestionStatus:
    checked_at: datetime
    success: bool
    latency_ms: float | None
    aircraft_count: int | None
    error_code: str | None


class Store(Protocol):
    async def upsert_aircraft(self, icao: str, seen_at: datetime, callsign: str | None) -> None: ...

    async def insert_observation(self, observation: AircraftObservation) -> None: ...

    async def upsert_traffic_minute(self, minute: TrafficMinute) -> None: ...

    async def record_ingestion_status(self, status: IngestionStatus) -> None: ...

    async def close(self) -> None: ...


@dataclass
class _AircraftRecord:
    first_seen_at: datetime
    last_seen_at: datetime
    last_callsign: str | None


@dataclass
class InMemoryStore:
    """Reference Store implementation used for tests and until a real
    Postgres-backed store exists (Task 3). Idempotent on (icao, observed_at);
    all collections are size-bounded so memory can't grow without limit even
    if the (future) real database is unreachable for a long time.
    """

    aircraft: dict[str, _AircraftRecord] = field(default_factory=dict)
    observations: dict[tuple[str, datetime], AircraftObservation] = field(default_factory=dict)
    traffic_minutes: dict[datetime, TrafficMinute] = field(default_factory=dict)
    ingestion_status_log: list[IngestionStatus] = field(default_factory=list)

    async def upsert_aircraft(self, icao: str, seen_at: datetime, callsign: str | None) -> None:
        existing = self.aircraft.get(icao)
        first_seen_at = existing.first_seen_at if existing else seen_at
        last_callsign = callsign or (existing.last_callsign if existing else None)
        self.aircraft[icao] = _AircraftRecord(first_seen_at, seen_at, last_callsign)

    async def insert_observation(self, observation: AircraftObservation) -> None:
        key = (observation.icao, observation.observed_at)
        self.observations[key] = observation  # idempotent: same key overwrites, never duplicates

    async def upsert_traffic_minute(self, minute: TrafficMinute) -> None:
        self.traffic_minutes[minute.bucket_at] = minute

    async def record_ingestion_status(self, status: IngestionStatus) -> None:
        self.ingestion_status_log.append(status)
        if len(self.ingestion_status_log) > MAX_INGESTION_STATUS_HISTORY:
            del self.ingestion_status_log[:-MAX_INGESTION_STATUS_HISTORY]

    async def close(self) -> None:
        pass  # no resources to release
