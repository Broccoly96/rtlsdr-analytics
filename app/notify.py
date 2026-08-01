"""Optional Slack/Discord-compatible webhook notifications. Three event
types share the one send_webhook() sender below:
  - daily summary, sent once per day from app/dailyrollup.py's --loop
    path, immediately after the previous day's rollup completes
  - emergency squawk (7500/7600/7700) transitions, sent from
    app/collector/service.py on every poll
  - "favorite aircraft seen" transitions, also from the collector

Each event type is independently opt-in (NOTIFY_WEBHOOK_ENABLED,
NOTIFY_EMERGENCY_SQUAWK_ENABLED, NOTIFY_FAVORITE_SEEN_ENABLED -- all
default disabled) but they all post to the same NOTIFY_WEBHOOK_URL;
absence of a webhook URL never fails startup on its own (app/config.py
only rejects enabling any of the three with no URL configured). A
failed or misconfigured webhook must never break the job that triggers
it, so send_webhook never raises -- it logs and returns instead.
"""

from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.db.queries.period import DailyTrafficSummary

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5.0


def build_payload(summary: DailyTrafficSummary) -> dict:
    """Slack-compatible {"text": ...} payload. Aircraft counts/rankings
    only -- never raw coordinates or other secrets (the same "never leak
    details" discipline as app/api/errors.py)."""
    lines = [
        f"*{summary.day.isoformat()} の受信サマリー*",
        f"ユニーク機数: {summary.unique_aircraft_count}機",
        f"最大同時受信数: {summary.max_concurrent_count}機",
        f"メッセージ数: {summary.message_count_total:,}",
    ]
    if summary.farthest_icao and summary.farthest_distance_km is not None:
        lines.append(f"最遠: {summary.farthest_icao} ({summary.farthest_distance_km:.1f} km)")
    if summary.closest_icao and summary.closest_distance_km is not None:
        lines.append(f"最接近: {summary.closest_icao} ({summary.closest_distance_km:.1f} km)")
    if summary.most_observed_icao and summary.most_observed_count is not None:
        lines.append(f"最多観測: {summary.most_observed_icao} ({summary.most_observed_count}回)")
    return {"text": "\n".join(lines)}


def build_emergency_squawk_payload(icao: str, squawk: str, *, callsign: str | None = None) -> dict:
    label = callsign or icao
    return {"text": f"🚨 緊急スコーク検知: {label} ({icao}) がsquawk {squawk} を発信しています"}


def build_favorite_seen_payload(icao: str, *, callsign: str | None = None) -> dict:
    label = callsign or icao
    return {"text": f"⭐ お気に入り機体を検知: {label} ({icao}) を受信中です"}


async def send_webhook(
    settings: Settings, payload: dict, *, client: httpx.AsyncClient | None = None
) -> None:
    """Shared sender for every webhook event type -- callers decide
    whether to call this at all (each event type's own enabled flag),
    this function only knows how to post a payload to notify_webhook_url."""
    if not settings.notify_webhook_url:
        return

    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS)
    try:
        response = await http_client.post(settings.notify_webhook_url, json=payload)
        response.raise_for_status()
        logger.info("notify: webhook sent")
    except Exception:
        logger.exception("notify: failed to send webhook")
    finally:
        if owns_client:
            await http_client.aclose()


async def send_daily_notification(
    settings: Settings, summary: DailyTrafficSummary, *, client: httpx.AsyncClient | None = None
) -> None:
    if not settings.notify_webhook_enabled:
        return
    await send_webhook(settings, build_payload(summary), client=client)


async def send_emergency_squawk_notification(
    settings: Settings,
    icao: str,
    squawk: str,
    *,
    callsign: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> None:
    if not settings.notify_emergency_squawk_enabled:
        return
    await send_webhook(
        settings, build_emergency_squawk_payload(icao, squawk, callsign=callsign), client=client
    )


async def send_favorite_seen_notification(
    settings: Settings,
    icao: str,
    *,
    callsign: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> None:
    if not settings.notify_favorite_seen_enabled:
        return
    await send_webhook(
        settings, build_favorite_seen_payload(icao, callsign=callsign), client=client
    )
