"""Milestone F-5 failure/mock tests: readsb/DB outage and error-message
hygiene, using mocks and disposable containers -- never the production
readsb service or compose.yaml's adsb-db (PLAN.md SS8's explicit rule).

readsb-outage crash-loop/backoff/recovery and the readsb-outage "stale ready/
status" scenarios are already covered by
tests/integration/test_collector_service.py's
test_readsb_outage_backs_off_without_crashing_and_recovers and
tests/integration/test_api.py's test_ready_fails_on_stale_data /
test_status_stale_zeroes_counts -- not duplicated here. Malformed-payload
shape handling (missing fields, bad coordinates, huge aircraft counts,
alt_baro: "ground", etc.) is covered at the normalize layer by
tests/unit/test_normalize.py against tests/fixtures/*.json. What's added
here: (1) a truly unparseable JSON body (as opposed to a validly-parsed but
semantically-wrong payload), (2) DB down/recovered against a real,
individually-controlled Postgres container (not the session-scoped fixture,
since this needs stop/start control), and (3) that DB error messages never
leak into API responses or collector logs.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

import asyncpg
import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_pool
from app.api.main import create_app
from app.collector.service import BACKOFF_INITIAL_SECONDS, CollectorService
from app.collector.store import InMemoryStore
from app.config import Settings
from tests.contract.pg_container import (
    CONTAINER_DB,
    CONTAINER_PASSWORD,
    CONTAINER_USER,
    _apply_migration,
    _docker_available,
    _free_tcp_port,
    _run_docker,
    _wait_until_ready,
)


def _settings(database_url: str) -> Settings:
    return Settings(
        readsb_aircraft_url="http://readsb.test/aircraft.json",
        receiver_lat=35.0,
        receiver_lon=139.0,
        database_url=database_url,
    )


# --- 不正JSON: a genuine JSON syntax error (not just a valid-but-wrong shape) ---


async def test_unparseable_json_body_does_not_crash_service(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{this is not valid json at all")

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://readsb.test"
    )
    store = InMemoryStore()
    service = CollectorService(
        client=client,
        url="/aircraft.json",
        store=store,
        receiver_lat=35.0,
        receiver_lon=139.0,
        poll_interval_seconds=5.0,
        track_sample_seconds=30.0,
    )

    with caplog.at_level(logging.WARNING):
        interval = await service.poll_once()  # must not raise

    assert interval == BACKOFF_INITIAL_SECONDS
    assert store.ingestion_status_log[-1].success is False
    assert len(store.observations) == 0
    assert "readsb fetch failed" in caplog.text
    await client.aclose()


# --- secrets hygiene: DB errors must never leak connection details ---


class _RaisingPool:
    """Stands in for asyncpg.Pool: every read raises, with a message crafted
    to look like it could contain a credential, to prove none of that ever
    reaches an HTTP response."""

    def __init__(self, message: str) -> None:
        self._message = message

    async def fetch(self, *args, **kwargs):
        raise asyncpg.PostgresConnectionError(self._message)

    async def fetchrow(self, *args, **kwargs):
        raise asyncpg.PostgresConnectionError(self._message)

    async def fetchval(self, *args, **kwargs):
        raise asyncpg.PostgresConnectionError(self._message)


SENSITIVE_MESSAGE = (
    "connection to server failed: FATAL: password authentication failed for "
    'user "adsb" (postgresql://adsb:hunter2@adsb-db:5432/adsb)'
)


@pytest.fixture
async def client_with_raising_pool():
    app = create_app(settings=_settings("postgresql://adsb:hunter2@adsb-db:5432/adsb"))
    app.dependency_overrides[get_pool] = lambda: _RaisingPool(SENSITIVE_MESSAGE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client


async def test_db_error_response_never_contains_connection_details(
    client_with_raising_pool, caplog
):
    with caplog.at_level(logging.ERROR):
        response = await client_with_raising_pool.get("/api/traffic?hours=24")

    assert response.status_code == 503
    body_text = response.text
    assert "hunter2" not in body_text
    assert "adsb-db" not in body_text
    assert "postgresql://" not in body_text
    assert (
        body_text
        == '{"error":"database_unavailable","detail":"the database is temporarily unavailable"}'
    )


async def test_real_auth_failure_exception_does_not_contain_the_password(postgres_url):
    # test_db_error_response_never_contains_connection_details above proves
    # the *API response* never echoes an exception's message, regardless of
    # its contents. This test checks the other half: that a real asyncpg
    # exception (which the collector *does* log verbatim via
    # logger.exception in _safe_store_call) doesn't contain the password to
    # begin with. Reuses the disposable postgres_url fixture with a
    # deliberately wrong password to trigger a real auth failure.
    bad_url = postgres_url.replace(f"{CONTAINER_PASSWORD}@", "wrong-password-xyz@")

    with pytest.raises(Exception) as exc_info:
        await asyncpg.connect(bad_url)

    assert "wrong-password-xyz" not in str(exc_info.value)


# --- DB down / recovered, against a real, individually-controlled container ---


@pytest.fixture
async def stoppable_postgres():
    """Like tests/contract/pg_container.py's postgres_url, but this test
    needs to actually stop/start the same container mid-test, so it can't
    reuse that session-scoped, --rm fixture."""
    if not _docker_available():
        pytest.skip("Docker is not available; skipping tests that need a real PostgreSQL")

    port = _free_tcp_port()
    name = f"adsb-failure-test-pg-{uuid.uuid4().hex[:8]}"
    _run_docker(
        [
            "run",
            "-d",
            "--name",
            name,
            "-p",
            f"127.0.0.1:{port}:5432",
            "-e",
            f"POSTGRES_USER={CONTAINER_USER}",
            "-e",
            f"POSTGRES_PASSWORD={CONTAINER_PASSWORD}",
            "-e",
            f"POSTGRES_DB={CONTAINER_DB}",
            "postgres:16",
        ]
    )
    url = (
        f"postgresql://{CONTAINER_USER}:{CONTAINER_PASSWORD}"
        f"@127.0.0.1:{port}/{CONTAINER_DB}?sslmode=disable"
    )
    try:
        _wait_until_ready(name)
        _apply_migration(url)
        yield name, url
    finally:
        _run_docker(["rm", "-f", name])


async def test_ready_goes_503_on_db_down_and_recovers_after_db_returns(stoppable_postgres):
    name, url = stoppable_postgres

    # /health/ready requires a recent successful ingestion, not just DB
    # connectivity -- seed one so the "before" check is a genuine 200, not a
    # 503 for the unrelated "no data yet" reason.
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(
            "INSERT INTO ingestion_status "
            "(checked_at, success, latency_ms, aircraft_count, error_code) "
            "VALUES (now(), true, 10.0, 5, NULL)"
        )
    finally:
        await conn.close()

    app = create_app(settings=_settings(url))

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            healthy = await client.get("/health/ready")
            assert healthy.status_code == 200

            _run_docker(["stop", name])
            down = await client.get("/health/ready")
            assert down.status_code == 503
            assert "hunter2" not in down.text  # no connection details leak here either

            _run_docker(["start", name])
            _wait_until_ready(name)

            recovered = False
            for _ in range(20):
                resp = await client.get("/health/ready")
                if resp.status_code == 200:
                    recovered = True
                    break
                await asyncio.sleep(1)
            assert recovered, "pool never reconnected after the DB came back"
