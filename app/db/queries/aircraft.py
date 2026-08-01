"""Read queries backing /api/aircraft/recent and /api/aircraft/nationalities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

from app.domain.nationality import country_for_icao

QUERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class RecentAircraft:
    icao: str
    callsign: str | None
    first_seen_at: datetime
    last_seen_at: datetime


async def get_recent_aircraft(
    pool: asyncpg.Pool, hours: int, limit: int, offset: int
) -> list[RecentAircraft]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        "SELECT icao, last_callsign AS callsign, first_seen_at, last_seen_at "
        "FROM aircraft WHERE last_seen_at >= $1 ORDER BY last_seen_at DESC LIMIT $2 OFFSET $3",
        since,
        limit,
        offset,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [RecentAircraft(**dict(row)) for row in rows]


_ARCHIVE_SORT_COLUMNS = {
    "last_seen_at": "a.last_seen_at",
    "first_seen_at": "a.first_seen_at",
    "days_observed": "days_observed",
    "total_pass_count": "total_pass_count",
    "icao": "a.icao",
}


@dataclass(frozen=True, slots=True)
class ArchiveEntry:
    icao: str
    callsign: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    days_observed: int
    total_pass_count: int


async def get_archive_total(pool: asyncpg.Pool, query: str | None) -> int:
    return await pool.fetchval(
        "SELECT count(*) FROM aircraft a WHERE ($1::text IS NULL OR a.icao ILIKE '%'||$1||'%' "
        "OR a.last_callsign ILIKE '%'||$1||'%')",
        query,
        timeout=QUERY_TIMEOUT_SECONDS,
    )


async def get_archive_page(
    pool: asyncpg.Pool,
    *,
    query: str | None,
    sort: str,
    descending: bool,
    limit: int,
    offset: int,
) -> list[ArchiveEntry]:
    """Full-archive search/browse over every aircraft ever seen -- backs
    /static/archive.html. `sort` is validated against a fixed whitelist
    (never interpolated as raw user input) to avoid SQL injection via the
    ORDER BY clause, which can't be parameterized with $N placeholders."""
    sort_column = _ARCHIVE_SORT_COLUMNS.get(sort, _ARCHIVE_SORT_COLUMNS["last_seen_at"])
    direction = "DESC" if descending else "ASC"
    rows = await pool.fetch(
        f"""
        SELECT a.icao, a.last_callsign AS callsign, a.first_seen_at, a.last_seen_at,
               COALESCE(ad.days_observed, 0)::int AS days_observed,
               COALESCE(ad.total_pass_count, 0)::int AS total_pass_count
        FROM aircraft a
        LEFT JOIN (
            SELECT icao, count(DISTINCT day) AS days_observed, sum(pass_count) AS total_pass_count
            FROM aircraft_day GROUP BY icao
        ) ad ON ad.icao = a.icao
        WHERE ($1::text IS NULL OR a.icao ILIKE '%'||$1||'%' OR a.last_callsign ILIKE '%'||$1||'%')
        ORDER BY {sort_column} {direction}
        LIMIT $2 OFFSET $3
        """,
        query,
        limit,
        offset,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    return [ArchiveEntry(**dict(row)) for row in rows]


@dataclass(frozen=True, slots=True)
class OnThisDayEntry:
    icao: str
    callsign: str | None
    pass_count: int


@dataclass(frozen=True, slots=True)
class OnThisDayYear:
    year: int
    aircraft: list[OnThisDayEntry]


ON_THIS_DAY_LIMIT_PER_YEAR = 10


async def get_on_this_day(
    pool: asyncpg.Pool, month: int, day: int, exclude_year: int
) -> list[OnThisDayYear]:
    """Which aircraft were observed on this exact calendar date in past
    years -- from `aircraft_day` (kept long-term), never raw `observations`
    (purged after RAW_RETENTION_DAYS, so most past years wouldn't have any
    left anyway)."""
    rows = await pool.fetch(
        """
        SELECT extract(year FROM ad.day)::int AS year, ad.icao,
               a.last_callsign AS callsign, ad.pass_count
        FROM aircraft_day ad
        JOIN aircraft a ON a.icao = ad.icao
        WHERE extract(month FROM ad.day) = $1 AND extract(day FROM ad.day) = $2
          AND extract(year FROM ad.day) != $3
        ORDER BY year DESC, ad.pass_count DESC
        """,
        month,
        day,
        exclude_year,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    by_year: dict[int, list[OnThisDayEntry]] = {}
    for row in rows:
        entries = by_year.setdefault(row["year"], [])
        if len(entries) < ON_THIS_DAY_LIMIT_PER_YEAR:
            entries.append(
                OnThisDayEntry(
                    icao=row["icao"], callsign=row["callsign"], pass_count=row["pass_count"]
                )
            )
    return [
        OnThisDayYear(year=year, aircraft=entries)
        for year, entries in sorted(by_year.items(), reverse=True)
    ]


@dataclass(frozen=True, slots=True)
class NationalityCount:
    code: str
    name: str
    aircraft_count: int
    first_seen_at: datetime


async def get_nationality_summary(pool: asyncpg.Pool) -> list[NationalityCount]:
    """Groups every aircraft ever seen by inferred country (see
    app/domain/nationality.py) -- backs the "flag collection" page.
    Grouping happens in Python, not SQL, since country_for_icao is a
    range lookup over a small fixed table, not something worth expressing
    as SQL BETWEEN clauses. `aircraft` only has as many rows as distinct
    ICAOs ever observed, so fetching the whole (icao, first_seen_at)
    column pair is cheap even after months of collection.
    """
    rows = await pool.fetch(
        "SELECT icao, first_seen_at FROM aircraft", timeout=QUERY_TIMEOUT_SECONDS
    )
    counts: dict[str, list] = {}
    for row in rows:
        info = country_for_icao(row["icao"])
        if info is None:
            continue
        entry = counts.setdefault(info.code, [info.name, 0, row["first_seen_at"]])
        entry[1] += 1
        if row["first_seen_at"] < entry[2]:
            entry[2] = row["first_seen_at"]
    return [
        NationalityCount(code=code, name=name, aircraft_count=count, first_seen_at=first_seen_at)
        for code, (name, count, first_seen_at) in counts.items()
    ]
