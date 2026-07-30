"""Contract tests for app.aircraft_lookup against a real, ephemeral
PostgreSQL instance, with api.adsbdb.com mocked via httpx.MockTransport
(same technique as tests/unit/test_notify.py) -- never hits the real
service in tests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
import httpx
import pytest

from app.aircraft_lookup import FAILED_LOOKUP_RETRY_DAYS, refresh_uncached_aircraft_types
from app.db.pool import close_pool, create_pool

# The retry-cooldown check compares looked_up_at against SQL's own now(),
# not this constant -- so this must track real wall-clock time, not a
# fixed calendar date (unlike e.g. dailyrollup's tests, which pin a fixed
# DAY because they test *calendar-day* boundary math instead).
NOW = datetime.now(UTC)

ADSBDB_FOUND_BODY = {
    "response": {
        "aircraft": {
            "type": "A330 303",
            "icao_type": "A333",
            "manufacturer": "Airbus",
            "mode_s": "AAAAAA",
            "registration": "TC-LNE",
            "registered_owner": "Turkish Airlines",
        }
    }
}


async def _insert_aircraft(conn: asyncpg.Connection, icao: str, last_seen_at: datetime) -> None:
    await conn.execute(
        "INSERT INTO aircraft (icao, first_seen_at, last_seen_at) VALUES ($1, $2, $2)",
        icao,
        last_seen_at,
    )


async def _insert_cache_row(
    conn: asyncpg.Connection, icao: str, *, lookup_failed: bool, looked_up_at: datetime
) -> None:
    await conn.execute(
        """
        INSERT INTO aircraft_type_cache (icao, lookup_failed, looked_up_at)
        VALUES ($1, $2, $3)
        """,
        icao,
        lookup_failed,
        looked_up_at,
    )


@pytest.fixture
async def pool(postgres_url, clean_db):
    p = await create_pool(postgres_url, min_size=1, max_size=3)
    yield p
    await close_pool(p)


async def test_looks_up_and_caches_new_aircraft(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "aaaaaa", NOW)

    def _respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/aaaaaa")
        return httpx.Response(200, json=ADSBDB_FOUND_BODY)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        looked_up = await refresh_uncached_aircraft_types(pool, client=client)

    assert looked_up == 1
    row = await pool.fetchrow("SELECT * FROM aircraft_type_cache WHERE icao = 'aaaaaa'")
    assert row["type_code"] == "A333"
    assert row["manufacturer"] == "Airbus"
    assert row["registration"] == "TC-LNE"
    assert row["lookup_failed"] is False


async def test_caches_failed_lookup_without_raising(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "bbbbbb", NOW)

    def _not_found(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_not_found)) as client:
        looked_up = await refresh_uncached_aircraft_types(pool, client=client)

    assert looked_up == 1
    row = await pool.fetchrow("SELECT * FROM aircraft_type_cache WHERE icao = 'bbbbbb'")
    assert row["lookup_failed"] is True
    assert row["type_code"] is None


async def test_connection_error_is_cached_as_failed_and_does_not_raise(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "cccccc", NOW)

    def _raise(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network failure", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_raise)) as client:
        looked_up = await refresh_uncached_aircraft_types(pool, client=client)

    assert looked_up == 1
    row = await pool.fetchrow("SELECT lookup_failed FROM aircraft_type_cache WHERE icao = 'cccccc'")
    assert row["lookup_failed"] is True


async def test_already_cached_aircraft_is_never_re_queried(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "dddddd", NOW)
        await _insert_cache_row(conn, "dddddd", lookup_failed=False, looked_up_at=NOW)

    def _fail_if_called(request: httpx.Request) -> httpx.Response:
        raise AssertionError("a cached, successful lookup must never be re-queried")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_fail_if_called)) as client:
        looked_up = await refresh_uncached_aircraft_types(pool, client=client)

    assert looked_up == 0


async def test_recently_failed_lookup_is_not_retried_yet(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "eeeeee", NOW)
        await _insert_cache_row(
            conn,
            "eeeeee",
            lookup_failed=True,
            looked_up_at=NOW - timedelta(days=FAILED_LOOKUP_RETRY_DAYS - 1),
        )

    def _fail_if_called(request: httpx.Request) -> httpx.Response:
        raise AssertionError("a recently-failed lookup must not be retried before the cooldown")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_fail_if_called)) as client:
        looked_up = await refresh_uncached_aircraft_types(pool, client=client)

    assert looked_up == 0


async def test_old_failed_lookup_is_retried_after_cooldown(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "ffffff", NOW)
        await _insert_cache_row(
            conn,
            "ffffff",
            lookup_failed=True,
            looked_up_at=NOW - timedelta(days=FAILED_LOOKUP_RETRY_DAYS + 1),
        )

    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=ADSBDB_FOUND_BODY)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        looked_up = await refresh_uncached_aircraft_types(pool, client=client)

    assert looked_up == 1
    row = await pool.fetchrow("SELECT lookup_failed FROM aircraft_type_cache WHERE icao = 'ffffff'")
    assert row["lookup_failed"] is False


async def test_respects_limit(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await _insert_aircraft(conn, "111111", NOW)
        await _insert_aircraft(conn, "222222", NOW)

    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=ADSBDB_FOUND_BODY)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        looked_up = await refresh_uncached_aircraft_types(pool, client=client, limit=1)

    assert looked_up == 1
