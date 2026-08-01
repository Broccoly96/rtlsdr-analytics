"""Integration-level tests for CollectorService: readsb outage/recovery and
store-failure resilience, using a mock HTTP transport and an in-memory store
-- never a live network call, and never the production readsb service
(PLAN.md SS8's explicit rule).
"""

from __future__ import annotations

import logging

import httpx

from app.collector.service import (
    BACKOFF_INITIAL_SECONDS,
    INGESTION_STATUS_INTERVAL_SECONDS,
    CollectorService,
)
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


def _service(client: httpx.AsyncClient, store, **kwargs) -> CollectorService:
    return CollectorService(
        client=client,
        url="/aircraft.json",
        store=store,
        receiver_lat=35.0,
        receiver_lon=139.0,
        poll_interval_seconds=5.0,
        track_sample_seconds=30.0,
        **kwargs,
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


async def test_success_status_is_checkpointed_every_30_seconds():
    client = _client_with_responses([httpx.Response(200, json=SAMPLE_PAYLOAD)])
    store = InMemoryStore()
    service = _service(client, store)

    await service.poll_once()  # first successful poll is always persisted
    assert len(store.ingestion_status_log) == 1

    await service.poll_once()  # normal 5-second poll remains below checkpoint interval
    assert len(store.ingestion_status_log) == 1

    service._last_ingestion_status_at -= INGESTION_STATUS_INTERVAL_SECONDS
    await service.poll_once()
    assert len(store.ingestion_status_log) == 2
    await client.aclose()


async def test_success_status_checkpoint_timer_advances_only_after_store_success():
    class FailFirstStatusStore(InMemoryStore):
        status_calls = 0

        async def record_ingestion_status(self, status):
            self.status_calls += 1
            if self.status_calls == 1:
                raise RuntimeError("simulated status DB outage")
            await super().record_ingestion_status(status)

    client = _client_with_responses([httpx.Response(200, json=SAMPLE_PAYLOAD)])
    store = FailFirstStatusStore()
    service = _service(client, store)

    await service.poll_once()
    assert store.ingestion_status_log == []
    assert service._last_ingestion_status_at is None

    await service.poll_once()
    assert len(store.ingestion_status_log) == 1
    assert store.status_calls == 2
    assert service._last_ingestion_status_at is not None
    await client.aclose()


async def test_readsb_outage_backs_off_without_crashing_and_recovers(caplog):
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

    with caplog.at_level(logging.WARNING):
        interval2 = await service.poll_once()
    assert interval2 == BACKOFF_INITIAL_SECONDS  # first failure -> initial backoff
    assert store.ingestion_status_log[-1].success is False
    assert "readsb fetch failed" in caplog.text  # PLAN.md E-4: failures are logged

    interval3 = await service.poll_once()
    assert interval3 > interval2  # backoff grows -- never hammers readsb with retries

    with caplog.at_level(logging.INFO):
        caplog.clear()
        interval4 = await service.poll_once()
    assert interval4 == 5.0  # recovered -> back to normal cadence
    assert store.ingestion_status_log[-1].success is True
    assert "recovered" in caplog.text  # PLAN.md E-4: recovery is logged too, not just failure
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


async def test_excluded_records_are_logged(caplog):
    payload = {
        "now": 1.0,
        "messages": 1,
        "aircraft": [
            {"hex": "aaaaaa", "seen": 0.5, "seen_pos": 0.5, "lat": 35.0, "lon": 139.0},
            "not-a-dict",  # excluded_reasons["not_a_dict"]
            {"seen": 0.5},  # missing hex -> excluded_reasons["missing_hex"]
        ],
    }
    client = _client_with_responses([httpx.Response(200, json=payload)])
    store = InMemoryStore()
    service = _service(client, store)

    with caplog.at_level(logging.DEBUG):
        await service.poll_once()

    # PLAN.md E-4: the count of excluded/invalid records must be logged, not
    # silently discarded (normalize_poll already computes this; the gap was
    # that poll_once never actually logged it).
    assert "excluded 2" in caplog.text
    assert "not_a_dict" in caplog.text
    assert "missing_hex" in caplog.text


async def test_excluded_records_are_not_logged_at_info(caplog):
    payload = {
        "now": 1.0,
        "messages": 1,
        "aircraft": [{"hex": "aaaaaa"}, "not-a-dict"],
    }
    client = _client_with_responses([httpx.Response(200, json=payload)])
    service = _service(client, InMemoryStore())

    with caplog.at_level(logging.INFO):
        await service.poll_once()

    assert "poll excluded" not in caplog.text
    await client.aclose()


async def test_empty_aircraft_list_does_not_crash_service():
    client = _client_with_responses(
        [httpx.Response(200, json={"now": 1.0, "messages": 1, "aircraft": []})]
    )
    store = InMemoryStore()
    service = _service(client, store)

    interval = await service.poll_once()

    assert interval == 5.0
    assert store.ingestion_status_log[-1].aircraft_count == 0


# --- Milestone KK: emergency squawk / favorite-seen event watchers --------


def _squawk_payload(icao: str, squawk: str, callsign: str = "TEST001") -> dict:
    return {
        "now": 1.0,
        "messages": 1,
        "aircraft": [
            {
                "hex": icao,
                "flight": callsign,
                "seen": 0.5,
                "seen_pos": 0.5,
                "lat": 35.0,
                "lon": 139.0,
                "alt_baro": 1000,
                "squawk": squawk,
            }
        ],
    }


async def test_emergency_squawk_disabled_by_default_never_notifies():
    calls = []

    async def notify(icao, squawk, callsign):
        calls.append((icao, squawk, callsign))

    client = _client_with_responses([httpx.Response(200, json=_squawk_payload("aaaaaa", "7700"))])
    service = _service(client, InMemoryStore(), notify_emergency_squawk=notify)

    await service.poll_once()

    assert calls == []
    await client.aclose()


async def test_emergency_squawk_notifies_once_on_transition_not_every_poll():
    calls = []

    async def notify(icao, squawk, callsign):
        calls.append((icao, squawk, callsign))

    payload = _squawk_payload("aaaaaa", "7700")
    client = _client_with_responses([httpx.Response(200, json=payload)])
    service = _service(
        client, InMemoryStore(), emergency_squawk_enabled=True, notify_emergency_squawk=notify
    )

    await service.poll_once()
    await service.poll_once()  # still squawking 7700 -- must not re-notify

    assert calls == [("aaaaaa", "7700", "TEST001")]
    await client.aclose()


async def test_emergency_squawk_renotifies_after_clearing_and_recurring():
    calls = []

    async def notify(icao, squawk, callsign):
        calls.append((icao, squawk, callsign))

    responses = [
        httpx.Response(200, json=_squawk_payload("aaaaaa", "7700")),
        httpx.Response(200, json=_squawk_payload("aaaaaa", "2000")),  # cleared
        httpx.Response(200, json=_squawk_payload("aaaaaa", "7700")),  # recurs
    ]
    client = _client_with_responses(responses)
    service = _service(
        client, InMemoryStore(), emergency_squawk_enabled=True, notify_emergency_squawk=notify
    )

    await service.poll_once()
    await service.poll_once()
    await service.poll_once()

    assert len(calls) == 2
    await client.aclose()


async def test_non_emergency_squawk_never_notifies():
    calls = []

    async def notify(icao, squawk, callsign):
        calls.append((icao, squawk, callsign))

    client = _client_with_responses([httpx.Response(200, json=_squawk_payload("aaaaaa", "2000"))])
    service = _service(
        client, InMemoryStore(), emergency_squawk_enabled=True, notify_emergency_squawk=notify
    )

    await service.poll_once()

    assert calls == []
    await client.aclose()


async def test_favorite_seen_disabled_by_default_never_notifies():
    calls = []

    async def notify(icao, callsign):
        calls.append((icao, callsign))

    store = InMemoryStore(favorite_icaos={"aaaaaa"})
    client = _client_with_responses([httpx.Response(200, json=SAMPLE_PAYLOAD)])
    service = _service(client, store, notify_favorite_seen=notify)

    await service.poll_once()

    assert calls == []
    await client.aclose()


async def test_favorite_seen_notifies_once_on_transition_not_every_poll():
    calls = []

    async def notify(icao, callsign):
        calls.append((icao, callsign))

    store = InMemoryStore(favorite_icaos={"aaaaaa"})
    client = _client_with_responses([httpx.Response(200, json=SAMPLE_PAYLOAD)])
    service = _service(
        client, store, favorite_seen_enabled=True, notify_favorite_seen=notify
    )

    await service.poll_once()
    await service.poll_once()  # still present -- must not re-notify

    assert calls == [("aaaaaa", "TEST001")]
    await client.aclose()


async def test_non_favorite_aircraft_never_notifies():
    calls = []

    async def notify(icao, callsign):
        calls.append((icao, callsign))

    store = InMemoryStore(favorite_icaos={"zzzzzz"})  # not the aircraft in SAMPLE_PAYLOAD
    client = _client_with_responses([httpx.Response(200, json=SAMPLE_PAYLOAD)])
    service = _service(
        client, store, favorite_seen_enabled=True, notify_favorite_seen=notify
    )

    await service.poll_once()

    assert calls == []
    await client.aclose()
