"""Read-only DB status report: sizes, row counts, growth rate, last ingestion.

Prints only aggregate numbers -- never row-level data, connection strings,
or credentials (PLAN.md SS8 E-2). Issues nothing but SELECTs, so it's safe
to run against the live production database at any time. Needs the app
package importable and DATABASE_URL set -- run it inside the app's own
container: `docker compose run --rm adsb-api python3 scripts/db_status.py`.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import asyncpg

from app.config import Settings

_TABLES = (
    "aircraft",
    "observations",
    "traffic_minute",
    "ingestion_status",
    "traffic_day",
    "aircraft_day",
    "aircraft_callsign_history",
)


def _human_bytes(n: float) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


async def gather_status(conn: asyncpg.Connection) -> dict:
    db_size = await conn.fetchval("SELECT pg_database_size(current_database())")
    table_sizes = {
        table: await conn.fetchval("SELECT pg_total_relation_size($1)", table) for table in _TABLES
    }
    observation_count = await conn.fetchval("SELECT count(*) FROM observations")
    oldest = await conn.fetchval("SELECT min(observed_at) FROM observations")
    newest = await conn.fetchval("SELECT max(observed_at) FROM observations")
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    growth_24h = await conn.fetchval(
        "SELECT count(*) FROM observations WHERE observed_at >= $1", since_24h
    )
    last_ingestion = await conn.fetchrow(
        "SELECT checked_at, success FROM ingestion_status ORDER BY checked_at DESC LIMIT 1"
    )

    if oldest and newest and newest > oldest and observation_count:
        days_covered = max((newest - oldest).total_seconds() / 86400, 1 / 24)
        avg_daily_rows = observation_count / days_covered
        avg_row_bytes = table_sizes["observations"] / observation_count
        estimated_daily_growth_bytes = avg_daily_rows * avg_row_bytes
        estimated_30d_bytes = estimated_daily_growth_bytes * 30
    else:
        estimated_daily_growth_bytes = 0.0
        estimated_30d_bytes = float(table_sizes["observations"])

    return {
        "db_size_bytes": db_size,
        "table_sizes_bytes": table_sizes,
        "observation_count": observation_count,
        "oldest_observation_at": oldest,
        "newest_observation_at": newest,
        "observations_last_24h": growth_24h,
        "estimated_daily_growth_bytes": estimated_daily_growth_bytes,
        "estimated_30d_size_bytes": estimated_30d_bytes,
        "last_ingestion_at": last_ingestion["checked_at"] if last_ingestion else None,
        "last_ingestion_success": last_ingestion["success"] if last_ingestion else None,
    }


def render_report(status: dict) -> str:
    lines = [
        "=== ADS-B Analytics: DB Status ===",
        f"Total DB size:             {_human_bytes(status['db_size_bytes'])}",
        "Table sizes:",
    ]
    for table, size in status["table_sizes_bytes"].items():
        lines.append(f"  {table:<16} {_human_bytes(size)}")
    lines += [
        f"observations rows:         {status['observation_count']:,}",
        f"  oldest:                  {status['oldest_observation_at']}",
        f"  newest:                  {status['newest_observation_at']}",
        f"  last 24h:                {status['observations_last_24h']:,}",
        f"Estimated daily growth:    {_human_bytes(status['estimated_daily_growth_bytes'])}",
        f"Estimated size at 30 days: {_human_bytes(status['estimated_30d_size_bytes'])}",
        f"Last ingestion:            {status['last_ingestion_at']} "
        f"(success={status['last_ingestion_success']})",
    ]
    return "\n".join(lines)


async def _run() -> str:
    settings = Settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        status = await gather_status(conn)
    finally:
        await conn.close()
    return render_report(status)


def main() -> None:
    print(asyncio.run(_run()))


if __name__ == "__main__":
    main()
