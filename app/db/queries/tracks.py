"""Read queries + segmentation/decimation logic backing /api/tracks.

A single query fetches observations for the top-N most recently active
aircraft in one shot (no N+1: PLAN.md's C-8 requirement) -- segmentation
and point-budget decimation then happen in Python, since they depend on
cross-row comparisons that don't map cleanly onto a single SQL query.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import asyncpg

from app.collector.geo import haversine_distance_km

QUERY_TIMEOUT_SECONDS = 5.0
MAX_AIRCRAFT = 100
MAX_TOTAL_POINTS = 10_000
MAX_GAP_SECONDS = 120.0
MAX_IMPLIED_SPEED_KT = 1200.0
KM_PER_NM = 1.852


@dataclass(frozen=True, slots=True)
class TrackPoint:
    observed_at: datetime
    lat: float
    lon: float
    altitude_ft: float | None


@dataclass(frozen=True, slots=True)
class AircraftTrack:
    icao: str
    callsign: str | None
    last_altitude_ft: float | None
    last_ground_speed_kt: float | None
    last_distance_km: float | None
    last_observed_at: datetime
    segments: list[list[TrackPoint]]


async def get_tracks(pool: asyncpg.Pool, hours: int) -> list[AircraftTrack]:
    since = datetime.now(UTC) - timedelta(hours=hours)

    top_icaos_rows = await pool.fetch(
        "SELECT icao FROM aircraft WHERE last_seen_at >= $1 ORDER BY last_seen_at DESC LIMIT $2",
        since,
        MAX_AIRCRAFT,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    icaos = [row["icao"] for row in top_icaos_rows]
    if not icaos:
        return []

    rows = await pool.fetch(
        """
        SELECT icao, callsign, observed_at, lat, lon, altitude_ft, ground_speed_kt, distance_km
        FROM observations
        WHERE icao = ANY($1::text[]) AND observed_at >= $2
        ORDER BY icao, observed_at
        """,
        icaos,
        since,
        timeout=QUERY_TIMEOUT_SECONDS,
    )

    by_icao: dict[str, list] = {}
    for row in rows:
        by_icao.setdefault(row["icao"], []).append(row)

    tracks = [_build_track(icao, icao_rows) for icao, icao_rows in by_icao.items()]
    return _decimate_to_budget(tracks, MAX_TOTAL_POINTS)


async def get_aircraft_track(pool: asyncpg.Pool, icao: str, hours: int) -> AircraftTrack | None:
    """Same segmentation/shape as get_tracks, but for one aircraft rather
    than the top-N most recently active -- backs the 3D flight globe's
    historical track and could enrich the aircraft-detail sidebar later.
    None if the aircraft has no positions in the window (not necessarily
    unknown -- an aircraft can exist in `aircraft` with no `observations`
    rows in a short window, same as get_tracks never 404s either)."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = await pool.fetch(
        """
        SELECT icao, callsign, observed_at, lat, lon, altitude_ft, ground_speed_kt, distance_km
        FROM observations
        WHERE icao = $1 AND observed_at >= $2 AND lat IS NOT NULL AND lon IS NOT NULL
        ORDER BY observed_at
        """,
        icao,
        since,
        timeout=QUERY_TIMEOUT_SECONDS,
    )
    if not rows:
        return None
    return _build_track(icao, rows)


def _build_track(icao: str, rows: list) -> AircraftTrack:
    segments: list[list[TrackPoint]] = []
    current: list[TrackPoint] = []
    previous_row = None

    for row in rows:
        point = TrackPoint(row["observed_at"], row["lat"], row["lon"], row["altitude_ft"])
        if previous_row is not None:
            elapsed = (row["observed_at"] - previous_row["observed_at"]).total_seconds()
            distance_km = haversine_distance_km(
                previous_row["lat"], previous_row["lon"], row["lat"], row["lon"]
            )
            implied_speed_kt = (distance_km / elapsed * 3600 / KM_PER_NM) if elapsed > 0 else 0.0
            # Don't connect points across a long reception gap or an
            # implausible position jump (e.g. a bad fix) with a straight line.
            if elapsed > MAX_GAP_SECONDS or implied_speed_kt > MAX_IMPLIED_SPEED_KT:
                if current:
                    segments.append(current)
                current = []
        current.append(point)
        previous_row = row

    if current:
        segments.append(current)

    last_row = rows[-1]
    return AircraftTrack(
        icao=icao,
        callsign=last_row["callsign"],
        last_altitude_ft=last_row["altitude_ft"],
        last_ground_speed_kt=last_row["ground_speed_kt"],
        last_distance_km=last_row["distance_km"],
        last_observed_at=last_row["observed_at"],
        segments=segments,
    )


def _decimate_to_budget(tracks: list[AircraftTrack], max_points: int) -> list[AircraftTrack]:
    total_points = sum(len(segment) for track in tracks for segment in track.segments)
    if total_points <= max_points:
        return tracks

    ratio = max_points / total_points
    decimated: list[AircraftTrack] = []
    for track in tracks:
        new_segments = []
        for segment in track.segments:
            stride = max(1, round(1 / ratio))
            kept = segment[::stride]
            if kept and kept[-1] is not segment[-1]:
                kept.append(segment[-1])  # always keep the most recent point
            if kept:
                new_segments.append(kept)
        decimated.append(replace(track, segments=new_segments))
    return decimated
