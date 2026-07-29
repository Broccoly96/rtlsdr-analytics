"""Contract tests for app.dailyrollup against a real, ephemeral PostgreSQL
instance. Modeled on tests/contract/test_retention.py: advisory-lock
behavior and idempotent re-run correctness, plus the one Phase-2-specific
case worth a dedicated test -- rollup values for a day must survive after
retention.py subsequently deletes that day's raw observations, proving
the two jobs compose safely.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import asyncpg
import pytest

from app.dailyrollup import _ADVISORY_LOCK_KEY, run_rollup
from app.db.pool import close_pool, create_pool
from app.domain.daytime import day_bounds_utc
from app.retention import delete_old_observations

TZ_NAME = "Asia/Tokyo"
DAY = date(2026, 1, 15)
DAY_START, DAY_END = day_bounds_utc(DAY, TZ_NAME)


async def _insert_aircraft(conn: asyncpg.Connection, icao: str, seen_at: datetime) -> None:
    await conn.execute(
        "INSERT INTO aircraft (icao, first_seen_at, last_seen_at) VALUES ($1, $2, $2)",
        icao,
        seen_at,
    )


async def _insert_observation(
    conn: asyncpg.Connection,
    icao: str,
    observed_at: datetime,
    *,
    callsign: str | None = None,
    distance_km: float | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO observations (observed_at, icao, callsign, distance_km, source_age_seconds)
        VALUES ($1, $2, $3, $4, 0)
        """,
        observed_at,
        icao,
        callsign,
        distance_km,
    )


@pytest.fixture
async def pool(postgres_url, clean_db):
    p = await create_pool(postgres_url, min_size=1, max_size=3)
    yield p
    await close_pool(p)


async def _seed_day(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "aaaaaa", DAY_START)
        await _insert_aircraft(conn, "bbbbbb", DAY_START)
        # aaaaaa: two passes (a >120s gap splits them), 3 observations,
        # callsign changes mid-day (AAA001 -> AAA002).
        await _insert_observation(
            conn, "aaaaaa", DAY_START + timedelta(minutes=1), callsign="AAA001", distance_km=10.0
        )
        await _insert_observation(
            conn,
            "aaaaaa",
            DAY_START + timedelta(minutes=1, seconds=30),
            callsign="AAA001",
            distance_km=20.0,
        )
        await _insert_observation(
            conn, "aaaaaa", DAY_START + timedelta(hours=2), callsign="AAA002", distance_km=5.0
        )
        # bbbbbb: single pass, one observation, farthest of the day.
        await _insert_observation(
            conn, "bbbbbb", DAY_START + timedelta(minutes=5), callsign="BBB001", distance_km=500.0
        )
        await conn.execute(
            """
            INSERT INTO traffic_minute (
                bucket_at, active_aircraft_count, position_aircraft_count, message_count_delta
            )
            VALUES ($1, 2, 1, 100)
            """,
            DAY_START + timedelta(minutes=1),
        )


def _without_computed_at(row: asyncpg.Record) -> dict:
    data = dict(row)
    data.pop("computed_at", None)
    return data


async def test_run_rollup_writes_expected_values(pool):
    await _seed_day(pool)

    result = await run_rollup(pool, day=DAY, tz_name=TZ_NAME)

    assert result.traffic_day_written is True
    assert result.aircraft_count == 2

    traffic_day = await pool.fetchrow("SELECT * FROM traffic_day WHERE day = $1", DAY)
    assert traffic_day["unique_aircraft_count"] == 2
    assert traffic_day["max_concurrent_count"] == 2
    assert traffic_day["message_count_total"] == 100
    assert traffic_day["position_aircraft_count_max"] == 1
    assert traffic_day["farthest_icao"] == "bbbbbb"
    assert traffic_day["farthest_distance_km"] == 500.0
    assert traffic_day["closest_icao"] == "aaaaaa"
    assert traffic_day["closest_distance_km"] == 5.0
    assert traffic_day["most_observed_icao"] == "aaaaaa"
    assert traffic_day["most_observed_count"] == 3

    aircraft_day_a = await pool.fetchrow(
        "SELECT * FROM aircraft_day WHERE icao = $1 AND day = $2", "aaaaaa", DAY
    )
    assert aircraft_day_a["pass_count"] == 2
    assert aircraft_day_a["observation_count"] == 3

    aircraft_day_b = await pool.fetchrow(
        "SELECT * FROM aircraft_day WHERE icao = $1 AND day = $2", "bbbbbb", DAY
    )
    assert aircraft_day_b["pass_count"] == 1
    assert aircraft_day_b["observation_count"] == 1

    callsigns_a = await pool.fetch(
        "SELECT callsign FROM aircraft_callsign_history WHERE icao = $1 ORDER BY callsign",
        "aaaaaa",
    )
    assert [row["callsign"] for row in callsigns_a] == ["AAA001", "AAA002"]


async def test_run_rollup_is_idempotent(pool):
    await _seed_day(pool)

    await run_rollup(pool, day=DAY, tz_name=TZ_NAME)
    first_traffic_day = await pool.fetchrow("SELECT * FROM traffic_day WHERE day = $1", DAY)
    first_aircraft_day = await pool.fetch(
        "SELECT * FROM aircraft_day WHERE day = $1 ORDER BY icao", DAY
    )
    first_callsigns = await pool.fetch(
        "SELECT * FROM aircraft_callsign_history ORDER BY icao, callsign"
    )

    await run_rollup(pool, day=DAY, tz_name=TZ_NAME)
    second_traffic_day = await pool.fetchrow("SELECT * FROM traffic_day WHERE day = $1", DAY)
    second_aircraft_day = await pool.fetch(
        "SELECT * FROM aircraft_day WHERE day = $1 ORDER BY icao", DAY
    )
    second_callsigns = await pool.fetch(
        "SELECT * FROM aircraft_callsign_history ORDER BY icao, callsign"
    )

    assert _without_computed_at(first_traffic_day) == _without_computed_at(second_traffic_day)
    assert [dict(r) for r in first_aircraft_day] == [dict(r) for r in second_aircraft_day]
    assert [dict(r) for r in first_callsigns] == [dict(r) for r in second_callsigns]

    assert await pool.fetchval("SELECT count(*) FROM traffic_day") == 1
    assert await pool.fetchval("SELECT count(*) FROM aircraft_day") == 2
    assert await pool.fetchval("SELECT count(*) FROM aircraft_callsign_history") == 3


async def test_dry_run_does_not_write(pool):
    await _seed_day(pool)

    result = await run_rollup(pool, day=DAY, tz_name=TZ_NAME, dry_run=True)

    assert result.dry_run is True
    assert result.aircraft_count == 2
    assert await pool.fetchval("SELECT count(*) FROM traffic_day") == 0
    assert await pool.fetchval("SELECT count(*) FROM aircraft_day") == 0


async def test_concurrent_run_skips_when_advisory_lock_held(pool):
    await _seed_day(pool)

    holder = await pool.acquire()
    try:
        await holder.fetchval("SELECT pg_try_advisory_lock($1)", _ADVISORY_LOCK_KEY)

        result = await run_rollup(pool, day=DAY, tz_name=TZ_NAME)

        assert result.lock_skipped is True
        assert await pool.fetchval("SELECT count(*) FROM traffic_day") == 0
    finally:
        await holder.execute("SELECT pg_advisory_unlock($1)", _ADVISORY_LOCK_KEY)
        await pool.release(holder)


async def test_rollup_survives_retention_deleting_the_day(pool):
    await _seed_day(pool)
    await run_rollup(pool, day=DAY, tz_name=TZ_NAME)

    # Simulate RAW_RETENTION_DAYS having passed for this day: retention.py
    # deletes every observation, but the rollup tables must be untouched.
    cutoff = DAY_END + timedelta(days=1)
    await delete_old_observations(pool, cutoff=cutoff)
    assert await pool.fetchval("SELECT count(*) FROM observations") == 0

    traffic_day = await pool.fetchrow("SELECT * FROM traffic_day WHERE day = $1", DAY)
    assert traffic_day is not None
    assert traffic_day["farthest_icao"] == "bbbbbb"
    assert traffic_day["most_observed_count"] == 3

    assert await pool.fetchval("SELECT count(*) FROM aircraft_day WHERE day = $1", DAY) == 2
    assert await pool.fetchval("SELECT count(*) FROM aircraft_callsign_history") == 3
