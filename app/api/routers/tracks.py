"""GET /api/tracks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_pool
from app.api.schemas import (
    GeoJSONMultiLineString,
    TrackFeature,
    TrackFeatureProperties,
    TracksResponse,
)
from app.db.queries.tracks import get_tracks

router = APIRouter(prefix="/api", tags=["tracks"])


@router.get("/tracks", response_model=TracksResponse)
async def get_tracks_endpoint(
    hours: float = Query(6, ge=0.25, le=72),
    pool=Depends(get_pool),
) -> TracksResponse:
    aircraft_tracks = await get_tracks(pool, hours)
    features = [
        TrackFeature(
            geometry=GeoJSONMultiLineString(
                coordinates=[
                    [[point.lon, point.lat, point.altitude_ft] for point in segment]
                    for segment in track.segments
                ]
            ),
            properties=TrackFeatureProperties(
                icao=track.icao,
                callsign=track.callsign,
                last_altitude_ft=track.last_altitude_ft,
                last_ground_speed_kt=track.last_ground_speed_kt,
                last_distance_km=track.last_distance_km,
                last_observed_at=track.last_observed_at,
            ),
        )
        for track in aircraft_tracks
        if track.segments  # skip aircraft fully decimated away (shouldn't happen, but be safe)
    ]
    return TracksResponse(features=features)
