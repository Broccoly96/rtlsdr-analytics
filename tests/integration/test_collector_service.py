"""Integration-level tests for CollectorService: readsb outage/recovery and
store-failure resilience, using a mock HTTP transport and an in-memory store
-- never a live network call, and never the production readsb service
(PLAN.md SS8's explicit rule).
"""

from __future__ import annotations

import httpx

from app.collector.service import BACKOFF_INITIAL_SECONDS, CollectorService
from app.collector.store import InMemoryStore

SAMPLE_PAYLOAD = {
    "now": 1700000000.0,
    "messages": 1000,
    "aircraft": [
        {
            "hex": "aaaaaa",
            "flight": "TEST001",
            "seen": 0.5,
            "seen_pos": 0.5,
            "lat": 35.0,
            "lon": 139.0,
            "alt_baro": 1000,
        }
    ],
}


def _client_with_responses(responses: list[httpx.Response]) -> httpx.AsyncClient:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        index = min(calls["count"], len(responses) - 1)
        calls["count"] += 1
        return responses[index]

    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://readsb.test")


def _service(client: httpx.AsyncClient, store) -> CollectorService:
    return CollectorService(
        client=client,
        url="/aircraft.json",
        store=store,
        receiver_lat=35.0,
        receiver_lon=139.0,
        poll_interval_seconds=5.0,
        track_sample_seconds=30.0,
    )


async def test_successful_poll_stores_aircraft_and_observation():
    client = _client_with_responses([httpx.Response(200, json=SAMPLE_PAYLOAD)])
    store = InMemoryStore()
    service = _service(client, store)

    interval = await service.poll_once()

    assert interval == 5.0
    assert "aaaaaa" in store.aircraft
    assert len(store.observations) == 1
    assert store.ingestion_status_log[-1].success is True
    await client.aclose()


async def test_readsb_outage_backs_off_without_crashing_and_recovers():
    responses = [
        httpx.Response(200, json=SAMPLE_PAYLOAD),
        httpx.Response(503, text="unavailable"),
        httpx.Response(503, text="unavailable"),
        httpx.Response(200, json=SAMPLE_PAYLOAD),
    ]
    client = _client_with_responses(responses)
    store = InMemoryStore()
    service = _service(client, store)

    interval1 = await service.poll_once()
    assert interval1 == 5.0  # healthy cadence

    interval2 = await service.poll_once()
    assert interval2 == BACKOFF_INITIAL_SECONDS  # first failure -> initial backoff
    assert store.ingestion_status_log[-1].success is False

    interval3 = await service.poll_once()
    assert interval3 > interval2  # backoff grows -- never hammers readsb with retries

    interval4 = await service.poll_once()
    assert interval4 == 5.0  # recovered -> back to normal cadence
    assert store.ingestion_status_log[-1].success is True
    await client.aclose()


async def test_store_failure_does_not_crash_service_and_stays_bounded():
    class FailingStore(InMemoryStore):
        async def insert_observation(self, observation):
            raise RuntimeError("simulated DB outage")

    client = _client_with_responses([httpx.Response(200, json=SAMPLE_PAYLOAD)])
    store = FailingStore()
    service = _service(client, store)

    interval = await service.poll_once()  # must not raise

    assert interval == 5.0
    assert len(store.observations) == 0
    await client.aclose()


async def test_malformed_payload_does_not_crash_service():
    client = _client_with_responses([httpx.Response(200, json={"aircraft": "not-a-list"})])
    store = InMemoryStore()
    service = _service(client, store)

    interval = await service.poll_once()

    assert interval == 5.0
    assert len(store.observations) == 0


async def test_empty_aircraft_list_does_not_crash_service():
    client = _client_with_responses(
        [httpx.Response(200, json={"now": 1.0, "messages": 1, "aircraft": []})]
    )
    store = InMemoryStore()
    service = _service(client, store)

    interval = await service.poll_once()

    assert interval == 5.0
    assert store.ingestion_status_log[-1].aircraft_count == 0
