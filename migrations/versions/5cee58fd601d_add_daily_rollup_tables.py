"""add daily rollup tables

Revision ID: 5cee58fd601d
Revises: 62c3f8022564
Create Date: 2026-07-29 02:27:07.687205

Phase 2 Milestone L: `observations` is hard-deleted after
RAW_RETENTION_DAYS (30 by default, see app/retention.py), so any feature
needing history beyond that window (Milestone M's day/week/month
comparisons, Milestone O's cross-30-day aircraft history) needs a rollup
written before retention prunes the day. app/dailyrollup.py (a new
standalone job, modeled on app/retention.py -- it reads after the fact,
it is not part of the collector's write path) populates these tables once
per finished calendar day.

Hand-written raw SQL, following 62c3f8022564's precedent (PostgreSQL-
specific CHECK constraints, no SQLAlchemy Core/ORM metadata anywhere in
this app to autogenerate against).

Downgrade policy: same fix-forward-only stance as 62c3f8022564 -- safe
against an empty/test database, but never run against a database holding
real rollup history (there is no prior schema state to preserve it into).
"""

from alembic import op

revision: str = "5cee58fd601d"
down_revision: str | None = "62c3f8022564"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE traffic_day (
            day                          DATE PRIMARY KEY,
            unique_aircraft_count        INTEGER NOT NULL,
            max_concurrent_count         INTEGER NOT NULL,
            message_count_total          BIGINT NOT NULL,
            position_aircraft_count_max  INTEGER NOT NULL,
            farthest_icao                TEXT REFERENCES aircraft (icao),
            farthest_distance_km         DOUBLE PRECISION,
            closest_icao                 TEXT REFERENCES aircraft (icao),
            closest_distance_km          DOUBLE PRECISION,
            most_observed_icao           TEXT REFERENCES aircraft (icao),
            most_observed_count          INTEGER,
            computed_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT traffic_day_unique_nonneg CHECK (unique_aircraft_count >= 0),
            CONSTRAINT traffic_day_concurrent_nonneg CHECK (max_concurrent_count >= 0),
            CONSTRAINT traffic_day_message_total_nonneg CHECK (message_count_total >= 0),
            CONSTRAINT traffic_day_position_max_nonneg
                CHECK (position_aircraft_count_max >= 0),
            CONSTRAINT traffic_day_farthest_distance_nonneg
                CHECK (farthest_distance_km IS NULL OR farthest_distance_km >= 0),
            CONSTRAINT traffic_day_closest_distance_nonneg
                CHECK (closest_distance_km IS NULL OR closest_distance_km >= 0),
            CONSTRAINT traffic_day_most_observed_count_nonneg
                CHECK (most_observed_count IS NULL OR most_observed_count >= 0)
        )
    """)

    op.execute("""
        CREATE TABLE aircraft_day (
            icao               TEXT NOT NULL REFERENCES aircraft (icao),
            day                DATE NOT NULL,
            pass_count         INTEGER NOT NULL,
            observation_count  INTEGER NOT NULL,
            PRIMARY KEY (icao, day),
            CONSTRAINT aircraft_day_pass_count_nonneg CHECK (pass_count >= 0),
            CONSTRAINT aircraft_day_observation_count_nonneg CHECK (observation_count >= 0)
        )
    """)
    # Justified upfront (not premature): Milestone O's "most frequently
    # seen in the last N days" query filters+groups aircraft_day by a day
    # range across all aircraft, which the (icao, day) primary key alone
    # doesn't serve.
    op.execute("CREATE INDEX ix_aircraft_day_day ON aircraft_day (day)")

    op.execute("""
        CREATE TABLE aircraft_callsign_history (
            icao            TEXT NOT NULL REFERENCES aircraft (icao),
            callsign        TEXT NOT NULL,
            first_seen_at   TIMESTAMPTZ NOT NULL,
            last_seen_at    TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (icao, callsign),
            CONSTRAINT aircraft_callsign_history_length CHECK (char_length(callsign) <= 20)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE aircraft_callsign_history")
    op.execute("DROP TABLE aircraft_day")
    op.execute("DROP TABLE traffic_day")
