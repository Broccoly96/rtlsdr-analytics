"""The collector's polling loop: fetch readsb -> normalize -> sample ->
store, with exponential backoff on failure and graceful shutdown.

Store writes are best-effort per record: a failure writing one aircraft's
observation is logged and skipped rather than aborting the whole poll, and a
failed poll never retries aggressively against readsb -- it just backs off
and tries again next cycle.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime

import httpx

from app.collector.aggregator import MinuteAggregator
from app.collector.normalize import normalize_poll
from app.collector.sampling import PositionSampler
from app.collector.store import IngestionStatus, Store
from app.domain.models import ReceptionState

logger = logging.getLogger(__name__)

FETCH_TIMEOUT_SECONDS = 5.0
BACKOFF_INITIAL_SECONDS = 5.0
BACKOFF_MAX_SECONDS = 300.0
BACKOFF_MULTIPLIER = 2.0
INGESTION_STATUS_INTERVAL_SECONDS = 30.0


class CollectorService:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        url: str,
        store: Store,
        receiver_lat: float,
        receiver_lon: float,
        poll_interval_seconds: float,
        track_sample_seconds: float,
    ) -> None:
        self._client = client
        self._url = url
        self._store = store
        self._receiver_lat = receiver_lat
        self._receiver_lon = receiver_lon
        self._poll_interval_seconds = poll_interval_seconds
        self._sampler = PositionSampler(track_sample_seconds)
        self._aggregator = MinuteAggregator()
        self._backoff_seconds = BACKOFF_INITIAL_SECONDS
        self._stopping = asyncio.Event()
        # A successful status checkpoint is deliberately less frequent than
        # the readsb poll cadence.  Keep this as monotonic time so wall-clock
        # adjustments cannot make checkpoints fire early or stop entirely.
        self._last_ingestion_status_at: float | None = None
        # The first successful poll after a readsb outage is always recorded,
        # even if the normal checkpoint interval has not elapsed yet.
        self._ingestion_status_needs_recovery = False

    def stop(self) -> None:
        self._stopping.set()

    async def run_forever(self) -> None:
        while not self._stopping.is_set():
            interval = await self.poll_once()
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=interval)
            except TimeoutError:
                pass
        completed = self._aggregator.flush()
        if completed is not None:
            await self._safe_store_call(
                self._store.upsert_traffic_minute(completed), "traffic minute"
            )

    async def poll_once(self) -> float:
        """Run a single fetch-normalize-store cycle. Returns the number of
        seconds to wait before the next poll (normal cadence, or backoff)."""
        polled_at = datetime.now(UTC)
        start = time.monotonic()
        try:
            response = await self._client.get(self._url, timeout=FETCH_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            latency_ms = (time.monotonic() - start) * 1000
            logger.warning("readsb fetch failed: %s", exc)
            self._ingestion_status_needs_recovery = True
            await self._safe_store_call(
                self._store.record_ingestion_status(
                    IngestionStatus(polled_at, False, latency_ms, None, type(exc).__name__)
                ),
                "ingestion status (failure)",
            )
            interval = self._backoff_seconds
            self._backoff_seconds = min(
                self._backoff_seconds * BACKOFF_MULTIPLIER, BACKOFF_MAX_SECONDS
            )
            return interval

        latency_ms = (time.monotonic() - start) * 1000
        if self._backoff_seconds > BACKOFF_INITIAL_SECONDS:
            logger.info("readsb fetch recovered after backoff")
        self._backoff_seconds = BACKOFF_INITIAL_SECONDS  # reset cadence on recovery

        result = normalize_poll(payload, polled_at, self._receiver_lat, self._receiver_lon)
        if result.excluded_reasons:
            logger.debug(
                "poll excluded %d record(s): %s",
                sum(result.excluded_reasons.values()),
                result.excluded_reasons,
            )
        await self._store_observations(result.observations, polled_at)
        self._forget_dropped_aircraft({o.icao for o in result.observations})

        messages_total = payload.get("messages") if isinstance(payload, dict) else None
        completed_minute = self._aggregator.record_poll(
            polled_at, result.received_count, result.position_acquired_count, messages_total
        )
        if completed_minute is not None:
            await self._safe_store_call(
                self._store.upsert_traffic_minute(completed_minute), "traffic minute"
            )

        await self._record_success_status_if_due(
            IngestionStatus(polled_at, True, latency_ms, result.received_count, None)
        )

        return self._poll_interval_seconds

    async def _store_observations(self, observations, polled_at: datetime) -> None:
        for observation in observations:
            await self._safe_store_call(
                self._store.upsert_aircraft(observation.icao, polled_at, observation.callsign),
                f"aircraft upsert for {observation.icao}",
            )
            should_persist_position = (
                observation.reception_state == ReceptionState.POSITION_ACQUIRED
                and observation.lat is not None
                and observation.lon is not None
                and self._sampler.should_sample(
                    observation.icao,
                    polled_at.timestamp(),
                    observation.lat,
                    observation.lon,
                    observation.altitude_ft,
                )
            )
            if should_persist_position:
                await self._safe_store_call(
                    self._store.insert_observation(observation),
                    f"observation insert for {observation.icao}",
                )

    def _forget_dropped_aircraft(self, seen_icaos: set[str]) -> None:
        for icao in self._sampler.tracked_icaos() - seen_icaos:
            self._sampler.forget(icao)

    @staticmethod
    async def _safe_store_call(coro, description: str) -> bool:
        try:
            await coro
            return True
        except Exception:
            logger.exception("store write failed (%s); continuing", description)
            return False

    async def _record_success_status_if_due(self, status: IngestionStatus) -> None:
        now = time.monotonic()
        is_due = (
            self._last_ingestion_status_at is None
            or self._ingestion_status_needs_recovery
            or now - self._last_ingestion_status_at >= INGESTION_STATUS_INTERVAL_SECONDS
        )
        if not is_due:
            return

        saved = await self._safe_store_call(
            self._store.record_ingestion_status(status), "ingestion status (success)"
        )
        # Advance the checkpoint only after the write has completed
        # successfully.  A failed write will therefore be retried on the next
        # eligible poll rather than silently extending the checkpoint window.
        if saved:
            self._last_ingestion_status_at = time.monotonic()
            self._ingestion_status_needs_recovery = False
