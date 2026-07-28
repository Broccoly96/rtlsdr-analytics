"""Pydantic response models for all API endpoints, so response shapes are
visible in the generated OpenAPI schema (PLAN.md Milestone C-1)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str


class ConfigResponse(BaseModel):
    map_style_url: str
    map_show_receiver_marker: bool
    map_receiver_marker_precision: int
    display_timezone: str
    version: str
    git_revision: str | None


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ok"] = "ok"


class StatusResponse(BaseModel):
    generated_at: datetime
    last_ingestion_at: datetime | None
    ingestion_state: Literal["ok", "stale", "error", "no_data"]
    active_aircraft_count: int
    position_aircraft_count: int
    data_age_seconds: float | None
    display_timezone: str


class TrafficBucketResponse(BaseModel):
    bucket_at: datetime
    active_aircraft_count: int
    position_aircraft_count: int
    message_count_delta: int


class TrafficResponse(BaseModel):
    hours: int
    buckets: list[TrafficBucketResponse]
    unique_aircraft_count: int


class RankingEntryResponse(BaseModel):
    icao: str
    callsign: str | None
    distance_km: float
    bearing_deg: float | None
    altitude_ft: float | None
    observed_at: datetime


class RankingsResponse(BaseModel):
    hours: int
    limit: int
    farthest: list[RankingEntryResponse]
    closest: list[RankingEntryResponse]


class RecentAircraftResponse(BaseModel):
    icao: str
    callsign: str | None
    first_seen_at: datetime
    last_seen_at: datetime


class GeoJSONMultiLineString(BaseModel):
    type: Literal["MultiLineString"] = "MultiLineString"
    coordinates: list[list[list[float]]]  # [[[lon, lat], ...], ...] per segment


class TrackFeatureProperties(BaseModel):
    icao: str
    callsign: str | None
    last_altitude_ft: float | None
    last_ground_speed_kt: float | None
    last_distance_km: float | None
    last_observed_at: datetime


class TrackFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: GeoJSONMultiLineString
    properties: TrackFeatureProperties


class TracksResponse(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[TrackFeature]
