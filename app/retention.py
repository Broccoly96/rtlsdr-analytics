"""Deletes observations older than RAW_RETENTION_DAYS in small batches.

`traffic_minute` rows are never deleted here (PLAN.md SS8 E-1: minute
aggregates are kept long-term). A Postgres advisory lock prevents two
retention runs from overlapping (e.g. a manual `--dry-run` check during a
scheduled run, or two `adsb-retention` containers started by mistake).

Batches are deleted one small DELETE statement at a time (default 1000 rows)
rather than in one big transaction, matching the rest of this app's
philosophy (app/db/postgres_store.py) of not holding long-running
transactions or locks against tables the API and collector are actively
reading/writing.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

from app.config import Settings
from app.db.pool import close_pool, create_pool

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 1000
DEFAULT_LOOP_INTERVAL_HOURS = 24.0

# Arbitrary fixed key scoped to this one job; any two processes calling
# pg_try_advisory_lock with the same key contend for the same lock.
_ADVISORY_LOCK_KEY = 84372910

_COUNT_SQL = "SELECT count(*) FROM observations WHERE observed_at < $1"
_SELECT_BATCH_SQL = """
    SELECT id FROM observations
    WHERE observed_at < $1
    ORDER BY observed_at
    LIMIT $2
"""
_DELETE_BATCH_SQL = "DELETE FROM observations WHERE id = ANY($1::bigint[])"


@dataclass(frozen=True, slots=True)
class RetentionResult:
    cutoff: datetime
    deleted_count: int
    batch_count: int
    elapsed_seconds: float
    dry_run: bool
    lock_skipped: bool = False


def compute_cutoff(now: datetime, retention_days: int) -> datetime:
    return now - timedelta(days=retention_days)


async def delete_old_observations(
    pool: asyncpg.Pool,
    *,
    cutoff: datetime,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> RetentionResult:
    start = time.monotonic()

    if dry_run:
        count = await pool.fetchval(_COUNT_SQL, cutoff)
        return RetentionResult(cutoff, count, 0, time.monotonic() - start, dry_run=True)

    async with pool.acquire() as conn:
        got_lock = await conn.fetchval("SELECT pg_try_advisory_lock($1)", _ADVISORY_LOCK_KEY)
        if not got_lock:
            logger.warning("retention: another run already holds the advisory lock, skipping")
            return RetentionResult(
                cutoff, 0, 0, time.monotonic() - start, dry_run=False, lock_skipped=True
            )

        total_deleted = 0
        batch_count = 0
        try:
            while True:
                rows = await conn.fetch(_SELECT_BATCH_SQL, cutoff, batch_size)
                if not rows:
                    break
                ids = [row["id"] for row in rows]
                await conn.execute(_DELETE_BATCH_SQL, ids)
                total_deleted += len(ids)
                batch_count += 1
                logger.info(
                    "retention: deleted batch %d (%d rows, %d total so far)",
                    batch_count,
                    len(ids),
                    total_deleted,
                )
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", _ADVISORY_LOCK_KEY)

    elapsed = time.monotonic() - start
    logger.info(
        "retention: complete, deleted=%d batches=%d elapsed=%.2fs cutoff=%s",
        total_deleted,
        batch_count,
        elapsed,
        cutoff.isoformat(),
    )
    return RetentionResult(cutoff, total_deleted, batch_count, elapsed, dry_run=False)


async def _run_once(settings: Settings, *, dry_run: bool, batch_size: int) -> RetentionResult:
    pool = await create_pool(settings.database_url, min_size=1, max_size=1)
    try:
        cutoff = compute_cutoff(datetime.now(UTC), settings.raw_retention_days)
        return await delete_old_observations(
            pool, cutoff=cutoff, batch_size=batch_size, dry_run=dry_run
        )
    finally:
        await close_pool(pool)


async def _run_loop(settings: Settings, *, batch_size: int, interval_hours: float) -> None:
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopping.set)

    while not stopping.is_set():
        try:
            await _run_once(settings, dry_run=False, batch_size=batch_size)
        except Exception:
            logger.exception("retention: run failed, will retry next cycle")
        try:
            await asyncio.wait_for(stopping.wait(), timeout=interval_hours * 3600)
        except TimeoutError:
            pass
    logger.info("retention: loop stopped")


def _print_result(result: RetentionResult) -> None:
    if result.dry_run:
        print(
            f"[dry-run] {result.deleted_count} observation(s) older than "
            f"{result.cutoff.isoformat()} would be deleted"
        )
    elif result.lock_skipped:
        print("skipped: another retention run is already in progress")
    else:
        print(
            f"deleted {result.deleted_count} observation(s) older than "
            f"{result.cutoff.isoformat()} in {result.batch_count} batch(es), "
            f"{result.elapsed_seconds:.2f}s"
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Delete observations older than RAW_RETENTION_DAYS, in small batches."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many rows would be deleted, without deleting",
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, sleeping --interval-hours between passes, until SIGTERM/SIGINT",
    )
    parser.add_argument("--interval-hours", type=float, default=DEFAULT_LOOP_INTERVAL_HOURS)
    args = parser.parse_args()

    try:
        settings = Settings()
    except Exception as exc:
        logger.error("invalid configuration: %s", exc)
        raise SystemExit(1) from exc

    if args.loop:
        if args.dry_run:
            raise SystemExit("--loop and --dry-run cannot be used together")
        asyncio.run(
            _run_loop(settings, batch_size=args.batch_size, interval_hours=args.interval_hours)
        )
        return

    result = asyncio.run(_run_once(settings, dry_run=args.dry_run, batch_size=args.batch_size))
    _print_result(result)


if __name__ == "__main__":
    main()
