"""Computes and persists one finished calendar day's rollup into
traffic_day, aircraft_day, and aircraft_callsign_history, so Milestone
M/N/O's long-horizon features have data to read once `observations` ages
out of RAW_RETENTION_DAYS (see app/retention.py). This is a standalone
job that reads after the fact, modeled 1:1 on app/retention.py's
structure -- it is not part of the collector's poll/write loop.

Runs once per day (--loop, sleeping until ~00:10 in DISPLAY_TIMEZONE by
default, then rolling up the previous day) or on demand (--day YYYY-MM-DD
for manual backfill, --dry-run to preview without writing).

A Postgres advisory lock (a key distinct from retention.py's 84372910/
84372911) prevents two rollup runs from overlapping. All three tables are
written idempotently via ON CONFLICT ... DO UPDATE, so re-running the
same day (a manual backfill re-run, or the --loop daemon catching up
after a restart) never duplicates or corrupts previously-written rows.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg

from app.config import Settings
from app.db.pool import close_pool, create_pool
from app.db.queries.period import compute_daily_summary, get_traffic_day
from app.domain.daytime import day_bounds_utc, yesterday_in_tz
from app.notify import send_daily_notification

logger = logging.getLogger(__name__)

_ADVISORY_LOCK_KEY = 84372950
MAX_PASS_GAP_SECONDS = 120.0  # same gap-segmentation technique as tracks.py's MAX_GAP_SECONDS
QUERY_TIMEOUT_SECONDS = 5.0
DEFAULT_LOOP_HOUR = 0
DEFAULT_LOOP_MINUTE = 10

_UPSERT_TRAFFIC_DAY_SQL = """
    INSERT INTO traffic_day (
        day, unique_aircraft_count, max_concurrent_count, message_count_total,
        position_aircraft_count_max, farthest_icao, farthest_distance_km,
        closest_icao, closest_distance_km, most_observed_icao, most_observed_count,
        computed_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now())
    ON CONFLICT (day) DO UPDATE SET
        unique_aircraft_count = EXCLUDED.unique_aircraft_count,
        max_concurrent_count = EXCLUDED.max_concurrent_count,
        message_count_total = EXCLUDED.message_count_total,
        position_aircraft_count_max = EXCLUDED.position_aircraft_count_max,
        farthest_icao = EXCLUDED.farthest_icao,
        farthest_distance_km = EXCLUDED.farthest_distance_km,
        closest_icao = EXCLUDED.closest_icao,
        closest_distance_km = EXCLUDED.closest_distance_km,
        most_observed_icao = EXCLUDED.most_observed_icao,
        most_observed_count = EXCLUDED.most_observed_count,
        computed_at = now()
"""

_UPSERT_AIRCRAFT_DAY_SQL = """
    INSERT INTO aircraft_day (icao, day, pass_count, observation_count)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (icao, day) DO UPDATE SET
        pass_count = EXCLUDED.pass_count,
        observation_count = EXCLUDED.observation_count
"""

_UPSERT_CALLSIGN_HISTORY_SQL = """
    INSERT INTO aircraft_callsign_history (icao, callsign, first_seen_at, last_seen_at)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (icao, callsign) DO UPDATE SET
        first_seen_at = LEAST(aircraft_callsign_history.first_seen_at, EXCLUDED.first_seen_at),
        last_seen_at = GREATEST(aircraft_callsign_history.last_seen_at, EXCLUDED.last_seen_at)
"""


@dataclass(frozen=True, slots=True)
class RollupResult:
    day: date
    dry_run: bool
    lock_skipped: bool = False
    aircraft_count: int = 0
    traffic_day_written: bool = False


def count_passes(observed_ats: list[datetime]) -> int:
    """Number of gap-separated passes in a sorted list of one aircraft's
    observation timestamps for a day -- consecutive observations more than
    MAX_PASS_GAP_SECONDS apart start a new pass."""
    if not observed_ats:
        return 0
    passes = 1
    for prev, curr in zip(observed_ats, observed_ats[1:], strict=False):
        if (curr - prev).total_seconds() > MAX_PASS_GAP_SECONDS:
            passes += 1
    return passes


def next_run_at(now_utc: datetime, tz_name: str, hour: int, minute: int) -> datetime:
    """The next UTC instant at which `hour:minute` next occurs in `tz_name`,
    strictly after `now_utc`."""
    tz = ZoneInfo(tz_name)
    now_local = now_utc.astimezone(tz)
    candidate_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate_local <= now_local:
        candidate_local += timedelta(days=1)
    return candidate_local.astimezone(UTC)


async def _write_aircraft_day_and_callsigns(
    pool: asyncpg.Pool, day: date, start_utc: datetime, end_utc: datetime
) -> int:
    rows = await pool.fetch(
        """
        SELECT icao, callsign, observed_at
        FROM observations
        WHERE observed_at >= $1 AND observed_at < $2
        ORDER BY icao, observed_at
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )

    by_icao: dict[str, list] = {}
    for row in rows:
        by_icao.setdefault(row["icao"], []).append(row)

    for icao, icao_rows in by_icao.items():
        observed_ats = [row["observed_at"] for row in icao_rows]
        pass_count = count_passes(observed_ats)
        await pool.execute(
            _UPSERT_AIRCRAFT_DAY_SQL,
            icao,
            day,
            pass_count,
            len(icao_rows),
            timeout=QUERY_TIMEOUT_SECONDS,
        )

        callsign_times: dict[str, list[datetime]] = {}
        for row in icao_rows:
            if row["callsign"]:
                callsign_times.setdefault(row["callsign"], []).append(row["observed_at"])
        for callsign, times in callsign_times.items():
            await pool.execute(
                _UPSERT_CALLSIGN_HISTORY_SQL,
                icao,
                callsign,
                min(times),
                max(times),
                timeout=QUERY_TIMEOUT_SECONDS,
            )

    return len(by_icao)


async def run_rollup(
    pool: asyncpg.Pool, *, day: date, tz_name: str, dry_run: bool = False
) -> RollupResult:
    start_utc, end_utc = day_bounds_utc(day, tz_name)

    if dry_run:
        summary = await compute_daily_summary(pool, day, start_utc, end_utc)
        aircraft_count = await pool.fetchval(
            "SELECT count(DISTINCT icao) FROM observations "
            "WHERE observed_at >= $1 AND observed_at < $2",
            start_utc,
            end_utc,
            timeout=QUERY_TIMEOUT_SECONDS,
        )
        logger.info(
            "dailyrollup: [dry-run] day=%s aircraft=%d summary=%s", day, aircraft_count, summary
        )
        return RollupResult(day, dry_run=True, aircraft_count=aircraft_count)

    lock_conn = await pool.acquire()
    try:
        got_lock = await lock_conn.fetchval("SELECT pg_try_advisory_lock($1)", _ADVISORY_LOCK_KEY)
        if not got_lock:
            logger.warning("dailyrollup: another run already holds the advisory lock, skipping")
            return RollupResult(day, dry_run=False, lock_skipped=True)

        try:
            summary = await compute_daily_summary(pool, day, start_utc, end_utc)
            await pool.execute(
                _UPSERT_TRAFFIC_DAY_SQL,
                summary.day,
                summary.unique_aircraft_count,
                summary.max_concurrent_count,
                summary.message_count_total,
                summary.position_aircraft_count_max,
                summary.farthest_icao,
                summary.farthest_distance_km,
                summary.closest_icao,
                summary.closest_distance_km,
                summary.most_observed_icao,
                summary.most_observed_count,
                timeout=QUERY_TIMEOUT_SECONDS,
            )
            aircraft_count = await _write_aircraft_day_and_callsigns(pool, day, start_utc, end_utc)
        finally:
            await lock_conn.execute("SELECT pg_advisory_unlock($1)", _ADVISORY_LOCK_KEY)
    finally:
        await pool.release(lock_conn)

    logger.info("dailyrollup: complete day=%s aircraft=%d", day, aircraft_count)
    return RollupResult(day, dry_run=False, aircraft_count=aircraft_count, traffic_day_written=True)


async def _run_once(settings: Settings, *, day: date, dry_run: bool) -> RollupResult:
    # max_size=2, not retention.py's max_size=1: run_rollup holds one
    # connection for the advisory lock while compute_daily_summary/the
    # aircraft-day writes acquire their own connections from the same pool.
    pool = await create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        return await run_rollup(pool, day=day, tz_name=settings.display_timezone, dry_run=dry_run)
    finally:
        await close_pool(pool)


async def _run_loop(settings: Settings, *, hour: int, minute: int) -> None:
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopping.set)

    pool = await create_pool(settings.database_url, min_size=1, max_size=2)
    try:
        while not stopping.is_set():
            wait_seconds = max(
                (
                    next_run_at(datetime.now(UTC), settings.display_timezone, hour, minute)
                    - datetime.now(UTC)
                ).total_seconds(),
                0,
            )
            try:
                await asyncio.wait_for(stopping.wait(), timeout=wait_seconds)
                break  # stopping was set during the sleep
            except TimeoutError:
                pass

            target_day = yesterday_in_tz(settings.display_timezone)
            try:
                result = await run_rollup(pool, day=target_day, tz_name=settings.display_timezone)
                if result.traffic_day_written:
                    summary = await get_traffic_day(pool, target_day)
                    if summary is not None:
                        await send_daily_notification(settings, summary)
            except Exception:
                logger.exception("dailyrollup: run failed, will retry next cycle")
    finally:
        await close_pool(pool)
    logger.info("dailyrollup: loop stopped")


def _print_result(result: RollupResult) -> None:
    if result.dry_run:
        print(f"[dry-run] day={result.day}: {result.aircraft_count} aircraft would be rolled up")
    elif result.lock_skipped:
        print("skipped: another dailyrollup run is already in progress")
    else:
        print(f"rollup complete for day={result.day}: {result.aircraft_count} aircraft")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Compute and persist one calendar day's traffic/aircraft rollup."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be written, without writing",
    )
    parser.add_argument(
        "--day",
        type=str,
        default=None,
        help="Calendar day to roll up, YYYY-MM-DD (default: yesterday in DISPLAY_TIMEZONE)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, rolling up the previous day once daily until SIGTERM/SIGINT",
    )
    parser.add_argument("--loop-hour", type=int, default=DEFAULT_LOOP_HOUR)
    parser.add_argument("--loop-minute", type=int, default=DEFAULT_LOOP_MINUTE)
    args = parser.parse_args()

    try:
        settings = Settings()
    except Exception as exc:
        logger.error("invalid configuration: %s", exc)
        raise SystemExit(1) from exc

    if args.loop:
        if args.dry_run or args.day:
            raise SystemExit("--loop cannot be combined with --dry-run or --day")
        asyncio.run(_run_loop(settings, hour=args.loop_hour, minute=args.loop_minute))
        return

    if args.day:
        try:
            target_day = date.fromisoformat(args.day)
        except ValueError as exc:
            raise SystemExit(f"--day must be YYYY-MM-DD: {exc}") from exc
    else:
        target_day = yesterday_in_tz(settings.display_timezone)

    result = asyncio.run(_run_once(settings, day=target_day, dry_run=args.dry_run))
    _print_result(result)


if __name__ == "__main__":
    main()
