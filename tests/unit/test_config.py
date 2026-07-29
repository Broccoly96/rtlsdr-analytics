import pytest
from pydantic import ValidationError

from app.config import Settings

BASE_ENV = {
    "READSB_AIRCRAFT_URL": "http://127.0.0.1/tar1090/data/aircraft.json",
    "RECEIVER_LAT": "35.0",
    "RECEIVER_LON": "139.0",
    "DATABASE_URL": "postgresql://adsb:pw@localhost:5432/adsb",
}


def _set_env(monkeypatch, overrides=None):
    env = dict(BASE_ENV, **(overrides or {}))
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_settings_load_with_defaults(monkeypatch):
    _set_env(monkeypatch)
    settings = Settings()
    assert settings.poll_interval_seconds == 5.0
    assert settings.track_sample_seconds == 30.0
    assert settings.raw_retention_days == 30
    assert settings.display_timezone == "Asia/Tokyo"
    assert settings.app_bind_host == "127.0.0.1"
    assert settings.app_port == 8088


def test_settings_rejects_bad_url(monkeypatch):
    _set_env(monkeypatch, {"READSB_AIRCRAFT_URL": "not-a-url"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_out_of_range_latitude(monkeypatch):
    _set_env(monkeypatch, {"RECEIVER_LAT": "200"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_out_of_range_longitude(monkeypatch):
    _set_env(monkeypatch, {"RECEIVER_LON": "-200"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_bad_timezone(monkeypatch):
    _set_env(monkeypatch, {"DISPLAY_TIMEZONE": "Not/AZone"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_non_positive_poll_interval(monkeypatch):
    _set_env(monkeypatch, {"POLL_INTERVAL_SECONDS": "0"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_bad_database_url(monkeypatch):
    _set_env(monkeypatch, {"DATABASE_URL": "mysql://x"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_out_of_range_port(monkeypatch):
    _set_env(monkeypatch, {"APP_PORT": "70000"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_notify_webhook_disabled_by_default(monkeypatch):
    _set_env(monkeypatch)
    settings = Settings()
    assert settings.notify_webhook_enabled is False
    assert settings.notify_webhook_url is None


def test_settings_rejects_notify_enabled_without_url(monkeypatch):
    _set_env(monkeypatch, {"NOTIFY_WEBHOOK_ENABLED": "true"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_bad_notify_webhook_url(monkeypatch):
    _set_env(
        monkeypatch,
        {"NOTIFY_WEBHOOK_ENABLED": "true", "NOTIFY_WEBHOOK_URL": "not-a-url"},
    )
    with pytest.raises(ValidationError):
        Settings()


def test_settings_accepts_valid_notify_webhook_config(monkeypatch):
    _set_env(
        monkeypatch,
        {
            "NOTIFY_WEBHOOK_ENABLED": "true",
            "NOTIFY_WEBHOOK_URL": "https://hooks.example.invalid/webhook",
        },
    )
    settings = Settings()
    assert settings.notify_webhook_enabled is True
    assert settings.notify_webhook_url == "https://hooks.example.invalid/webhook"


def test_settings_missing_required_field_raises(monkeypatch):
    for key in BASE_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError):
        Settings()
