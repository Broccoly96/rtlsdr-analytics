"""Collector process entrypoint.

Task 3 will add a Postgres-backed Store; until then this runs against an
in-memory store, which exercises the full collector pipeline but does not
persist across restarts.
"""

from __future__ import annotations

import asyncio
import logging
import signal

import httpx

from app.collector.service import CollectorService
from app.collector.store import InMemoryStore
from app.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


async def _run(settings: Settings) -> None:
    store = InMemoryStore()  # TODO(Task 3): swap for a Postgres-backed Store

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


def main() -> None:
    try:
        settings = Settings()
    except Exception as exc:
        logger.error("invalid configuration: %s", exc)
        raise SystemExit(1) from exc
    asyncio.run(_run(settings))


if __name__ == "__main__":
    main()
