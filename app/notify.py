"""Optional Slack/Discord-compatible daily-summary webhook, sent once per
day from app/dailyrollup.py's --loop path, immediately after the previous
day's rollup completes -- the moment that day's data is finalized.

Opt-in via NOTIFY_WEBHOOK_ENABLED (default disabled); absence of a
webhook URL never fails startup on its own (app/config.py only rejects
the combination of enabled=true with no URL configured). A failed or
misconfigured webhook must never break the rollup job that triggers it,
so send_daily_notification never raises -- it logs and returns instead.
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


async def send_daily_notification(
    settings: Settings, summary: DailyTrafficSummary, *, client: httpx.AsyncClient | None = None
) -> None:
    if not settings.notify_webhook_enabled or not settings.notify_webhook_url:
        return

    payload = build_payload(summary)
    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS)
    try:
        response = await http_client.post(settings.notify_webhook_url, json=payload)
        response.raise_for_status()
        logger.info("notify: daily webhook sent for day=%s", summary.day)
    except Exception:
        logger.exception("notify: failed to send daily webhook for day=%s", summary.day)
    finally:
        if owns_client:
            await http_client.aclose()
