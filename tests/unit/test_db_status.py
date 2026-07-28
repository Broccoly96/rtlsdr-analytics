from __future__ import annotations

from scripts.db_status import _human_bytes, render_report


def test_human_bytes_scales_units():
    assert _human_bytes(500) == "500.0B"
    assert _human_bytes(2048) == "2.0KB"
    assert _human_bytes(5 * 1024 * 1024) == "5.0MB"
    assert _human_bytes(3 * 1024**4) == "3.0TB"


def test_render_report_contains_no_secrets_and_key_fields():
    status = {
        "db_size_bytes": 1024,
        "table_sizes_bytes": {
            "aircraft": 100,
            "observations": 900,
            "traffic_minute": 20,
            "ingestion_status": 4,
        },
        "observation_count": 42,
        "oldest_observation_at": "2026-01-01T00:00:00Z",
        "newest_observation_at": "2026-01-02T00:00:00Z",
        "observations_last_24h": 10,
        "estimated_daily_growth_bytes": 1000.0,
        "estimated_30d_size_bytes": 30000.0,
        "last_ingestion_at": "2026-01-02T00:00:00Z",
        "last_ingestion_success": True,
    }

    report = render_report(status)

    assert "42" in report
    assert "observations" in report
    assert "postgresql://" not in report
    assert "password" not in report.lower()
