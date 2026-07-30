"""Pydantic response models for all API endpoints, so response shapes are
visible in the generated OpenAPI schema (PLAN.md Milestone C-1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str


class AltitudeBandResponse(BaseModel):
    key: str
    label: str
    max_ft: float | None
    color: str


class ConfigResponse(BaseModel):
    map_style_url: str
    map_show_receiver_marker: bool
    map_receiver_marker_precision: int
    display_timezone: str
    altitude_bands: list[AltitudeBandResponse]
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


class DailyTrafficSummaryResponse(BaseModel):
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


class TrafficDailyResponse(BaseModel):
    days: int
    daily: list[DailyTrafficSummaryResponse]


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


class BearingRangeEntryResponse(BaseModel):
    sector_index: int
    sector_center_deg: float
    max_distance_km: float | None
    sample_count: int


class BearingRangeResponse(BaseModel):
    hours: int
    sectors: list[BearingRangeEntryResponse]


class AltitudeBandRangeEntryResponse(BaseModel):
    band_key: str
    max_distance_km: float | None
    sample_count: int


class AltitudeRangeResponse(BaseModel):
    hours: int
    bands: list[AltitudeBandRangeEntryResponse]


class ReceptionBucketResponse(BaseModel):
    bucket_at: datetime
    message_count: int
    position_rate: float | None


class ReceptionResponse(BaseModel):
    hours: int
    buckets: list[ReceptionBucketResponse]


class RssiDistanceCellResponse(BaseModel):
    distance_bucket_km: float
    rssi_bucket_db: float
    count: int


class RssiByDistanceResponse(BaseModel):
    hours: int
    distance_bucket_km: float
    rssi_bucket_db: float
    cells: list[RssiDistanceCellResponse]


class HourOfDayEntryResponse(BaseModel):
    hour: int
    unique_aircraft_count: int


class HourOfDayResponse(BaseModel):
    days: int
    hours: list[HourOfDayEntryResponse]


class HistogramBucketResponse(BaseModel):
    bucket_start: float
    count: int


class AltitudeHistogramResponse(BaseModel):
    hours: int
    bucket_ft: int
    buckets: list[HistogramBucketResponse]


class SpeedHistogramResponse(BaseModel):
    hours: int
    bucket_kt: int
    buckets: list[HistogramBucketResponse]


class CallsignHistoryEntryResponse(BaseModel):
    callsign: str
    first_seen_at: datetime
    last_seen_at: datetime


class AircraftHistoryResponse(BaseModel):
    icao: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_callsign: str | None
    days_observed: int
    total_pass_count: int
    total_observation_count: int
    callsign_history: list[CallsignHistoryEntryResponse]


class FrequentAircraftEntryResponse(BaseModel):
    icao: str
    last_callsign: str | None
    days_observed: int
    total_pass_count: int


class FrequentAircraftResponse(BaseModel):
    days: int
    limit: int
    aircraft: list[FrequentAircraftEntryResponse]


class GridCellResponse(BaseModel):
    lat: float
    lon: float
    count: int


class HeatmapResponse(BaseModel):
    hours: int
    cells: list[GridCellResponse]
