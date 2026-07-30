"""Once-ever, permanently-cached aircraft type/registration lookups
against api.adsbdb.com, backing the daily aircraft-type chart (Milestone
S). Never called from any GET request path, so a slow or unavailable
upstream never affects page load latency. A type/registration essentially
never changes once assigned, so a successful lookup is cached forever; a
failed lookup (unknown hex, timeout) is cached too, so the same hex isn't
re-queried on every single run -- only retried after a long cooldown, in
case adsbdb.com's own data improves over time.

Runs as its own standalone --loop process (adsb-type-lookup, mirroring
app/retention.py's --loop/--interval pattern) on a short interval, decoupled
from app/dailyrollup.py's once-a-day cycle -- that cadence left the daily
aircraft-type chart (which is supposed to reflect *today's* traffic) stuck
showing only whatever handful of types had been looked up as of yesterday.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from dataclasses import dataclass

import asyncpg
import httpx

from app.config import Settings
from app.db.pool import close_pool, create_pool
from app.version import get_user_agent

logger = logging.getLogger(__name__)

ADSBDB_BASE_URL = "https://api.adsbdb.com/v0/aircraft/"
LOOKUP_TIMEOUT_SECONDS = 5.0
REQUEST_DELAY_SECONDS = 0.5  # good-citizen pacing between requests
FAILED_LOOKUP_RETRY_DAYS = 30
DEFAULT_LOOKUP_LIMIT = 200
DEFAULT_LOOP_INTERVAL_MINUTES = 15.0
QUERY_TIMEOUT_SECONDS = 5.0

_UPSERT_FOUND_SQL = """
    INSERT INTO aircraft_type_cache
        (icao, type_code, type_name, manufacturer, registration, lookup_failed, looked_up_at)
    VALUES ($1, $2, $3, $4, $5, false, now())
    ON CONFLICT (icao) DO UPDATE SET
        type_code = EXCLUDED.type_code,
        type_name = EXCLUDED.type_name,
        manufacturer = EXCLUDED.manufacturer,
        registration = EXCLUDED.registration,
        lookup_failed = false,
        looked_up_at = now()
"""

_UPSERT_FAILED_SQL = """
    INSERT INTO aircraft_type_cache (icao, lookup_failed, looked_up_at)
    VALUES ($1, true, now())
    ON CONFLICT (icao) DO UPDATE SET
        lookup_failed = true,
        looked_up_at = now()
"""


@dataclass(frozen=True, slots=True)
class AircraftTypeInfo:
    type_code: str | None
    type_name: str | None
    manufacturer: str | None
    registration: str | None


async def _lookup_one(client: httpx.AsyncClient, icao: str) -> AircraftTypeInfo | None:
    """None on any failure (not found, timeout, malformed response) -- the
    caller still records that as a failed lookup so it isn't retried
    every run."""
    try:
        response = await client.get(f"{ADSBDB_BASE_URL}{icao}", timeout=LOOKUP_TIMEOUT_SECONDS)
        if response.status_code != 200:
            return None
        aircraft = (response.json() or {}).get("response", {}).get("aircraft")
        if not aircraft:
            return None
        return AircraftTypeInfo(
            type_code=aircraft.get("icao_type") or None,
            type_name=aircraft.get("type") or None,
            manufacturer=aircraft.get("manufacturer") or None,
            registration=aircraft.get("registration") or None,
        )
    except Exception:
        logger.warning("aircraft_lookup: adsbdb.com lookup failed for %s", icao, exc_info=True)
        return None


async def refresh_uncached_aircraft_types(
    pool: asyncpg.Pool,
    *,
    client: httpx.AsyncClient | None = None,
    limit: int = DEFAULT_LOOKUP_LIMIT,
) -> int:
    """Looks up and caches any ever-seen aircraft with no
    aircraft_type_cache row yet (or whose previous lookup failed more than
    FAILED_LOOKUP_RETRY_DAYS ago), up to `limit` per call, most-recently-
    seen first. Returns the number looked up. Never raises -- a single bad
    lookup is logged and skipped, never aborts the whole batch."""
    rows = await pool.fetch(
        f"""
        SELECT a.icao FROM aircraft a
        LEFT JOIN aircraft_type_cache c ON c.icao = a.icao
        WHERE c.icao IS NULL
           OR (c.lookup_failed
               AND c.looked_up_at < now() - interval '{FAILED_LOOKUP_RETRY_DAYS} days')
        ORDER BY a.last_seen_at DESC
        LIMIT $1
        """,
        limit,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    if not rows:
        return 0

    owns_client = client is None
    http_client = client or httpx.AsyncClient(headers={"User-Agent": get_user_agent()})
    looked_up = 0
    try:
        for row in rows:
            icao = row["icao"]
            info = await _lookup_one(http_client, icao)
            if info is not None:
                await pool.execute(
                    _UPSERT_FOUND_SQL,
                    icao,
                    info.type_code,
                    info.type_name,
                    info.manufacturer,
                    info.registration,
                    timeout=QUERY_TIMEOUT_SECONDS,
                )
            else:
                await pool.execute(_UPSERT_FAILED_SQL, icao, timeout=QUERY_TIMEOUT_SECONDS)
            looked_up += 1
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
    finally:
        if owns_client:
            await http_client.aclose()

    logger.info("aircraft_lookup: refreshed %d aircraft type cache entries", looked_up)
    return looked_up


async def _run_once(settings: Settings, *, limit: int) -> int:
    pool = await create_pool(settings.database_url, min_size=1, max_size=1)
    try:
        return await refresh_uncached_aircraft_types(pool, limit=limit)
    finally:
        await close_pool(pool)


async def _run_loop(settings: Settings, *, limit: int, interval_minutes: float) -> None:
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopping.set)

    logger.info(
        "aircraft_lookup: loop starting, interval=%.1f minutes, limit=%d",
        interval_minutes,
        limit,
    )
    while not stopping.is_set():
        try:
            looked_up = await _run_once(settings, limit=limit)
            logger.info("aircraft_lookup: cycle complete, refreshed=%d", looked_up)
        except Exception:
            logger.exception("aircraft_lookup: run failed, will retry next cycle")
        try:
            await asyncio.wait_for(stopping.wait(), timeout=interval_minutes * 60)
        except TimeoutError:
            pass
    logger.info("aircraft_lookup: loop stopped")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Look up and permanently cache aircraft type/registration info "
        "against api.adsbdb.com for any ever-seen aircraft not cached yet."
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LOOKUP_LIMIT)
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, sleeping --interval-minutes between passes, until SIGTERM/SIGINT",
    )
    parser.add_argument("--interval-minutes", type=float, default=DEFAULT_LOOP_INTERVAL_MINUTES)
    args = parser.parse_args()

    try:
        settings = Settings()
    except Exception as exc:
        logger.error("invalid configuration: %s", exc)
        raise SystemExit(1) from exc

    if args.loop:
        asyncio.run(_run_loop(settings, limit=args.limit, interval_minutes=args.interval_minutes))
        return

    looked_up = asyncio.run(_run_once(settings, limit=args.limit))
    print(f"refreshed {looked_up} aircraft type cache entries")


if __name__ == "__main__":
    main()
