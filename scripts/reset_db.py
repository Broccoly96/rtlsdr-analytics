"""DESTRUCTIVE dev/testing convenience: TRUNCATEs every table this app
owns, resetting the database to empty. The schema is kept (no migration
re-run needed) -- only the data is deleted, permanently.

Deliberately NOT wired into compose.yaml and never reachable over the
network: this app has no auth on any route (PLAN.md SS16's "no mutating
endpoint exists anywhere in this API" precedent), so a destructive action
like this must never be one click/request away. It's a manual script,
requires shell access to the server, and refuses to run without typing
the exact database name back -- the same friction a `terraform destroy`-
style confirmation provides.

Run inside the app's own container, same convention as db_status.py:
    docker compose run --rm adsb-api python3 scripts/reset_db.py

--yes skips the interactive confirmation, for scripted use ONLY against a
database you already know is disposable (e.g. a CI/test container) --
never pass it against a database holding data you care about.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import asyncpg

from app.config import Settings
from app.db.tables import ALL_TABLES


async def _row_counts(conn: asyncpg.Connection) -> dict[str, int]:
    return {table: await conn.fetchval(f"SELECT count(*) FROM {table}") for table in ALL_TABLES}


async def _run(*, skip_confirmation: bool) -> int:
    settings = Settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        db_name = await conn.fetchval("SELECT current_database()")
        counts = await _row_counts(conn)
        total_rows = sum(counts.values())

        print(f"=== reset_db: {db_name} ===")
        for table, count in counts.items():
            print(f"  {table:<24} {count:,} row(s)")
        print(f"  {'TOTAL':<24} {total_rows:,} row(s)")

        if total_rows == 0:
            print("\ndatabase is already empty, nothing to do.")
            return 0

        print(
            "\nThis will PERMANENTLY DELETE all rows listed above. The schema is "
            "kept (no migration re-run needed), but all collected history is gone."
        )

        if not skip_confirmation:
            typed = input(f"\nType the database name ({db_name}) to confirm: ")
            if typed != db_name:
                print("confirmation did not match, aborting. Nothing was deleted.")
                return 1

        await conn.execute(f"TRUNCATE {', '.join(ALL_TABLES)} CASCADE")
        print(f"\ndone: {db_name} reset, all {len(ALL_TABLES)} tables truncated.")
        return 0
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DESTRUCTIVE: truncate every table this app owns, resetting to "
        "empty. Dev/testing convenience only -- never run against data you want to keep."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive type-the-database-name confirmation "
        "(only for scripted use against a database you already know is disposable)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(skip_confirmation=args.yes)))


if __name__ == "__main__":
    main()
