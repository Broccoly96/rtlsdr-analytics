"""add aircraft_type_cache

Revision ID: d6494c2713c8
Revises: 5cee58fd601d
Create Date: 2026-07-30 03:02:20.903971

Phase 2 dashboard-feedback milestone S: the daily-report "top 10 aircraft
type" chart needs a type designator per aircraft, which readsb's own
aircraft.json does not provide (confirmed live: its `type` field is the
ADS-B message source, e.g. "adsb_icao", and `category` is the wake/
emitter class, e.g. "A3" -- neither is an ICAO type code like "A321").

The original plan called for vendoring an offline hex->type dataset
(tar1090's approach), but the realistic candidates (wiedehopf/tar1090-db,
OpenSky's aircraft database) both turned out unlicensed for
redistribution. This table is a lazily-populated *cache* of live lookups
against api.adsbdb.com instead (app/aircraft_lookup.py), called only from
app/dailyrollup.py's --loop cycle -- never from a request path, and never
more than once per aircraft (a type/registration essentially never
changes once assigned; a failed lookup is cached too so an unknown hex
isn't re-queried every single day).

Hand-written raw SQL, following 62c3f8022564/5cee58fd601d's precedent.
Downgrade policy: same fix-forward-only stance -- safe against an empty/
test database only.
"""

from alembic import op

revision: str = "d6494c2713c8"
down_revision: str | None = "5cee58fd601d"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE aircraft_type_cache (
            icao            TEXT PRIMARY KEY REFERENCES aircraft (icao),
            type_code       TEXT,
            type_name       TEXT,
            manufacturer    TEXT,
            registration    TEXT,
            lookup_failed   BOOLEAN NOT NULL DEFAULT false,
            looked_up_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE aircraft_type_cache")
