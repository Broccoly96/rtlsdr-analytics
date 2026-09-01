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


def test_settings_accepts_empty_string_notify_webhook_url_as_unset(monkeypatch):
    # NOTIFY_WEBHOOK_URL=  (empty, .env.example's documented "leave unset"
    # convention -- e.g. from `cp .env.example .env` without filling it
    # in) must behave identically to the var being absent entirely, not
    # raise as a malformed URL.
    _set_env(monkeypatch, {"NOTIFY_WEBHOOK_URL": ""})
    settings = Settings()
    assert settings.notify_webhook_url is None
    assert settings.notify_webhook_enabled is False


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


def test_settings_new_alert_toggles_disabled_by_default(monkeypatch):
    _set_env(monkeypatch)
    settings = Settings()
    assert settings.notify_emergency_squawk_enabled is False
    assert settings.notify_favorite_seen_enabled is False


def test_settings_rejects_emergency_squawk_enabled_without_url(monkeypatch):
    _set_env(monkeypatch, {"NOTIFY_EMERGENCY_SQUAWK_ENABLED": "true"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_favorite_seen_enabled_without_url(monkeypatch):
    _set_env(monkeypatch, {"NOTIFY_FAVORITE_SEEN_ENABLED": "true"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_accepts_emergency_squawk_enabled_with_shared_url(monkeypatch):
    _set_env(
        monkeypatch,
        {
            "NOTIFY_EMERGENCY_SQUAWK_ENABLED": "true",
            "NOTIFY_WEBHOOK_URL": "https://hooks.example.invalid/webhook",
        },
    )
    settings = Settings()
    assert settings.notify_emergency_squawk_enabled is True
    assert settings.notify_webhook_enabled is False  # independent toggles


def test_settings_metar_station_icao_unset_by_default(monkeypatch):
    _set_env(monkeypatch)
    settings = Settings()
    assert settings.metar_station_icao is None


def test_settings_metar_station_icao_normalizes_case(monkeypatch):
    _set_env(monkeypatch, {"METAR_STATION_ICAO": "rjtt"})
    settings = Settings()
    assert settings.metar_station_icao == "RJTT"


def test_settings_metar_station_icao_empty_string_is_unset(monkeypatch):
    _set_env(monkeypatch, {"METAR_STATION_ICAO": ""})
    settings = Settings()
    assert settings.metar_station_icao is None


def test_settings_rejects_malformed_metar_station_icao(monkeypatch):
    _set_env(monkeypatch, {"METAR_STATION_ICAO": "toolong"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_defaults_beast_host_from_aircraft_url(monkeypatch):
    _set_env(
        monkeypatch,
        {"READSB_AIRCRAFT_URL": "http://host.docker.internal/tar1090/data/aircraft.json"},
    )
    settings = Settings()
    assert settings.readsb_beast_host == "host.docker.internal"
    assert settings.readsb_beast_port == 30005


def test_settings_readsb_beast_host_override_respected(monkeypatch):
    _set_env(monkeypatch, {"READSB_BEAST_HOST": "beast.example.invalid"})
    settings = Settings()
    assert settings.readsb_beast_host == "beast.example.invalid"


def test_settings_rejects_out_of_range_beast_port(monkeypatch):
    _set_env(monkeypatch, {"READSB_BEAST_PORT": "0"})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_accepts_empty_string_beast_host_as_unset(monkeypatch):
    # READSB_BEAST_HOST= (empty, matching .env.example's documented "leave
    # unset" convention) must derive from READSB_AIRCRAFT_URL, not become a
    # literal empty-string host.
    _set_env(
        monkeypatch,
        {
            "READSB_AIRCRAFT_URL": "http://host.docker.internal/tar1090/data/aircraft.json",
            "READSB_BEAST_HOST": "",
        },
    )
    settings = Settings()
    assert settings.readsb_beast_host == "host.docker.internal"


def test_settings_accepts_empty_string_beast_port_as_default(monkeypatch):
    # READSB_BEAST_PORT= must not crash trying to parse "" as int.
    _set_env(monkeypatch, {"READSB_BEAST_PORT": ""})
    settings = Settings()
    assert settings.readsb_beast_port == 30005


def test_settings_public_hostname_is_optional_and_normalized(monkeypatch):
    _set_env(monkeypatch, {"PUBLIC_HOSTNAME": "Public.BroccoliNet.com."})
    assert Settings().public_hostname == "public.broccolinet.com"


@pytest.mark.parametrize(
    "hostname",
    [
        "https://public.broccolynet.com",
        "public.broccolynet.com/path",
        "public.broccolynet.com:443",
        "*.broccolynet.com",
        "single-label",
    ],
)
def test_settings_rejects_malformed_public_hostname(monkeypatch, hostname):
    _set_env(monkeypatch, {"PUBLIC_HOSTNAME": hostname})
    with pytest.raises(ValidationError):
        Settings()


def test_settings_missing_required_field_raises(monkeypatch):
    for key in BASE_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError):
        Settings()
