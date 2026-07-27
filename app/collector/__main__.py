"""Collector process entrypoint."""

from __future__ import annotations

import asyncio
import logging
import signal

import httpx

from app.collector.service import CollectorService
from app.config import Settings
from app.db.postgres_store import PostgresStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


async def _run(settings: Settings) -> None:
    store = await PostgresStore.connect(settings.database_url)
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
