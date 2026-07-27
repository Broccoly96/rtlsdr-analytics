"""asyncpg connection pool lifecycle helpers.

Kept separate from PostgresStore so a future read-side repository (Task/
Milestone C's app/db/queries/) can own its own pool without going through
the collector's write-side Store.
"""

from __future__ import annotations

import asyncpg


async def create_pool(
    database_url: str,
    *,
    min_size: int = 1,
    max_size: int = 5,
    command_timeout: float = 5.0,
) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        dsn=database_url,
        min_size=min_size,
        max_size=max_size,
        command_timeout=command_timeout,
    )


async def close_pool(pool: asyncpg.Pool) -> None:
    await pool.close()
