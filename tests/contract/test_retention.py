from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
import pytest

from app.db.pool import close_pool, create_pool
from app.retention import _ADVISORY_LOCK_KEY, delete_old_observations

CUTOFF = datetime(2026, 1, 1, tzinfo=UTC)


async def _insert_aircraft(conn: asyncpg.Connection, icao: str, seen_at: datetime) -> None:
    await conn.execute(
        "INSERT INTO aircraft (icao, first_seen_at, last_seen_at) VALUES ($1, $2, $2)",
        icao,
        seen_at,
    )


async def _insert_observation(conn: asyncpg.Connection, icao: str, observed_at: datetime) -> None:
    await conn.execute(
        """
        INSERT INTO observations (observed_at, icao, source_age_seconds)
        VALUES ($1, $2, 0)
        """,
        observed_at,
        icao,
    )


@pytest.fixture
async def pool(postgres_url, clean_db):
    p = await create_pool(postgres_url, min_size=1, max_size=3)
    yield p
    await close_pool(p)


async def test_deletes_only_observations_older_than_cutoff(pool):
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "abc123", CUTOFF - timedelta(days=1))
        await _insert_observation(conn, "abc123", CUTOFF - timedelta(days=5))
        await _insert_observation(conn, "abc123", CUTOFF - timedelta(seconds=1))
        await _insert_observation(conn, "abc123", CUTOFF + timedelta(seconds=1))
        await _insert_observation(conn, "abc123", CUTOFF + timedelta(days=1))

    result = await delete_old_observations(pool, cutoff=CUTOFF, batch_size=1000)

    assert result.deleted_count == 2
    remaining = await pool.fetchval("SELECT count(*) FROM observations")
    assert remaining == 2


async def test_batches_across_multiple_small_batch_sizes(pool):
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "abc123", CUTOFF - timedelta(days=1))
        for i in range(7):
            await _insert_observation(conn, "abc123", CUTOFF - timedelta(days=1, seconds=i))

    result = await delete_old_observations(pool, cutoff=CUTOFF, batch_size=3)

    assert result.deleted_count == 7
    assert result.batch_count == 3  # 3 + 3 + 1
    remaining = await pool.fetchval("SELECT count(*) FROM observations")
    assert remaining == 0


async def test_dry_run_does_not_delete(pool):
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "abc123", CUTOFF - timedelta(days=1))
        await _insert_observation(conn, "abc123", CUTOFF - timedelta(days=1))

    result = await delete_old_observations(pool, cutoff=CUTOFF, dry_run=True)

    assert result.dry_run is True
    assert result.deleted_count == 1
    remaining = await pool.fetchval("SELECT count(*) FROM observations")
    assert remaining == 1


async def test_traffic_minute_rows_are_never_touched(pool):
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "abc123", CUTOFF - timedelta(days=1))
        await _insert_observation(conn, "abc123", CUTOFF - timedelta(days=1))
        await conn.execute(
            """
            INSERT INTO traffic_minute (
                bucket_at, active_aircraft_count, position_aircraft_count, message_count_delta
            )
            VALUES ($1, 1, 1, 1)
            """,
            CUTOFF - timedelta(days=100),
        )

    await delete_old_observations(pool, cutoff=CUTOFF)

    remaining = await pool.fetchval("SELECT count(*) FROM traffic_minute")
    assert remaining == 1


async def test_concurrent_run_skips_when_advisory_lock_held(pool):
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "abc123", CUTOFF - timedelta(days=1))
        await _insert_observation(conn, "abc123", CUTOFF - timedelta(days=1))

    holder = await pool.acquire()
    try:
        await holder.fetchval("SELECT pg_try_advisory_lock($1)", _ADVISORY_LOCK_KEY)

        result = await delete_old_observations(pool, cutoff=CUTOFF)

        assert result.lock_skipped is True
        assert result.deleted_count == 0
        remaining = await pool.fetchval("SELECT count(*) FROM observations")
        assert remaining == 1
    finally:
        await holder.execute("SELECT pg_advisory_unlock($1)", _ADVISORY_LOCK_KEY)
        await pool.release(holder)
