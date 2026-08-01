from __future__ import annotations

import json
from datetime import date

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.db.queries.period import DailyTrafficSummary
from app.notify import (
    build_emergency_squawk_payload,
    build_favorite_seen_payload,
    build_payload,
    send_daily_notification,
    send_emergency_squawk_notification,
    send_favorite_seen_notification,
)

SUMMARY = DailyTrafficSummary(
    day=date(2026, 7, 28),
    unique_aircraft_count=42,
    max_concurrent_count=7,
    message_count_total=123456,
    position_aircraft_count_max=5,
    farthest_icao="aaaaaa",
    farthest_distance_km=250.5,
    closest_icao="bbbbbb",
    closest_distance_km=3.2,
    most_observed_icao="cccccc",
    most_observed_count=88,
)


def _settings(**overrides) -> Settings:
    base = dict(
        readsb_aircraft_url="http://127.0.0.1/tar1090/data/aircraft.json",
        receiver_lat=35.0,
        receiver_lon=139.0,
        database_url="postgresql://adsb:pw@localhost:5432/adsb",
    )
    base.update(overrides)
    return Settings(**base)


def test_build_payload_has_slack_compatible_shape():
    payload = build_payload(SUMMARY)
    assert set(payload.keys()) == {"text"}
    text = payload["text"]
    assert "2026-07-28" in text
    assert "42" in text
    assert "aaaaaa" in text
    assert "250.5" in text
    assert "bbbbbb" in text
    assert "cccccc" in text


def test_build_payload_omits_missing_rankings():
    summary = DailyTrafficSummary(
        day=date(2026, 7, 28),
        unique_aircraft_count=0,
        max_concurrent_count=0,
        message_count_total=0,
        position_aircraft_count_max=0,
        farthest_icao=None,
        farthest_distance_km=None,
        closest_icao=None,
        closest_distance_km=None,
        most_observed_icao=None,
        most_observed_count=None,
    )
    payload = build_payload(summary)
    assert "最遠" not in payload["text"]
    assert "最接近" not in payload["text"]
    assert "最多観測" not in payload["text"]


def test_build_payload_never_includes_coordinates_or_secrets():
    payload = build_payload(SUMMARY)
    text_lower = payload["text"].lower()
    assert "lat" not in text_lower
    assert "lon" not in text_lower
    assert "postgresql://" not in payload["text"]


async def test_disabled_by_default_sends_nothing():
    settings = _settings()
    assert settings.notify_webhook_enabled is False

    def _fail_if_called(request: httpx.Request) -> httpx.Response:
        raise AssertionError("webhook must not be called when disabled")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_fail_if_called)) as client:
        await send_daily_notification(settings, SUMMARY, client=client)


async def test_enabled_sends_expected_payload():
    settings = _settings(
        notify_webhook_enabled=True, notify_webhook_url="https://hooks.example.invalid/webhook"
    )
    captured = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_capture)) as client:
        await send_daily_notification(settings, SUMMARY, client=client)

    assert captured["url"] == "https://hooks.example.invalid/webhook"
    assert json.loads(captured["body"]) == build_payload(SUMMARY)


async def test_webhook_failure_does_not_raise():
    settings = _settings(
        notify_webhook_enabled=True, notify_webhook_url="https://hooks.example.invalid/webhook"
    )

    def _server_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_server_error)) as client:
        # Must not raise even though the webhook returns an error status.
        await send_daily_notification(settings, SUMMARY, client=client)


async def test_webhook_connection_error_does_not_raise():
    settings = _settings(
        notify_webhook_enabled=True, notify_webhook_url="https://hooks.example.invalid/webhook"
    )

    def _raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network failure", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_raise_connect_error)) as client:
        await send_daily_notification(settings, SUMMARY, client=client)


def test_enabling_webhook_without_url_is_rejected():
    with pytest.raises(ValidationError):
        _settings(notify_webhook_enabled=True)


def test_notify_webhook_url_must_have_scheme():
    with pytest.raises(ValidationError):
        _settings(notify_webhook_enabled=True, notify_webhook_url="not-a-url")


# --- emergency squawk / favorite seen (Milestone KK) -----------------------


def test_build_emergency_squawk_payload_prefers_callsign():
    payload = build_emergency_squawk_payload("aaaaaa", "7700", callsign="TEST001")
    assert "TEST001" in payload["text"]
    assert "aaaaaa" in payload["text"]
    assert "7700" in payload["text"]


def test_build_emergency_squawk_payload_falls_back_to_icao():
    payload = build_emergency_squawk_payload("aaaaaa", "7500", callsign=None)
    assert payload["text"].count("aaaaaa") >= 1


def test_build_favorite_seen_payload_prefers_callsign():
    payload = build_favorite_seen_payload("bbbbbb", callsign="JAL10")
    assert "JAL10" in payload["text"]
    assert "bbbbbb" in payload["text"]


async def test_emergency_squawk_disabled_by_default_sends_nothing():
    settings = _settings()
    assert settings.notify_emergency_squawk_enabled is False

    def _fail_if_called(request: httpx.Request) -> httpx.Response:
        raise AssertionError("webhook must not be called when disabled")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_fail_if_called)) as client:
        await send_emergency_squawk_notification(settings, "aaaaaa", "7700", client=client)


async def test_emergency_squawk_enabled_sends_expected_payload():
    settings = _settings(
        notify_emergency_squawk_enabled=True,
        notify_webhook_url="https://hooks.example.invalid/webhook",
    )
    captured = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_capture)) as client:
        await send_emergency_squawk_notification(
            settings, "aaaaaa", "7700", callsign="TEST001", client=client
        )

    assert json.loads(captured["body"]) == build_emergency_squawk_payload(
        "aaaaaa", "7700", callsign="TEST001"
    )


async def test_favorite_seen_disabled_by_default_sends_nothing():
    settings = _settings()
    assert settings.notify_favorite_seen_enabled is False

    def _fail_if_called(request: httpx.Request) -> httpx.Response:
        raise AssertionError("webhook must not be called when disabled")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_fail_if_called)) as client:
        await send_favorite_seen_notification(settings, "bbbbbb", client=client)


async def test_favorite_seen_enabled_sends_expected_payload():
    settings = _settings(
        notify_favorite_seen_enabled=True,
        notify_webhook_url="https://hooks.example.invalid/webhook",
    )
    captured = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_capture)) as client:
        await send_favorite_seen_notification(settings, "bbbbbb", callsign="JAL10", client=client)

    assert json.loads(captured["body"]) == build_favorite_seen_payload("bbbbbb", callsign="JAL10")
