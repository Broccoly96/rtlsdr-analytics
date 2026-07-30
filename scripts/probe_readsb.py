"""Phase 0 environment probe: readsb connectivity, receiver-location
detection, and aggregation/rendering of checks A-H into
reports/environment-report.{md,json}.

Standard-library only, deliberately: this must be runnable before the
project's own dependencies (httpx, etc.) are installed, since Phase 0 exists
to check whether the environment is even ready for those dependencies.

Checks A/B/C/F/G are fed in from a JSON "shell facts" file produced by
scripts/check_environment.sh (which gathers OS/memory/disk/Docker/time/port
facts via read-only commands). This module owns checks D (readsb
connectivity), E (receiver location), and H (existing-service impact)
directly, plus the verdict thresholds and report rendering for all eight.

Never emit full aircraft-level data (positions, callsigns, hex codes) or
full-precision receiver coordinates into the generated report -- only
aggregate counts/percentages and rounded coordinates.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

DEFAULT_CANDIDATE_URLS: tuple[str, ...] = (
    "http://127.0.0.1/tar1090/data/aircraft.json",
    "http://127.0.0.1/readsb/data/aircraft.json",
    "http://127.0.0.1/dump1090-fa/data/aircraft.json",
)

AIRCRAFT_FIELDS_TO_TALLY: tuple[str, ...] = (
    "hex",
    "flight",
    "lat",
    "lon",
    "alt_baro",
    "alt_geom",
    "gs",
    "track",
    "baro_rate",
    "geom_rate",
    "seen",
    "seen_pos",
    "rssi",
)

DEFAULT_RECEIVER_JSON_PATH = Path("/run/readsb/receiver.json")
DEFAULT_READSB_CONF_PATH = Path("/etc/default/readsb")
DEFAULT_EXISTING_SERVICES: tuple[str, ...] = ("readsb", "tar1090", "fr24feed")

MEMORY_PASS_GIB = 1.0
MEMORY_RECOMMENDED_GIB = 2.0
DISK_PASS_GB = 10.0
DISK_RECOMMENDED_GB = 30.0
TIME_SKEW_WARN_SECONDS = 60.0
TIME_SKEW_FAIL_SECONDS = 300.0


class Verdict(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


_SEVERITY = {Verdict.PASS: 0, Verdict.UNKNOWN: 1, Verdict.WARN: 2, Verdict.FAIL: 3}


def _worse(a: Verdict, b: Verdict) -> Verdict:
    return a if _SEVERITY[a] >= _SEVERITY[b] else b


class InvalidPayloadError(ValueError):
    pass


@dataclass
class CheckResult:
    id: str
    name: str
    verdict: Verdict
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "verdict": self.verdict.value,
            "summary": self.summary,
            "details": self.details,
            "notes": self.notes,
        }


@dataclass
class FetchResult:
    url: str
    status_code: int | None
    elapsed_ms: float | None
    error: str | None
    payload: dict[str, Any] | None
    fetched_at: float


@dataclass
class FieldTally:
    aircraft_count: int
    unique_icao_count: int
    field_presence_pct: dict[str, float]


@dataclass
class LivenessResult:
    verdict: Verdict
    now_advanced: bool | None
    messages_advanced: bool | None
    notes: list[str]


@dataclass
class ReceiverLocation:
    lat: float
    lon: float
    source: str

    def rounded(self, ndigits: int = 1) -> tuple[float, float]:
        return (round(self.lat, ndigits), round(self.lon, ndigits))


@dataclass
class EnvironmentReport:
    generated_at: str
    target_host: str
    overall_verdict: Verdict
    ready_for_phase1: bool
    blocking_decisions: list[str]
    checks: dict[str, CheckResult]


# --- D. readsb connectivity -------------------------------------------------


def fetch_aircraft_json(url: str, timeout: float = 5.0) -> FetchResult:
    """Read-only GET of a readsb aircraft.json endpoint. Never raises."""
    start = time.monotonic()
    fetched_at = time.time()
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "adsb-analytics-phase0-probe/1"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status_code = response.status
            body = response.read()
        elapsed_ms = (time.monotonic() - start) * 1000
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            return FetchResult(
                url, status_code, elapsed_ms, f"invalid JSON: {exc}", None, fetched_at
            )
        if not isinstance(payload, dict):
            return FetchResult(
                url, status_code, elapsed_ms, "payload is not a JSON object", None, fetched_at
            )
        return FetchResult(url, status_code, elapsed_ms, None, payload, fetched_at)
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return FetchResult(url, exc.code, elapsed_ms, f"HTTP error: {exc}", None, fetched_at)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return FetchResult(url, None, elapsed_ms, f"connection error: {exc}", None, fetched_at)


def parse_and_tally(payload: dict[str, Any]) -> FieldTally:
    """Shallow presence/shape check -- NOT semantic validation.

    This only asks "is the feed shaped correctly and alive" (Phase 0's job).
    Full semantic validation (range checks, `alt_baro: "ground"` handling,
    future-timestamp rejection) happens later against the same fixtures, in
    the Task 4 collector's normalizer.
    """
    if not isinstance(payload, dict) or "aircraft" not in payload:
        raise InvalidPayloadError("payload missing 'aircraft' key")
    aircraft = payload["aircraft"]
    if not isinstance(aircraft, list):
        raise InvalidPayloadError("'aircraft' is not a list")

    count = len(aircraft)
    icaos: set[Any] = set()
    present_counts = dict.fromkeys(AIRCRAFT_FIELDS_TO_TALLY, 0)

    for entry in aircraft:
        if not isinstance(entry, dict):
            continue
        hex_value = entry.get("hex")
        if hex_value is not None:
            icaos.add(hex_value)
        for field_name in AIRCRAFT_FIELDS_TO_TALLY:
            if entry.get(field_name) is not None:
                present_counts[field_name] += 1

    if count == 0:
        presence_pct = {name: 0.0 for name in AIRCRAFT_FIELDS_TO_TALLY}
    else:
        presence_pct = {
            name: round(present_counts[name] / count * 100, 1) for name in AIRCRAFT_FIELDS_TO_TALLY
        }

    return FieldTally(
        aircraft_count=count,
        unique_icao_count=len(icaos),
        field_presence_pct=presence_pct,
    )


def evaluate_liveness(fetch1: FetchResult, fetch2: FetchResult | None) -> LivenessResult:
    if fetch1.error is not None or fetch1.payload is None:
        return LivenessResult(
            Verdict.UNKNOWN, None, None, ["first fetch failed; cannot confirm liveness"]
        )
    if fetch2 is None or fetch2.error is not None or fetch2.payload is None:
        return LivenessResult(
            Verdict.UNKNOWN, None, None, ["second fetch failed; cannot confirm liveness"]
        )

    now1, now2 = fetch1.payload.get("now"), fetch2.payload.get("now")
    messages1, messages2 = fetch1.payload.get("messages"), fetch2.payload.get("messages")

    now_advanced = isinstance(now1, int | float) and isinstance(now2, int | float) and now2 > now1
    messages_advanced = (
        isinstance(messages1, int | float)
        and isinstance(messages2, int | float)
        and messages2 > messages1
    )

    if now_advanced or messages_advanced:
        return LivenessResult(Verdict.PASS, now_advanced, messages_advanced, [])
    return LivenessResult(
        Verdict.WARN,
        now_advanced,
        messages_advanced,
        ["neither `now` nor `messages` advanced between fetches"],
    )


def check_readsb_connectivity(
    candidate_urls: Sequence[str],
    primary_url: str | None,
    wait_seconds: float = 12.0,
    timeout: float = 5.0,
    try_all_candidates: bool = False,
) -> CheckResult:
    if primary_url and not try_all_candidates:
        urls_to_try = [primary_url]
    elif primary_url:
        urls_to_try = [primary_url, *[u for u in candidate_urls if u != primary_url]]
    else:
        urls_to_try = list(candidate_urls)

    fetch1 = None
    used_url = None
    last_error = None
    tally1 = None
    for url in urls_to_try:
        result = fetch_aircraft_json(url, timeout=timeout)
        if result.error is None and result.payload is not None:
            try:
                tally1 = parse_and_tally(result.payload)
            except InvalidPayloadError as exc:
                last_error = f"invalid payload shape: {exc}"
                continue
            fetch1 = result
            used_url = url
            break
        last_error = result.error

    if fetch1 is None or tally1 is None or used_url is None:
        return CheckResult(
            id="D",
            name="readsb connectivity",
            verdict=Verdict.FAIL,
            summary="could not reach a valid readsb endpoint",
            details={"urls_tried": urls_to_try, "last_error": last_error},
            notes=["each candidate URL tried once; never retried aggressively against readsb"],
        )

    time.sleep(wait_seconds)
    fetch2 = fetch_aircraft_json(used_url, timeout=timeout)
    liveness = evaluate_liveness(fetch1, fetch2)

    readsb_now = None
    if fetch2.payload:
        readsb_now = fetch2.payload.get("now")
    if readsb_now is None and fetch1.payload:
        readsb_now = fetch1.payload.get("now")

    top_level_keys_present = sorted(
        k for k in ("now", "messages", "aircraft") if k in fetch1.payload
    )

    return CheckResult(
        id="D",
        name="readsb connectivity",
        verdict=liveness.verdict,
        summary=f"reached readsb at {used_url}",
        details={
            "url_used": used_url,
            "http_status": fetch1.status_code,
            "latency_ms": round(fetch1.elapsed_ms, 1) if fetch1.elapsed_ms is not None else None,
            "json_valid": True,
            "top_level_keys_present": top_level_keys_present,
            "aircraft_count": tally1.aircraft_count,
            "unique_icao_count": tally1.unique_icao_count,
            "field_presence_pct": tally1.field_presence_pct,
            "wait_seconds": wait_seconds,
            "now_advanced": liveness.now_advanced,
            "messages_advanced": liveness.messages_advanced,
            "readsb_now": readsb_now,
        },
        notes=liveness.notes,
    )


# --- E. Receiver location ----------------------------------------------------


def _is_valid_coordinate(lat: float, lon: float) -> bool:
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def detect_receiver_location(
    env: Mapping[str, str],
    receiver_json_path: Path = DEFAULT_RECEIVER_JSON_PATH,
    readsb_conf_path: Path = DEFAULT_READSB_CONF_PATH,
) -> ReceiverLocation | None:
    lat_str, lon_str = env.get("RECEIVER_LAT"), env.get("RECEIVER_LON")
    if lat_str and lon_str:
        try:
            lat, lon = float(lat_str), float(lon_str)
            if _is_valid_coordinate(lat, lon):
                return ReceiverLocation(lat, lon, "env")
        except ValueError:
            pass

    if receiver_json_path.is_file():
        try:
            data = json.loads(receiver_json_path.read_text())
            lat, lon = float(data["lat"]), float(data["lon"])
            if _is_valid_coordinate(lat, lon):
                return ReceiverLocation(lat, lon, "readsb_receiver_json")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            pass

    if readsb_conf_path.is_file():
        try:
            text = readsb_conf_path.read_text()
            lat_match = re.search(r"--lat[= ]([-\d.]+)", text)
            lon_match = re.search(r"--lon[= ]([-\d.]+)", text)
            if lat_match and lon_match:
                lat, lon = float(lat_match.group(1)), float(lon_match.group(1))
                if _is_valid_coordinate(lat, lon):
                    return ReceiverLocation(lat, lon, "readsb_conf_file")
        except OSError:
            pass

    return None


def check_receiver_location(
    env: Mapping[str, str],
    receiver_json_path: Path = DEFAULT_RECEIVER_JSON_PATH,
    readsb_conf_path: Path = DEFAULT_READSB_CONF_PATH,
) -> CheckResult:
    location = detect_receiver_location(env, receiver_json_path, readsb_conf_path)
    if location is None:
        return CheckResult(
            id="E",
            name="receiver location",
            verdict=Verdict.UNKNOWN,
            summary="could not determine receiver location",
            details={"source": None},
            notes=["set RECEIVER_LAT/RECEIVER_LON in .env -- required before Phase 1"],
        )
    lat_rounded, lon_rounded = location.rounded(1)
    return CheckResult(
        id="E",
        name="receiver location",
        verdict=Verdict.PASS,
        summary=f"detected via {location.source}",
        details={"source": location.source, "lat_rounded": lat_rounded, "lon_rounded": lon_rounded},
        notes=["full-precision coordinates intentionally not written to this report"],
    )


# --- H. Existing-service impact ---------------------------------------------


def capture_service_states(services: Sequence[str] = DEFAULT_EXISTING_SERVICES) -> dict[str, str]:
    states: dict[str, str] = {}
    for name in services:
        try:
            result = subprocess.run(  # noqa: S603, S607
                ["systemctl", "is-active", name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            states[name] = result.stdout.strip() or result.stderr.strip() or "unknown"
        except (OSError, subprocess.SubprocessError):
            states[name] = "unknown"
    return states


def check_existing_services(before: Mapping[str, str], after: Mapping[str, str]) -> CheckResult:
    changed = {
        name: [before.get(name), after.get(name)]
        for name in before
        if before.get(name) != after.get(name)
    }
    if changed:
        return CheckResult(
            id="H",
            name="existing services",
            verdict=Verdict.FAIL,
            summary="an existing service's state changed during the check",
            details={
                "before": dict(before),
                "after": dict(after),
                "unchanged": False,
                "changed": changed,
            },
            notes=["this should never happen from a read-only check; investigate immediately"],
        )
    inactive = {name: state for name, state in after.items() if state != "active"}
    verdict = Verdict.PASS if not inactive else Verdict.WARN
    return CheckResult(
        id="H",
        name="existing services",
        verdict=verdict,
        summary="unchanged before/after" if not inactive else "some services are not active",
        details={
            "before": dict(before),
            "after": dict(after),
            "unchanged": True,
            "inactive": inactive,
        },
        notes=[],
    )


# --- A/B/C/F/G: fed from shell-gathered facts -------------------------------


def check_os_cpu(facts: Mapping[str, Any]) -> CheckResult:
    if "os_cpu" not in facts:
        return CheckResult(
            id="A",
            name="OS and CPU",
            verdict=Verdict.UNKNOWN,
            summary="not run (no shell facts provided)",
            details={},
            notes=["run via scripts/check_environment.sh to populate this check"],
        )
    info = dict(facts["os_cpu"])
    arch = info.get("arch")
    if arch != "x86_64":
        return CheckResult(
            id="A",
            name="OS and CPU",
            verdict=Verdict.FAIL,
            summary=f"unsupported architecture: {arch!r}",
            details=info,
            notes=["PLAN.md requires x86-64"],
        )
    return CheckResult(
        id="A",
        name="OS and CPU",
        verdict=Verdict.PASS,
        summary=(
            f"{info.get('distro_name') or 'unknown distro'} on x86_64, "
            f"{info.get('cpu_cores', '?')} cores"
        ),
        details=info,
        notes=[],
    )


def check_memory_disk(facts: Mapping[str, Any]) -> CheckResult:
    if "memory_disk" not in facts:
        return CheckResult(
            id="B",
            name="memory and disk",
            verdict=Verdict.UNKNOWN,
            summary="not run (no shell facts provided)",
            details={},
            notes=["run via scripts/check_environment.sh to populate this check"],
        )
    info = dict(facts["memory_disk"])
    mem_gib = (info.get("available_memory_bytes") or 0) / (1024**3)
    disk_gb = (info.get("free_disk_bytes") or 0) / (1000**3)

    notes = []
    if mem_gib < MEMORY_PASS_GIB or disk_gb < DISK_PASS_GB:
        verdict = Verdict.FAIL
        notes.append(
            "below minimum thresholds -- do not change anything; consider shorter retention instead"
        )
    elif mem_gib < MEMORY_RECOMMENDED_GIB or disk_gb < DISK_RECOMMENDED_GB:
        verdict = Verdict.WARN
        notes.append(
            "below recommended thresholds; acceptable, but consider a more conservative config"
        )
    else:
        verdict = Verdict.PASS

    return CheckResult(
        id="B",
        name="memory and disk",
        verdict=verdict,
        summary=f"{mem_gib:.1f} GiB available memory, {disk_gb:.1f} GB free disk",
        details={
            "available_memory_gib": round(mem_gib, 2),
            "free_disk_gb": round(disk_gb, 2),
            "disk_fs_type": info.get("disk_fs_type"),
            "free_inode_pct": info.get("free_inode_pct"),
            "pass_thresholds": {"memory_gib": MEMORY_PASS_GIB, "disk_gb": DISK_PASS_GB},
            "recommended_thresholds": {
                "memory_gib": MEMORY_RECOMMENDED_GIB,
                "disk_gb": DISK_RECOMMENDED_GB,
            },
        },
        notes=notes,
    )


def check_container_runtime(facts: Mapping[str, Any]) -> CheckResult:
    info = dict(facts.get("container_runtime", {}))
    if not info.get("docker_installed"):
        return CheckResult(
            id="C",
            name="container runtime",
            verdict=Verdict.UNKNOWN,
            summary="Docker is not installed",
            details={
                "docker_installed": False,
                "decision_required": True,
                "options": [
                    {
                        "id": "install_docker",
                        "description": (
                            "Install Docker Engine + Compose v2 (needs sudo -- present "
                            "target/impact for approval before Task 3)"
                        ),
                    },
                    {
                        "id": "systemd_venv_postgres",
                        "description": (
                            "systemd units + Python venv + host PostgreSQL (needs sudo for package "
                            "install -- present target/impact for approval before Task 3)"
                        ),
                    },
                ],
            },
            notes=["PLAN.md treats Docker-absent as a decision to be made, not a FAIL"],
        )
    return CheckResult(
        id="C",
        name="container runtime",
        verdict=Verdict.PASS,
        summary=f"{info.get('docker_version') or 'Docker (version unknown)'} available",
        details=info,
        notes=[],
    )


def check_time(
    facts: Mapping[str, Any], readsb_now: float | None, local_time: float
) -> CheckResult:
    info = dict(facts.get("time", {}))
    notes: list[str] = []
    skew = abs(local_time - readsb_now) if readsb_now is not None else None

    if skew is None:
        verdict = Verdict.UNKNOWN
        notes.append("no readsb `now` value available to compute clock skew")
    elif skew > TIME_SKEW_FAIL_SECONDS:
        verdict = Verdict.FAIL
        notes.append(f"clock skew {skew:.1f}s exceeds FAIL threshold ({TIME_SKEW_FAIL_SECONDS}s)")
    elif skew > TIME_SKEW_WARN_SECONDS:
        verdict = Verdict.WARN
        notes.append(f"clock skew {skew:.1f}s exceeds WARN threshold ({TIME_SKEW_WARN_SECONDS}s)")
    else:
        verdict = Verdict.PASS

    if info.get("ntp_synchronized") is False:
        verdict = _worse(verdict, Verdict.WARN)
        notes.append("NTP is not synchronized")

    return CheckResult(
        id="F",
        name="time",
        verdict=verdict,
        summary=f"clock skew vs readsb: {skew:.1f}s" if skew is not None else "clock skew unknown",
        details={
            "timezone": info.get("timezone"),
            "ntp_synchronized": info.get("ntp_synchronized"),
            "clock_skew_seconds": skew,
        },
        notes=notes,
    )


# Matches this app's own adsb-api container regardless of Compose project
# name (which follows the clone directory name and so varies): Compose v2's
# default naming is "<project>-adsb-api-<n>", v1-style/COMPOSE_COMPATIBILITY
# uses "<project>_adsb-api_<n>". A `container_name:` override isn't used in
# compose.yaml, so this pattern is expected to match reliably.
_ADSB_API_CONTAINER_PATTERN = re.compile(r"(?:^|[-_])adsb-api(?:[-_]|$)")


def check_network_ports(
    facts: Mapping[str, Any], app_port: int, readsb_reachable: bool
) -> CheckResult:
    if "network_ports" not in facts:
        return CheckResult(
            id="G",
            name="network and ports",
            verdict=Verdict.UNKNOWN,
            summary="not run (no shell facts provided)",
            details={"app_port": app_port},
            notes=["run via scripts/check_environment.sh to populate this check"],
        )
    info = dict(facts["network_ports"])
    listening = set(info.get("listening_ports", []))
    port_free = app_port not in listening

    owner_names = [n for n in info.get("port_owner_container_names", []) if n]
    own_deployment_owns_port = any(
        _ADSB_API_CONTAINER_PATTERN.search(name) for name in owner_names
    )

    notes = []
    if not port_free and own_deployment_owns_port:
        # Re-running the check against an already-running deployment of this
        # same app: the port is "in use" by our own adsb-api container, which
        # `docker compose up -d` will simply recreate in place. That's not
        # the "some unrelated process/service is squatting on this port"
        # conflict this check exists to catch, so it isn't a FAIL.
        verdict = Verdict.PASS if readsb_reachable else Verdict.WARN
        notes.append(
            f"port {app_port} is in use by this project's own adsb-api "
            f"container ({', '.join(owner_names)}) -- expected on a redeploy, "
            "not a conflict"
        )
        if not readsb_reachable:
            notes.append(
                "readsb was not reachable during this check; network conclusions are partial"
            )
    elif not port_free:
        verdict = Verdict.FAIL
        notes.append(f"port {app_port} is already in use; choose a different APP_PORT")
    elif not readsb_reachable:
        verdict = Verdict.WARN
        notes.append("readsb was not reachable during this check; network conclusions are partial")
    else:
        verdict = Verdict.PASS

    return CheckResult(
        id="G",
        name="network and ports",
        verdict=verdict,
        summary=f"app port {app_port} {'free' if port_free else 'in use'}",
        details={
            "app_port": app_port,
            "app_port_free": port_free,
            "listening_ports": sorted(listening),
            "port_owned_by_own_deployment": own_deployment_owns_port,
        },
        notes=notes,
    )


# --- Report assembly ---------------------------------------------------------

_SUMMARY_LABELS: dict[str, str] = {
    "os_cpu": "OS / CPU (x86-64)",
    "memory_disk": "Memory / disk",
    "container_runtime": "Container runtime (Docker)",
    "readsb_connectivity": "readsb connectivity",
    "receiver_location": "Receiver location",
    "time": "Time sync",
    "network_ports": "Network / ports",
    "existing_services": "Existing services unaffected",
}

_DETAIL_ORDER: tuple[tuple[str, str], ...] = (
    ("os_cpu", "A. OS and CPU"),
    ("memory_disk", "B. Memory and disk"),
    ("container_runtime", "C. Container runtime"),
    ("readsb_connectivity", "D. readsb connectivity"),
    ("receiver_location", "E. Receiver location"),
    ("time", "F. Time"),
    ("network_ports", "G. Network and ports"),
    ("existing_services", "H. Existing services"),
)


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_report(checks: dict[str, CheckResult], target_host: str) -> EnvironmentReport:
    overall = Verdict.PASS
    for check in checks.values():
        overall = _worse(overall, check.verdict)

    blocking_decisions: list[str] = []
    container = checks.get("container_runtime")
    if container is not None and container.details.get("decision_required"):
        blocking_decisions.append("container_runtime_choice")

    receiver = checks.get("receiver_location")
    if receiver is not None and receiver.verdict == Verdict.UNKNOWN:
        blocking_decisions.append("receiver_location_input_required")

    ready_for_phase1 = overall != Verdict.FAIL and not blocking_decisions

    return EnvironmentReport(
        generated_at=_utc_now_iso(),
        target_host=target_host,
        overall_verdict=overall,
        ready_for_phase1=ready_for_phase1,
        blocking_decisions=blocking_decisions,
        checks=checks,
    )


def to_json_dict(report: EnvironmentReport) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": report.generated_at,
        "target_host": report.target_host,
        "overall_verdict": report.overall_verdict.value,
        "ready_for_phase1": report.ready_for_phase1,
        "blocking_decisions": report.blocking_decisions,
        "checks": {name: check.to_dict() for name, check in report.checks.items()},
    }


def render_markdown(report: EnvironmentReport) -> str:
    lines = [
        "# Environment Report",
        "",
        f"Generated at: {report.generated_at}",
        f"Target host: {report.target_host}",
        f"Overall verdict: {report.overall_verdict.value}",
        f"Ready for Phase 1: {report.ready_for_phase1}",
    ]
    if report.blocking_decisions:
        lines.append(f"Blocking decisions: {', '.join(report.blocking_decisions)}")

    lines += ["", "## Summary", "", "| Check | Result |", "|---|---|"]
    for key, label in _SUMMARY_LABELS.items():
        check = report.checks.get(key)
        verdict = check.verdict.value if check else "UNKNOWN"
        lines.append(f"| {label} | {verdict} |")

    lines += ["", "## Details", ""]
    for key, heading in _DETAIL_ORDER:
        check = report.checks.get(key)
        lines.append(f"### {heading}")
        if check is None:
            lines += ["- not run", ""]
            continue
        lines.append(f"- Verdict: {check.verdict.value}")
        lines.append(f"- Summary: {check.summary}")
        for detail_key, detail_value in check.details.items():
            lines.append(f"- {detail_key}: {detail_value}")
        for note in check.notes:
            lines.append(f"- Note: {note}")
        lines.append("")

    return "\n".join(lines)


# --- CLI ----------------------------------------------------------------


def _load_shell_facts(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _fixture_mode_check(fixture_path: Path) -> CheckResult:
    try:
        payload = json.loads(fixture_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return CheckResult(
            id="D",
            name="readsb connectivity",
            verdict=Verdict.FAIL,
            summary="fixture could not be read as JSON",
            details={"mode": "fixture", "fixture_path": str(fixture_path), "error": str(exc)},
            notes=[],
        )
    try:
        tally = parse_and_tally(payload)
    except InvalidPayloadError as exc:
        return CheckResult(
            id="D",
            name="readsb connectivity",
            verdict=Verdict.FAIL,
            summary="fixture payload shape is invalid",
            details={"mode": "fixture", "fixture_path": str(fixture_path), "error": str(exc)},
            notes=[],
        )
    readsb_now = payload.get("now") if isinstance(payload, dict) else None
    return CheckResult(
        id="D",
        name="readsb connectivity",
        verdict=Verdict.UNKNOWN,
        summary=f"fixture mode: read {fixture_path}",
        details={
            "mode": "fixture",
            "fixture_path": str(fixture_path),
            "aircraft_count": tally.aircraft_count,
            "unique_icao_count": tally.unique_icao_count,
            "field_presence_pct": tally.field_presence_pct,
            "readsb_now": readsb_now,
        },
        notes=["offline fixture mode: liveness against a live endpoint was not checked"],
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 0 environment/readsb probe")
    parser.add_argument("--shell-facts", type=Path, default=None)
    parser.add_argument("--url", default=None)
    parser.add_argument("--try-all-candidates", action="store_true")
    parser.add_argument("--wait-seconds", type=float, default=12.0)
    parser.add_argument("--app-port", type=int, default=8088)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="offline mode: read this JSON file instead of HTTP",
    )
    parser.add_argument("--json-out", type=Path, default=Path("reports/environment-report.json"))
    parser.add_argument("--md-out", type=Path, default=Path("reports/environment-report.md"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    facts = _load_shell_facts(args.shell_facts)
    env = os.environ

    services_before = capture_service_states()

    if args.fixture is not None:
        readsb_check = _fixture_mode_check(args.fixture)
    else:
        primary_url = args.url or env.get("READSB_AIRCRAFT_URL")
        readsb_check = check_readsb_connectivity(
            DEFAULT_CANDIDATE_URLS,
            primary_url,
            wait_seconds=args.wait_seconds,
            try_all_candidates=args.try_all_candidates,
        )

    services_after = capture_service_states()

    # Fixture timestamps are arbitrary/stale (they exist to test parsing, not
    # liveness), so they must never be compared against the real wall clock.
    readsb_now = None if args.fixture is not None else readsb_check.details.get("readsb_now")
    readsb_reachable = readsb_check.verdict != Verdict.FAIL

    checks: dict[str, CheckResult] = {
        "os_cpu": check_os_cpu(facts),
        "memory_disk": check_memory_disk(facts),
        "container_runtime": check_container_runtime(facts),
        "readsb_connectivity": readsb_check,
        "receiver_location": check_receiver_location(env),
        "time": check_time(facts, readsb_now, time.time()),
        "network_ports": check_network_ports(facts, args.app_port, readsb_reachable),
        "existing_services": check_existing_services(services_before, services_after),
    }

    target_host = facts.get("os_cpu", {}).get("hostname") or socket.gethostname()
    report = build_report(checks, target_host)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(to_json_dict(report), indent=2) + "\n")
    args.md_out.write_text(render_markdown(report) + "\n")

    print(f"Overall verdict: {report.overall_verdict.value}")
    print(f"Ready for Phase 1: {report.ready_for_phase1}")
    if report.blocking_decisions:
        print(f"Blocking decisions: {', '.join(report.blocking_decisions)}")
    print(f"Reports written to {args.json_out} and {args.md_out}")

    return 1 if report.overall_verdict == Verdict.FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
