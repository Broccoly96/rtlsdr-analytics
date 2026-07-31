"""Read/aggregation queries for calendar-day traffic summaries.

`compute_daily_summary` is the shared aggregation logic called from both
the write path (app/dailyrollup.py, for a finished past day) and the read
path (Milestone N's "today", which isn't rolled up into `traffic_day`
yet) -- same pool-taking, dataclass-returning shape as every other query
module in this package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import asyncpg

QUERY_TIMEOUT_SECONDS = 5.0
FIRST_SEEN_TODAY_LIMIT = 20


@dataclass(frozen=True, slots=True)
class FirstSeenAircraft:
    icao: str
    callsign: str | None
    first_seen_at: datetime


@dataclass(frozen=True, slots=True)
class DailyTrafficSummary:
    day: date
    unique_aircraft_count: int
    max_concurrent_count: int
    message_count_total: int
    position_aircraft_count_max: int
    farthest_icao: str | None
    farthest_distance_km: float | None
    closest_icao: str | None
    closest_distance_km: float | None
    most_observed_icao: str | None
    most_observed_count: int | None
    # Only populated by compute_daily_summary ("today", always computed
    # live) -- None/empty for get_traffic_day's past-day path, since
    # traffic_day has no columns for these and was never asked to carry
    # them (no migration needed: these all have defaults, so **dict(row)
    # from that table's narrower column set still constructs fine).
    farthest_callsign: str | None = None
    closest_callsign: str | None = None
    most_observed_callsign: str | None = None
    fastest_icao: str | None = None
    fastest_callsign: str | None = None
    fastest_ground_speed_kt: float | None = None
    highest_icao: str | None = None
    highest_callsign: str | None = None
    highest_altitude_ft: float | None = None
    first_seen_today: list[FirstSeenAircraft] = field(default_factory=list)


async def compute_daily_summary(
    pool: asyncpg.Pool, day: date, start_utc: datetime, end_utc: datetime
) -> DailyTrafficSummary:
    unique_count = await pool.fetchval(
        "SELECT count(DISTINCT icao) FROM observations "
        "WHERE observed_at >= $1 AND observed_at < $2",
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    minute_row = await pool.fetchrow(
        """
        SELECT
            coalesce(max(active_aircraft_count), 0) AS max_concurrent,
            coalesce(sum(message_count_delta), 0) AS message_total,
            coalesce(max(position_aircraft_count), 0) AS position_max
        FROM traffic_minute
        WHERE bucket_at >= $1 AND bucket_at < $2
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    # Same ORDER BY distance_km {ASC,DESC} LIMIT shape rankings.py already
    # uses successfully against ix_observations_distance_observed_at.
    # callsign comes from the SAME AIRCRAFT's temporally-nearest
    # non-null-callsign row that day, not necessarily the winning row's own
    # callsign -- a newly-acquired aircraft's first pings (disproportionately
    # likely to be the farthest, edge-of-range ones) are systematically
    # decoded before its callsign is (confirmed against real data: on a
    # sampled day, the max-distance row had a null callsign ~37% of the
    # time vs. ~6% for a random row). Still scoped to the aircraft's
    # activity *that day*, consistent with the original intent of not
    # attributing a later/different flight's callsign -- just no longer
    # tied to that one exact row, which can easily predate ident decoding.
    farthest = await pool.fetchrow(
        """
        WITH winner AS (
            SELECT icao, distance_km, observed_at FROM observations
            WHERE observed_at >= $1 AND observed_at < $2 AND distance_km IS NOT NULL
            ORDER BY distance_km DESC LIMIT 1
        )
        SELECT w.icao, w.distance_km,
            (SELECT o.callsign FROM observations o
             WHERE o.icao = w.icao AND o.observed_at >= $1 AND o.observed_at < $2
               AND o.callsign IS NOT NULL
             ORDER BY abs(extract(epoch FROM o.observed_at - w.observed_at)) ASC
             LIMIT 1) AS callsign
        FROM winner w
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    closest = await pool.fetchrow(
        """
        WITH winner AS (
            SELECT icao, distance_km, observed_at FROM observations
            WHERE observed_at >= $1 AND observed_at < $2 AND distance_km IS NOT NULL
            ORDER BY distance_km ASC LIMIT 1
        )
        SELECT w.icao, w.distance_km,
            (SELECT o.callsign FROM observations o
             WHERE o.icao = w.icao AND o.observed_at >= $1 AND o.observed_at < $2
               AND o.callsign IS NOT NULL
             ORDER BY abs(extract(epoch FROM o.observed_at - w.observed_at)) ASC
             LIMIT 1) AS callsign
        FROM winner w
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    # callsign here is that aircraft's most recent NON-NULL callsign
    # *within this day* (not the aircraft table's all-time last_callsign),
    # consistent with farthest/closest above being scoped to the day too.
    # FILTER (not just array_agg(...)[1]) so a null-callsign latest ping
    # doesn't mask an earlier real one that day -- same bug class as
    # farthest/closest, just far less likely to bite here since this
    # aggregates over every row the aircraft has that day, not one.
    most_observed = await pool.fetchrow(
        """
        SELECT icao, count(*) AS observation_count,
               (array_agg(callsign ORDER BY observed_at DESC)
                    FILTER (WHERE callsign IS NOT NULL))[1] AS callsign
        FROM observations
        WHERE observed_at >= $1 AND observed_at < $2
        GROUP BY icao ORDER BY observation_count DESC LIMIT 1
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    # Same "winning row's own callsign can be null" concern as
    # farthest/closest above, same fix: nearest-in-time non-null callsign
    # for that aircraft that day.
    fastest = await pool.fetchrow(
        """
        WITH winner AS (
            SELECT icao, ground_speed_kt, observed_at FROM observations
            WHERE observed_at >= $1 AND observed_at < $2 AND ground_speed_kt IS NOT NULL
            ORDER BY ground_speed_kt DESC LIMIT 1
        )
        SELECT w.icao, w.ground_speed_kt,
            (SELECT o.callsign FROM observations o
             WHERE o.icao = w.icao AND o.observed_at >= $1 AND o.observed_at < $2
               AND o.callsign IS NOT NULL
             ORDER BY abs(extract(epoch FROM o.observed_at - w.observed_at)) ASC
             LIMIT 1) AS callsign
        FROM winner w
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    highest = await pool.fetchrow(
        """
        WITH winner AS (
            SELECT icao, altitude_ft, observed_at FROM observations
            WHERE observed_at >= $1 AND observed_at < $2 AND altitude_ft IS NOT NULL
            ORDER BY altitude_ft DESC LIMIT 1
        )
        SELECT w.icao, w.altitude_ft,
            (SELECT o.callsign FROM observations o
             WHERE o.icao = w.icao AND o.observed_at >= $1 AND o.observed_at < $2
               AND o.callsign IS NOT NULL
             ORDER BY abs(extract(epoch FROM o.observed_at - w.observed_at)) ASC
             LIMIT 1) AS callsign
        FROM winner w
        """,
        start_utc,
        end_utc,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    first_seen_rows = await pool.fetch(
        """
        SELECT icao, last_callsign AS callsign, first_seen_at FROM aircraft
        WHERE first_seen_at >= $1 AND first_seen_at < $2
        ORDER BY first_seen_at DESC LIMIT $3
        """,
        start_utc,
        end_utc,
        FIRST_SEEN_TODAY_LIMIT,
        timeout=QUERY_TIMEOUT_SECONDS,
    )

    return DailyTrafficSummary(
        day=day,
        unique_aircraft_count=unique_count,
        max_concurrent_count=minute_row["max_concurrent"],
        message_count_total=minute_row["message_total"],
        position_aircraft_count_max=minute_row["position_max"],
        farthest_icao=farthest["icao"] if farthest else None,
        farthest_distance_km=farthest["distance_km"] if farthest else None,
        farthest_callsign=farthest["callsign"] if farthest else None,
        closest_icao=closest["icao"] if closest else None,
        closest_distance_km=closest["distance_km"] if closest else None,
        closest_callsign=closest["callsign"] if closest else None,
        most_observed_icao=most_observed["icao"] if most_observed else None,
        most_observed_count=most_observed["observation_count"] if most_observed else None,
        most_observed_callsign=most_observed["callsign"] if most_observed else None,
        fastest_icao=fastest["icao"] if fastest else None,
        fastest_callsign=fastest["callsign"] if fastest else None,
        fastest_ground_speed_kt=fastest["ground_speed_kt"] if fastest else None,
        highest_icao=highest["icao"] if highest else None,
        highest_callsign=highest["callsign"] if highest else None,
        highest_altitude_ft=highest["altitude_ft"] if highest else None,
        first_seen_today=[
            FirstSeenAircraft(row["icao"], row["callsign"], row["first_seen_at"])
            for row in first_seen_rows
        ],
    )


_TRAFFIC_DAY_COLUMNS = """
    day, unique_aircraft_count, max_concurrent_count, message_count_total,
    position_aircraft_count_max, farthest_icao, farthest_distance_km,
    closest_icao, closest_distance_km, most_observed_icao, most_observed_count
"""


async def get_traffic_day(pool: asyncpg.Pool, day: date) -> DailyTrafficSummary | None:
    row = await pool.fetchrow(
        f"SELECT {_TRAFFIC_DAY_COLUMNS} FROM traffic_day WHERE day = $1",
        day,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return DailyTrafficSummary(**dict(row)) if row else None


def _zero_summary(day: date) -> DailyTrafficSummary:
    return DailyTrafficSummary(
        day=day,
        unique_aircraft_count=0,
        max_concurrent_count=0,
        message_count_total=0,
        position_aircraft_count_max=0,
        farthest_icao=None,
        farthest_distance_km=None,
        closest_icao=None,
        closest_distance_km=None,
        most_observed_icao=None,
        most_observed_count=None,
    )


async def list_traffic_days(
    pool: asyncpg.Pool, start_day: date, end_day: date
) -> list[DailyTrafficSummary]:
    """[start_day, end_day] inclusive, zero-filled for days with no
    persisted rollup row yet (matches traffic.py's zero-filled-bucket
    convention)."""
    rows = await pool.fetch(
        f"SELECT {_TRAFFIC_DAY_COLUMNS} FROM traffic_day WHERE day >= $1 AND day <= $2",
        start_day,
        end_day,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    by_day = {row["day"]: row for row in rows}

    summaries: list[DailyTrafficSummary] = []
    cursor = start_day
    while cursor <= end_day:
        row = by_day.get(cursor)
        summaries.append(DailyTrafficSummary(**dict(row)) if row else _zero_summary(cursor))
        cursor += timedelta(days=1)
    return summaries
