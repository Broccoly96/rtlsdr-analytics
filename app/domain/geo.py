"""Great-circle distance and initial bearing calculations, used to compute
each observation's distance/bearing from the configured receiver location.

Moved here from app/collector/geo.py (Milestone LL of the 2026-08 feature
roadmap) -- pure geometry with no collector-specific dependency, and the
sun-transit-alert feature needed it importable from the API layer
(app/api/routers/aircraft_positions.py) too. app/db/queries/tracks.py was
already importing this cross-package before the move (collector -> API),
which is the "reads oddly" smell that prompted moving it now rather than
adding a third cross-package import on top.
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360
