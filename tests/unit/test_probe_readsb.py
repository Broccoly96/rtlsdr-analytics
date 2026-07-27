import json
from pathlib import Path

import pytest

from scripts import probe_readsb
from scripts.probe_readsb import (
    CheckResult,
    FetchResult,
    InvalidPayloadError,
    ReceiverLocation,
    Verdict,
    build_report,
    check_container_runtime,
    check_existing_services,
    check_memory_disk,
    check_network_ports,
    check_os_cpu,
    check_readsb_connectivity,
    check_receiver_location,
    check_time,
    detect_receiver_location,
    evaluate_liveness,
    main,
    parse_and_tally,
    render_markdown,
    to_json_dict,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


# --- parse_and_tally against the shared malformed-data fixtures ------------


def test_tally_sample_fixture():
    tally = parse_and_tally(_load("aircraft_sample.json"))
    assert tally.aircraft_count == 5
    assert tally.unique_icao_count == 5
    assert tally.field_presence_pct["hex"] == 100.0
    assert tally.field_presence_pct["lat"] == 100.0
    assert tally.field_presence_pct["lon"] == 100.0
    assert tally.field_presence_pct["seen"] == 100.0


def test_tally_empty_fixture_no_divide_by_zero():
    tally = parse_and_tally(_load("aircraft_empty.json"))
    assert tally.aircraft_count == 0
    assert tally.unique_icao_count == 0
    assert all(pct == 0.0 for pct in tally.field_presence_pct.values())


def test_tally_missing_fields_fixture():
    tally = parse_and_tally(_load("aircraft_missing_fields.json"))
    assert tally.aircraft_count == 3
    assert tally.unique_icao_count == 2
    assert tally.field_presence_pct["hex"] == pytest.approx(66.7)
    assert tally.field_presence_pct["lat"] == pytest.approx(33.3)


def test_tally_lat_only_fixture_counts_lat_and_lon_independently():
    tally = parse_and_tally(_load("aircraft_lat_only.json"))
    assert tally.aircraft_count == 2
    assert tally.field_presence_pct["lat"] == 50.0
    assert tally.field_presence_pct["lon"] == 50.0


def test_tally_ground_altitude_counts_string_value_as_present():
    tally = parse_and_tally(_load("aircraft_ground_altitude.json"))
    assert tally.aircraft_count == 1
    assert tally.field_presence_pct["alt_baro"] == 100.0


def test_tally_future_time_counts_negative_seen_as_present():
    tally = parse_and_tally(_load("aircraft_future_time.json"))
    assert tally.field_presence_pct["seen"] == 100.0
    assert tally.field_presence_pct["seen_pos"] == 100.0


def test_tally_out_of_range_coords_counts_present_regardless_of_range():
    tally = parse_and_tally(_load("aircraft_out_of_range_coords.json"))
    assert tally.aircraft_count == 2
    assert tally.field_presence_pct["lat"] == 100.0
    assert tally.field_presence_pct["lon"] == 100.0


def test_tally_duplicate_icao_fixture():
    tally = parse_and_tally(_load("aircraft_duplicate_icao.json"))
    assert tally.aircraft_count == 2
    assert tally.unique_icao_count == 1


# --- structural robustness (Phase 0 must never crash on a malformed feed) --


def test_parse_and_tally_missing_aircraft_key_raises_invalid_payload_error():
    with pytest.raises(InvalidPayloadError):
        parse_and_tally({"now": 123, "messages": 1})


def test_parse_and_tally_aircraft_not_a_list_raises_invalid_payload_error():
    with pytest.raises(InvalidPayloadError):
        parse_and_tally({"aircraft": "not-a-list"})


def test_parse_and_tally_handles_large_aircraft_count():
    payload = {"now": 1.0, "messages": 1, "aircraft": [{"hex": f"a{i:05x}"} for i in range(5000)]}
    tally = parse_and_tally(payload)
    assert tally.aircraft_count == 5000
    assert tally.unique_icao_count == 5000


def test_parse_and_tally_ignores_non_dict_entries():
    tally = parse_and_tally({"aircraft": [{"hex": "aaaaaa"}, "garbage", None, 42]})
    assert tally.aircraft_count == 4
    assert tally.unique_icao_count == 1


# --- evaluate_liveness -------------------------------------------------------


def _fetch(payload, error=None):
    return FetchResult(
        url="http://x",
        status_code=200,
        elapsed_ms=1.0,
        error=error,
        payload=payload,
        fetched_at=0.0,
    )


def test_liveness_pass_when_now_advances():
    result = evaluate_liveness(
        _fetch({"now": 1.0, "messages": 100}), _fetch({"now": 2.0, "messages": 100})
    )
    assert result.verdict == Verdict.PASS
    assert result.now_advanced is True


def test_liveness_warn_when_nothing_advances():
    result = evaluate_liveness(
        _fetch({"now": 1.0, "messages": 100}), _fetch({"now": 1.0, "messages": 100})
    )
    assert result.verdict == Verdict.WARN
    assert result.now_advanced is False
    assert result.messages_advanced is False


def test_liveness_unknown_when_second_fetch_failed():
    result = evaluate_liveness(_fetch({"now": 1.0}), _fetch(None, error="timeout"))
    assert result.verdict == Verdict.UNKNOWN


# --- check_readsb_connectivity: never leaks aircraft-level data ------------


def test_check_readsb_connectivity_never_includes_aircraft_values(monkeypatch):
    sample = _load("aircraft_sample.json")
    calls = iter([sample, sample])

    def fake_fetch(url, timeout=5.0):
        return _fetch(next(calls))

    monkeypatch.setattr(probe_readsb, "fetch_aircraft_json", fake_fetch)

    result = check_readsb_connectivity(
        probe_readsb.DEFAULT_CANDIDATE_URLS,
        "http://127.0.0.1/tar1090/data/aircraft.json",
        wait_seconds=0,
    )
    assert result.verdict in (Verdict.PASS, Verdict.WARN)
    rendered = json.dumps(result.details)
    assert "aaaaa1" not in rendered
    assert "35.68" not in rendered


def test_check_readsb_connectivity_fail_when_unreachable(monkeypatch):
    def fake_fetch(url, timeout=5.0):
        return _fetch(None, error="connection refused")

    monkeypatch.setattr(probe_readsb, "fetch_aircraft_json", fake_fetch)

    result = check_readsb_connectivity(probe_readsb.DEFAULT_CANDIDATE_URLS, None, wait_seconds=0)
    assert result.verdict == Verdict.FAIL


# --- detect_receiver_location -----------------------------------------------


def test_detect_receiver_location_from_env(tmp_path):
    location = detect_receiver_location(
        {"RECEIVER_LAT": "36.1234", "RECEIVER_LON": "139.5678"},
        receiver_json_path=tmp_path / "missing.json",
        readsb_conf_path=tmp_path / "missing.conf",
    )
    assert location is not None
    assert location.source == "env"
    assert location.lat == pytest.approx(36.1234)


def test_detect_receiver_location_from_receiver_json(tmp_path):
    receiver_json = tmp_path / "receiver.json"
    receiver_json.write_text(json.dumps({"lat": 36.24, "lon": 139.53}))
    location = detect_receiver_location(
        {}, receiver_json_path=receiver_json, readsb_conf_path=tmp_path / "missing.conf"
    )
    assert location is not None
    assert location.source == "readsb_receiver_json"


def test_detect_receiver_location_from_conf_file(tmp_path):
    conf = tmp_path / "readsb"
    conf.write_text('DECODER_OPTIONS="--device-type rtlsdr --lat 36.24 --lon 139.53 --gain auto"')
    location = detect_receiver_location(
        {}, receiver_json_path=tmp_path / "missing.json", readsb_conf_path=conf
    )
    assert location is not None
    assert location.source == "readsb_conf_file"


def test_detect_receiver_location_returns_none_when_nothing_found(tmp_path):
    location = detect_receiver_location(
        {}, receiver_json_path=tmp_path / "missing.json", readsb_conf_path=tmp_path / "missing.conf"
    )
    assert location is None


def test_receiver_location_report_never_contains_full_precision():
    location = ReceiverLocation(lat=36.123456, lon=139.654321, source="env")
    check = CheckResult(
        id="E",
        name="receiver location",
        verdict=Verdict.PASS,
        summary="detected",
        details={
            "source": location.source,
            "lat_rounded": location.rounded(1)[0],
            "lon_rounded": location.rounded(1)[1],
        },
    )
    report = build_report({"receiver_location": check}, "host")
    rendered_md = render_markdown(report)
    rendered_json = json.dumps(to_json_dict(report))
    assert "123456" not in rendered_md
    assert "654321" not in rendered_json


def test_check_receiver_location_unknown_when_not_found(tmp_path):
    result = check_receiver_location(
        {}, receiver_json_path=tmp_path / "missing.json", readsb_conf_path=tmp_path / "missing.conf"
    )
    assert result.verdict == Verdict.UNKNOWN


# --- threshold checks fed by shell facts ------------------------------------


def test_check_os_cpu_pass_on_x86_64():
    result = check_os_cpu({"os_cpu": {"arch": "x86_64", "distro_name": "Ubuntu", "cpu_cores": 8}})
    assert result.verdict == Verdict.PASS


def test_check_os_cpu_fail_on_other_arch():
    result = check_os_cpu({"os_cpu": {"arch": "aarch64"}})
    assert result.verdict == Verdict.FAIL


@pytest.mark.parametrize(
    ("mem_gib", "disk_gb", "expected"),
    [
        (0.5, 50.0, Verdict.FAIL),
        (10.0, 5.0, Verdict.FAIL),
        (1.5, 50.0, Verdict.WARN),
        (10.0, 20.0, Verdict.WARN),
        (10.0, 100.0, Verdict.PASS),
    ],
)
def test_check_memory_disk_thresholds(mem_gib, disk_gb, expected):
    facts = {
        "memory_disk": {
            "available_memory_bytes": int(mem_gib * 1024**3),
            "free_disk_bytes": int(disk_gb * 1000**3),
        }
    }
    assert check_memory_disk(facts).verdict == expected


def test_check_container_runtime_docker_absent_is_unknown_not_fail():
    result = check_container_runtime({"container_runtime": {"docker_installed": False}})
    assert result.verdict == Verdict.UNKNOWN
    assert result.details["decision_required"] is True
    assert {opt["id"] for opt in result.details["options"]} == {
        "install_docker",
        "systemd_venv_postgres",
    }


def test_check_container_runtime_pass_when_installed():
    result = check_container_runtime(
        {"container_runtime": {"docker_installed": True, "docker_version": "27.0"}}
    )
    assert result.verdict == Verdict.PASS


@pytest.mark.parametrize(
    ("skew", "expected"),
    [(10.0, Verdict.PASS), (90.0, Verdict.WARN), (400.0, Verdict.FAIL)],
)
def test_check_time_skew_thresholds(skew, expected):
    result = check_time(
        {"time": {"ntp_synchronized": True}}, readsb_now=1000.0, local_time=1000.0 + skew
    )
    assert result.verdict == expected


def test_check_time_unknown_without_readsb_now():
    result = check_time({"time": {}}, readsb_now=None, local_time=1000.0)
    assert result.verdict == Verdict.UNKNOWN


def test_check_network_ports_pass_when_free():
    result = check_network_ports(
        {"network_ports": {"listening_ports": [22, 80]}}, app_port=8088, readsb_reachable=True
    )
    assert result.verdict == Verdict.PASS


def test_check_network_ports_fail_when_occupied():
    result = check_network_ports(
        {"network_ports": {"listening_ports": [22, 80, 8088]}}, app_port=8088, readsb_reachable=True
    )
    assert result.verdict == Verdict.FAIL


def test_check_existing_services_pass_when_unchanged():
    before = {"readsb": "active", "tar1090": "active", "fr24feed": "active"}
    after = dict(before)
    result = check_existing_services(before, after)
    assert result.verdict == Verdict.PASS


def test_check_existing_services_fail_when_changed():
    before = {"readsb": "active", "tar1090": "active", "fr24feed": "active"}
    after = {"readsb": "inactive", "tar1090": "active", "fr24feed": "active"}
    result = check_existing_services(before, after)
    assert result.verdict == Verdict.FAIL
    assert "readsb" in result.details["changed"]


# --- aggregation and rendering ----------------------------------------------


def test_build_report_any_fail_wins():
    checks = {
        "a": CheckResult(id="A", name="a", verdict=Verdict.PASS, summary=""),
        "b": CheckResult(id="B", name="b", verdict=Verdict.FAIL, summary=""),
    }
    report = build_report(checks, "host")
    assert report.overall_verdict == Verdict.FAIL
    assert report.ready_for_phase1 is False


def test_build_report_docker_absent_is_warn_or_pass_but_not_ready():
    checks = {
        "container_runtime": check_container_runtime(
            {"container_runtime": {"docker_installed": False}}
        ),
    }
    report = build_report(checks, "host")
    assert report.overall_verdict != Verdict.FAIL
    assert report.ready_for_phase1 is False
    assert report.blocking_decisions == ["container_runtime_choice"]


def test_render_markdown_contains_all_section_headers():
    checks = {"os_cpu": check_os_cpu({"os_cpu": {"arch": "x86_64"}})}
    report = build_report(checks, "host")
    rendered = render_markdown(report)
    for heading in ("A. OS and CPU", "B. Memory and disk", "H. Existing services"):
        assert heading in rendered


def test_to_json_dict_round_trips():
    checks = {"os_cpu": check_os_cpu({"os_cpu": {"arch": "x86_64"}})}
    report = build_report(checks, "host")
    payload = json.loads(json.dumps(to_json_dict(report)))
    assert payload["schema_version"] == 1
    assert "checks" in payload


# --- CLI smoke test ----------------------------------------------------------


def test_main_fixture_mode_writes_reports(tmp_path):
    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"
    exit_code = main(
        [
            "--fixture",
            str(FIXTURES_DIR / "aircraft_sample.json"),
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
        ]
    )
    assert exit_code == 0
    assert json_out.exists()
    assert md_out.exists()
    payload = json.loads(json_out.read_text())
    assert payload["checks"]["readsb_connectivity"]["details"]["mode"] == "fixture"
