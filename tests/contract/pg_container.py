"""Ephemeral, disposable PostgreSQL container for contract/integration
tests. Always a separate instance from compose.yaml's adsb-db -- binds only
to 127.0.0.1 on a random free port, is migrated with the real Alembic
migration, and is torn down at session end. Tests depending on this fixture
are skipped (not failed) when Docker isn't available.
"""

from __future__ import annotations

import os
import shlex
import socket
import subprocess
import time
import uuid
from pathlib import Path

import asyncpg
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
POSTGRES_IMAGE = "postgres:16"
CONTAINER_USER = "test"
CONTAINER_PASSWORD = "test"
CONTAINER_DB = "test"


def _run_docker(args: list[str], timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 or "permission denied" not in result.stderr.lower():
            return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Fall back for shells where this session's `docker` group membership
    # hasn't been refreshed since the docker group was granted (no fresh
    # login yet) -- `sg docker` applies the group without one.
    quoted = " ".join(shlex.quote(a) for a in args)
    return subprocess.run(
        ["sg", "docker", "-c", f"docker {quoted}"], capture_output=True, text=True, timeout=timeout
    )


def _docker_available() -> bool:
    try:
        return _run_docker(["version"], timeout=10.0).returncode == 0
    except Exception:
        return False


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_ready(container_name: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = _run_docker(
            ["exec", container_name, "pg_isready", "-U", CONTAINER_USER], timeout=5.0
        )
        if result.returncode == 0:
            return
        time.sleep(0.5)
    raise RuntimeError(f"postgres container {container_name} did not become ready in time")


def _apply_migration(database_url: str, attempts: int = 5) -> None:
    """Retries a few times: this host's Docker port-forwarding occasionally
    resets the very first connection or two right after a freshly published
    port starts accepting connections, even once pg_isready succeeds."""
    last_result = None
    for attempt in range(attempts):
        last_result = subprocess.run(
            ["alembic", "-c", str(REPO_ROOT / "alembic.ini"), "upgrade", "head"],
            cwd=REPO_ROOT,
            env={**os.environ, "DATABASE_URL": database_url},
            capture_output=True,
            text=True,
            timeout=30,
        )
        if last_result.returncode == 0:
            return
        time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"alembic upgrade failed:\n{last_result.stdout}\n{last_result.stderr}")


@pytest.fixture(scope="session")
def postgres_url():
    if not _docker_available():
        pytest.skip("Docker is not available; skipping tests that need a real PostgreSQL")

    port = _free_tcp_port()
    name = f"adsb-contract-pg-{uuid.uuid4().hex[:8]}"
    _run_docker(
        [
            "run",
            "--rm",
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
            POSTGRES_IMAGE,
        ]
    )
    # sslmode=disable: this host's Docker port-forwarding occasionally resets
    # the connection during SSL negotiation on a freshly published port
    # (container-to-container traffic on the internal compose network, used
    # in production, is unaffected -- this only matters for host-forwarded
    # ephemeral test containers).
    url = (
        f"postgresql://{CONTAINER_USER}:{CONTAINER_PASSWORD}"
        f"@127.0.0.1:{port}/{CONTAINER_DB}?sslmode=disable"
    )
    try:
        _wait_until_ready(name)
        _apply_migration(url)
        yield url
    finally:
        _run_docker(["rm", "-f", name])


@pytest.fixture
async def clean_db(postgres_url):
    """Truncate all tables before each test for isolation, without paying
    the container-startup cost per test."""
    conn = await asyncpg.connect(postgres_url)
    try:
        await conn.execute(
            "TRUNCATE aircraft, observations, traffic_minute, ingestion_status, "
            "traffic_day, aircraft_day, aircraft_callsign_history CASCADE"
        )
        yield
    finally:
        await conn.close()
