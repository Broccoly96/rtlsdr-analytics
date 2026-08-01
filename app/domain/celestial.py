"""Low-precision solar position (the standard Astronomical Almanac / NOAA
solar-position algorithm, accurate to roughly 0.01 degrees through 2100 --
far finer than this feature needs) -- backs Milestone LL's "transit
alert": flagging when a live aircraft's position as seen from the
receiver nearly lines up with the sun.

Stdlib math/datetime only, matching this app's other domain modules
(app/domain/bands.py, app/domain/geo.py) -- no new runtime dependency.
Moon position is deliberately out of scope for now: its orbital elements
are meaningfully more complex to get right and validate than the sun's
(see PLAN.md Milestone LL) -- a possible follow-up, not this milestone.

Azimuth is always a compass bearing (0-360, measured clockwise from
North), matching app/domain/geo.py's bearing_deg convention throughout
this codebase -- not the "from South" convention some astronomy
references use.

IMPORTANT: this has not been cross-checked against a real compass/device
in the field (no such hardware is available in this session) -- treat the
computed azimuth as provisional until verified on the real deployment
(see PLAN.md Milestone LL's session log) before tightening
ANGULAR_SEPARATION_THRESHOLD_DEG or trusting it for anything beyond a
low-stakes "hey, maybe go look up" alert.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

# The sun's apparent angular diameter is ~0.5 degrees; this threshold adds
# generous margin for this algorithm's own low-precision approximation and
# for the fact that "worth a look" doesn't require exact alignment.
ANGULAR_SEPARATION_THRESHOLD_DEG = 2.0

_J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class CelestialPosition:
    azimuth_deg: float  # compass bearing from North, clockwise, [0, 360)
    elevation_deg: float  # degrees above the horizon; negative = below


def _days_since_j2000(dt_utc: datetime) -> float:
    return (dt_utc - _J2000).total_seconds() / 86400.0


def solar_position(dt_utc: datetime, lat_deg: float, lon_deg: float) -> CelestialPosition:
    """The sun's apparent azimuth/elevation as seen from (lat_deg, lon_deg)
    at dt_utc (must be timezone-aware, any timezone -- converted to UTC
    internally)."""
    n = _days_since_j2000(dt_utc.astimezone(UTC))

    mean_lon_deg = (280.460 + 0.9856474 * n) % 360.0
    mean_anomaly = math.radians((357.528 + 0.9856003 * n) % 360.0)
    ecliptic_lon = math.radians(mean_lon_deg) + math.radians(
        1.915 * math.sin(mean_anomaly) + 0.020 * math.sin(2 * mean_anomaly)
    )
    obliquity = math.radians(23.439 - 0.0000004 * n)

    right_ascension = math.atan2(
        math.cos(obliquity) * math.sin(ecliptic_lon), math.cos(ecliptic_lon)
    )
    declination = math.asin(math.sin(obliquity) * math.sin(ecliptic_lon))

    gmst_deg = (280.46061837 + 360.98564736629 * n) % 360.0
    hour_angle = math.radians((gmst_deg + lon_deg - math.degrees(right_ascension)) % 360.0)

    lat = math.radians(lat_deg)
    sin_elevation = math.sin(declination) * math.sin(lat) + math.cos(declination) * math.cos(
        lat
    ) * math.cos(hour_angle)
    sin_elevation = max(-1.0, min(1.0, sin_elevation))
    elevation = math.asin(sin_elevation)

    # atan2 form (quadrant-safe, unlike the acos form) giving azimuth
    # measured from South, positive westward -- the natural output of the
    # hour-angle formulation; +180 converts to this codebase's North-
    # clockwise compass convention.
    azimuth_from_south = math.atan2(
        math.sin(hour_angle),
        math.cos(hour_angle) * math.sin(lat) - math.tan(declination) * math.cos(lat),
    )
    azimuth = (math.degrees(azimuth_from_south) + 180.0) % 360.0

    return CelestialPosition(azimuth_deg=azimuth, elevation_deg=math.degrees(elevation))


def angular_separation_deg(
    az1_deg: float, el1_deg: float, az2_deg: float, el2_deg: float
) -> float:
    """Great-circle angular separation between two (azimuth, elevation)
    points on the sky, in degrees -- the "close enough to call it a
    transit" check."""
    az1, el1, az2, el2 = (
        math.radians(az1_deg),
        math.radians(el1_deg),
        math.radians(az2_deg),
        math.radians(el2_deg),
    )
    cos_sep = math.sin(el1) * math.sin(el2) + math.cos(el1) * math.cos(el2) * math.cos(az1 - az2)
    cos_sep = max(-1.0, min(1.0, cos_sep))
    return math.degrees(math.acos(cos_sep))
