"""initial schema

Revision ID: 62c3f8022564
Revises:
Create Date: 2026-07-27 05:25:16.140628

Hand-written raw SQL rather than op.create_table(): this needs PostgreSQL-
specific syntax (GENERATED ALWAYS AS IDENTITY, regex CHECK constraints, a
partial index) that's more directly expressed as literal DDL, and there's no
SQLAlchemy Core/ORM metadata anywhere in the app to autogenerate against or
keep in sync (app/db/postgres_store.py uses raw asyncpg SQL, not an ORM).

Downgrade policy: `alembic downgrade base` is safe and tested against an
empty database, but since this is the initial schema, downgrading it is
inherently destructive (there's no prior schema to preserve data into).
Never run this downgrade against a database holding real observation
history -- fix forward with a new migration instead, or restore from a
Milestone E backup.
"""

from alembic import op

revision: str = "62c3f8022564"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE aircraft (
            icao            TEXT PRIMARY KEY,
            first_seen_at   TIMESTAMPTZ NOT NULL,
            last_seen_at    TIMESTAMPTZ NOT NULL,
            last_callsign   TEXT,
            CONSTRAINT aircraft_icao_format CHECK (icao ~ '^~?[0-9a-f]{6}$'),
            CONSTRAINT aircraft_last_callsign_length
                CHECK (last_callsign IS NULL OR char_length(last_callsign) <= 20)
        )
    """)
    op.execute("CREATE INDEX ix_aircraft_last_seen_at ON aircraft (last_seen_at DESC)")

    op.execute("""
        CREATE TABLE observations (
            id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            observed_at         TIMESTAMPTZ NOT NULL,
            icao                TEXT NOT NULL REFERENCES aircraft (icao),
            callsign            TEXT,
            lat                 DOUBLE PRECISION,
            lon                 DOUBLE PRECISION,
            altitude_ft         DOUBLE PRECISION,
            ground_speed_kt     DOUBLE PRECISION,
            track_deg           DOUBLE PRECISION,
            vertical_rate_fpm   DOUBLE PRECISION,
            rssi                DOUBLE PRECISION,
            distance_km         DOUBLE PRECISION,
            bearing_deg         DOUBLE PRECISION,
            source_age_seconds  DOUBLE PRECISION NOT NULL,
            CONSTRAINT observations_icao_observed_at_uniq UNIQUE (icao, observed_at),
            CONSTRAINT observations_lat_range CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
            CONSTRAINT observations_lon_range CHECK (lon IS NULL OR lon BETWEEN -180 AND 180),
            CONSTRAINT observations_distance_nonneg
                CHECK (distance_km IS NULL OR distance_km >= 0),
            CONSTRAINT observations_bearing_range
                CHECK (bearing_deg IS NULL OR bearing_deg BETWEEN 0 AND 360),
            CONSTRAINT observations_track_range
                CHECK (track_deg IS NULL OR track_deg BETWEEN 0 AND 360),
            CONSTRAINT observations_altitude_range
                CHECK (altitude_ft IS NULL OR altitude_ft BETWEEN -2000 AND 100000),
            CONSTRAINT observations_gs_nonneg
                CHECK (ground_speed_kt IS NULL OR ground_speed_kt >= 0),
            CONSTRAINT observations_source_age_nonneg CHECK (source_age_seconds >= 0)
        )
    """)
    op.execute("CREATE INDEX ix_observations_observed_at ON observations (observed_at DESC)")
    op.execute("""
        CREATE INDEX ix_observations_distance_observed_at
            ON observations (distance_km, observed_at DESC)
            WHERE distance_km IS NOT NULL
    """)

    op.execute("""
        CREATE TABLE traffic_minute (
            bucket_at               TIMESTAMPTZ PRIMARY KEY,
            active_aircraft_count   INTEGER NOT NULL,
            position_aircraft_count INTEGER NOT NULL,
            message_count_delta     INTEGER NOT NULL,
            CONSTRAINT traffic_minute_active_nonneg CHECK (active_aircraft_count >= 0),
            CONSTRAINT traffic_minute_position_nonneg CHECK (position_aircraft_count >= 0),
            CONSTRAINT traffic_minute_position_le_active
                CHECK (position_aircraft_count <= active_aircraft_count),
            CONSTRAINT traffic_minute_delta_nonneg CHECK (message_count_delta >= 0)
        )
    """)

    op.execute("""
        CREATE TABLE ingestion_status (
            id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            checked_at     TIMESTAMPTZ NOT NULL,
            success        BOOLEAN NOT NULL,
            latency_ms     DOUBLE PRECISION,
            aircraft_count INTEGER,
            error_code     TEXT,
            CONSTRAINT ingestion_status_latency_nonneg
                CHECK (latency_ms IS NULL OR latency_ms >= 0),
            CONSTRAINT ingestion_status_count_nonneg
                CHECK (aircraft_count IS NULL OR aircraft_count >= 0),
            CONSTRAINT ingestion_status_error_code_len
                CHECK (error_code IS NULL OR char_length(error_code) <= 100)
        )
    """)
    op.execute("CREATE INDEX ix_ingestion_status_checked_at ON ingestion_status (checked_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE observations")
    op.execute("DROP TABLE traffic_minute")
    op.execute("DROP TABLE ingestion_status")
    op.execute("DROP TABLE aircraft")
