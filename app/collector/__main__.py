"""Collector process entrypoint."""

from __future__ import annotations

import asyncio
import logging
import signal

import httpx

from app.collector.service import CollectorService
from app.config import Settings
from app.db.postgres_store import PostgresStore
from app.notify import send_emergency_squawk_notification, send_favorite_seen_notification

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
# HTTP 2xx request logs are high-volume at the collector's five-second poll
# cadence.  Keep warnings/errors visible while avoiding a Docker-log write for
# every successful request (and its associated microSD churn).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def _run(settings: Settings) -> None:
    store = await PostgresStore.connect(settings.database_url)

    async def notify_emergency_squawk(icao: str, squawk: str, callsign: str | None) -> None:
        await send_emergency_squawk_notification(settings, icao, squawk, callsign=callsign)

    async def notify_favorite_seen(icao: str, callsign: str | None) -> None:
        await send_favorite_seen_notification(settings, icao, callsign=callsign)

    try:
        async with httpx.AsyncClient() as client:
            service = CollectorService(
                client=client,
                url=settings.readsb_aircraft_url,
                store=store,
                receiver_lat=settings.receiver_lat,
                receiver_lon=settings.receiver_lon,
                poll_interval_seconds=settings.poll_interval_seconds,
                track_sample_seconds=settings.track_sample_seconds,
                emergency_squawk_enabled=settings.notify_emergency_squawk_enabled,
                favorite_seen_enabled=settings.notify_favorite_seen_enabled,
                notify_emergency_squawk=notify_emergency_squawk,
                notify_favorite_seen=notify_favorite_seen,
            )

            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, service.stop)

            logger.info("collector starting, polling %s", settings.readsb_aircraft_url)
            await service.run_forever()
            logger.info("collector stopped")
    finally:
        await store.close()


def main() -> None:
    try:
        settings = Settings()
    except Exception as exc:
        logger.error("invalid configuration: %s", exc)
        raise SystemExit(1) from exc
    asyncio.run(_run(settings))


if __name__ == "__main__":
    main()
