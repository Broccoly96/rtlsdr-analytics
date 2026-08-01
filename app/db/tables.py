"""Single source of truth for every table this app owns.

Used by scripts/db_status.py, scripts/reset_db.py, and
tests/contract/pg_container.py's clean_db fixture -- previously hand-copied
in each of those, a drift risk every time a migration adds a table.
"""

from __future__ import annotations

ALL_TABLES: tuple[str, ...] = (
    "aircraft",
    "observations",
    "traffic_minute",
    "ingestion_status",
    "traffic_day",
    "aircraft_day",
    "aircraft_callsign_history",
    "aircraft_type_cache",
    "favorites",
)
