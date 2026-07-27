import asyncio
import os
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Hand-written raw-SQL migrations (see versions/0001_initial_schema.py) --
# there's no SQLAlchemy Core/ORM metadata anywhere in this app to diff
# against, so autogenerate is intentionally unused.
target_metadata = None


def _sqlalchemy_url_and_connect_args() -> tuple[str, dict]:
    """Read DATABASE_URL directly from the environment rather than
    alembic.ini, so the same env var app.config.Settings validates also
    drives migrations -- and so migrations don't require the rest of the
    app's unrelated settings (RECEIVER_LAT, READSB_AIRCRAFT_URL, ...) just
    to run.

    A `sslmode` query param (only ever set by the ephemeral test-container
    fixture, tests/contract/pg_container.py -- never by the real
    DATABASE_URL) is translated into asyncpg's `ssl` connect kwarg rather
    than left in the URL: SQLAlchemy's asyncpg dialect forwards unknown
    query params straight to asyncpg.connect(), which has no `sslmode`
    keyword and raises a TypeError."""
    raw = os.environ["DATABASE_URL"]
    if not raw.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("DATABASE_URL must be a postgres:// or postgresql:// URL")
    _scheme, _, rest = raw.partition("://")

    parts = urlsplit(f"postgresql+asyncpg://{rest}")
    query = parse_qs(parts.query)
    connect_args = {}
    if query.pop("sslmode", None) == ["disable"]:
        connect_args["ssl"] = False
    url = urlunsplit(parts._replace(query=urlencode(query, doseq=True)))
    return url, connect_args


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url, _connect_args = _sqlalchemy_url_and_connect_args()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    url, connect_args = _sqlalchemy_url_and_connect_args()
    connectable = create_async_engine(url, poolclass=pool.NullPool, connect_args=connect_args)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
