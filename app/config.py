"""Application configuration, validated eagerly at startup.

All environment variables are validated when Settings() is constructed so
misconfiguration fails fast with a clear message instead of surfacing as a
confusing runtime error later (PLAN.md SS6.3).
"""

from __future__ import annotations

from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    readsb_aircraft_url: str
    receiver_lat: float
    receiver_lon: float
    display_timezone: str = "Asia/Tokyo"
    poll_interval_seconds: float = 5.0
    track_sample_seconds: float = 30.0
    raw_retention_days: int = 30
    # Raw Beast-format TCP stream (app/api/routers/rawdata.py's live,
    # display-only "raw data" tab -- CLAUDE.md's original "no raw Beast"
    # scope, revisited at the user's explicit request). Host defaults to
    # READSB_AIRCRAFT_URL's own hostname in a model_validator below, since
    # it's normally the same readsb instance -- only needs overriding if
    # Beast is served from a different host than aircraft.json.
    readsb_beast_host: str | None = None
    readsb_beast_port: int = 30005
    database_url: str
    app_bind_host: str = "127.0.0.1"
    app_port: int = 8088
    # OpenFreeMap's "positron" style: free, no API key, no attribution
    # sign-up required (PLAN.md D-2's "quick MVP" option). Overridable via
    # MAP_STYLE_URL -- e.g. to a MapTiler style, or a self-hosted PMTiles
    # style in a later phase -- without any code change.
    map_style_url: str = "https://tiles.openfreemap.org/styles/positron"
    map_show_receiver_marker: bool = False
    map_receiver_marker_precision: int = 1
    # Opt-in Slack/Discord-compatible daily-summary webhook (app/notify.py),
    # sent once per day from app/dailyrollup.py. Disabled by default, and
    # absence of NOTIFY_WEBHOOK_URL must never fail startup on its own --
    # only enabling without a URL configured is an actual misconfiguration.
    notify_webhook_enabled: bool = False
    notify_webhook_url: str | None = None

    @field_validator("readsb_aircraft_url")
    @classmethod
    def _validate_readsb_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("READSB_AIRCRAFT_URL must start with http:// or https://")
        return value

    @field_validator("receiver_lat")
    @classmethod
    def _validate_lat(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError("RECEIVER_LAT must be between -90 and 90")
        return value

    @field_validator("receiver_lon")
    @classmethod
    def _validate_lon(cls, value: float) -> float:
        if not -180.0 <= value <= 180.0:
            raise ValueError("RECEIVER_LON must be between -180 and 180")
        return value

    @field_validator("display_timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"DISPLAY_TIMEZONE {value!r} is not a known IANA timezone") from exc
        return value

    @field_validator("poll_interval_seconds", "track_sample_seconds")
    @classmethod
    def _validate_positive_seconds(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be a positive number of seconds")
        return value

    @field_validator("raw_retention_days")
    @classmethod
    def _validate_retention(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("RAW_RETENTION_DAYS must be a positive integer")
        return value

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        if not value.startswith(("postgres://", "postgresql://")):
            raise ValueError("DATABASE_URL must be a postgres:// or postgresql:// URL")
        return value

    @field_validator("readsb_beast_host", mode="before")
    @classmethod
    def _empty_beast_host_is_unset(cls, value: str | None) -> str | None:
        # An empty string (READSB_BEAST_HOST=, .env.example's documented
        # "leave unset" convention) means "derive it", same as the env var
        # being absent entirely -- see _default_readsb_beast_host below.
        return None if value == "" else value

    @field_validator("readsb_beast_port", mode="before")
    @classmethod
    def _empty_beast_port_is_default(cls, value: object) -> object:
        # Must run before int coercion: an empty string can't be parsed as
        # int at all, so this has to intercept it pre-coercion rather than
        # follow the "" -> None pattern used for the (nullable) host above.
        return 30005 if value == "" else value

    @field_validator("app_port", "readsb_beast_port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("port must be between 1 and 65535")
        return value

    @field_validator("notify_webhook_url")
    @classmethod
    def _validate_notify_webhook_url(cls, value: str | None) -> str | None:
        # An empty string (NOTIFY_WEBHOOK_URL=, .env.example's documented
        # "leave unset" convention) means "not configured", same as the env
        # var being absent entirely -- not a malformed URL.
        if value == "":
            return None
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("NOTIFY_WEBHOOK_URL must start with http:// or https://")
        return value

    @model_validator(mode="after")
    def _validate_notify_webhook_enabled_has_url(self) -> Settings:
        if self.notify_webhook_enabled and not self.notify_webhook_url:
            raise ValueError("NOTIFY_WEBHOOK_URL must be set when NOTIFY_WEBHOOK_ENABLED is true")
        return self

    @model_validator(mode="after")
    def _default_readsb_beast_host(self) -> Settings:
        if self.readsb_beast_host is None:
            hostname = urlparse(self.readsb_aircraft_url).hostname
            if not hostname:
                raise ValueError(
                    "could not derive READSB_BEAST_HOST from READSB_AIRCRAFT_URL "
                    "-- set READSB_BEAST_HOST explicitly"
                )
            self.readsb_beast_host = hostname
        return self
