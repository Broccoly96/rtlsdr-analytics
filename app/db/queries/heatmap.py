"""Read query backing GET /api/heatmap -- a position-density grid for the
map's heatmap overlay, with optional altitude-band/hour-of-day/day-of-week
filters. Cell truncation favors the densest cells (ORDER BY count DESC
LIMIT), the same "budget, don't drop everything" approach tracks.py's
MAX_TOTAL_POINTS decimation uses -- avoiding a repeat of Milestone C-8's
hours=168/1.18MB uncapped-response mistake.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg

from app.domain.bands import band_case_sql

QUERY_TIMEOUT_SECONDS = 5.0
MAX_GRID_CELLS = 5000
DEFAULT_CELL_DEG = 0.01


@dataclass(frozen=True, slots=True)
class GridCell:
    lat: float
    lon: float
    count: int


async def grid_density(
    pool: asyncpg.Pool,
    hours: int,
    *,
    cell_deg: float = DEFAULT_CELL_DEG,
    altitude_band: str | None = None,
    hour_of_day: int | None = None,
    day_of_week: int | None = None,
) -> list[GridCell]:
    since = datetime.now(UTC) - timedelta(hours=hours)
    conditions = ["observed_at >= $1", "lat IS NOT NULL", "lon IS NOT NULL"]
    params: list[object] = [since]

    if altitude_band is not None:
        params.append(altitude_band)
        conditions.append(f"({band_case_sql('altitude_ft')}) = ${len(params)}")
    if hour_of_day is not None:
        params.append(hour_of_day)
        conditions.append(f"extract(hour FROM observed_at)::int = ${len(params)}")
    if day_of_week is not None:
        # Postgres EXTRACT(DOW): 0=Sunday .. 6=Saturday -- passed straight
        # through from the API's day_of_week param, no remapping needed.
        params.append(day_of_week)
        conditions.append(f"extract(dow FROM observed_at)::int = ${len(params)}")

    params.append(cell_deg)
    cell_param = len(params)
    params.append(MAX_GRID_CELLS)
    limit_param = len(params)

    sql = f"""
        SELECT
            round(lat / ${cell_param}) * ${cell_param} AS grid_lat,
            round(lon / ${cell_param}) * ${cell_param} AS grid_lon,
            count(*) AS cell_count
        FROM observations
        WHERE {" AND ".join(conditions)}
        GROUP BY grid_lat, grid_lon
        ORDER BY cell_count DESC
        LIMIT ${limit_param}
    """
    rows = await pool.fetch(sql, *params, timeout=QUERY_TIMEOUT_SECONDS)
    return [GridCell(row["grid_lat"], row["grid_lon"], row["cell_count"]) for row in rows]
