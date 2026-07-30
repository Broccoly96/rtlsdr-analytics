#!/usr/bin/env bash
# Phase 0 environment check.
#
# Read-only, non-root, makes no file/package/service-config changes. Gathers
# raw facts for checks A (OS/CPU), B (memory/disk), C (container runtime),
# F (time), and G (network/ports) via plain read-only commands, then hands
# off to probe_readsb.py, which performs checks D (readsb connectivity),
# E (receiver location), and H (existing-service impact) and renders
# reports/environment-report.{md,json}.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORTS_DIR="$REPO_ROOT/reports"
RAW_FACTS_PATH="$REPORTS_DIR/environment-report.raw-facts.json"

mkdir -p "$REPORTS_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required but was not found on PATH" >&2
    exit 1
fi

if [[ "$(id -u)" -eq 0 ]]; then
    echo "WARNING: running as root; Phase 0 is designed to run as a normal, non-root user." >&2
fi

DEPLOY_PATH="$REPO_ROOT" RAW_FACTS_PATH="$RAW_FACTS_PATH" python3 <<'PYEOF'
"""Read-only fact-gathering for Phase 0 checks A, B, C, F, G.

Kept as an inline script (rather than a separate .py module) so this shell
script's only dependency is python3 itself, and so scripts/probe_readsb.py
stays focused on checks D/E/H plus report rendering.
"""
import json
import os
import re
import shutil
import subprocess


def _run(cmd, timeout=5):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "", str(exc)


def _os_cpu():
    _, arch, _ = _run(["uname", "-m"])
    _, kernel, _ = _run(["uname", "-r"])
    _, hostname, _ = _run(["hostname"])
    distro_name = distro_version = ""
    try:
        with open("/etc/os-release") as fh:
            for line in fh:
                if line.startswith("NAME="):
                    distro_name = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("VERSION_ID="):
                    distro_version = line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return {
        "arch": arch,
        "distro_name": distro_name,
        "distro_version": distro_version,
        "kernel": kernel,
        "has_systemd": shutil.which("systemctl") is not None,
        "hostname": hostname,
        "cpu_cores": os.cpu_count() or 0,
    }


def _memory_disk():
    available_kb = 0
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    available_kb = int(line.split()[1])
                    break
    except OSError:
        pass

    deploy_path = os.environ.get("DEPLOY_PATH", ".")
    usage = shutil.disk_usage(deploy_path)

    fs_type = ""
    _, mount_out, _ = _run(["df", "--output=fstype", deploy_path])
    mount_lines = mount_out.splitlines()
    if len(mount_lines) >= 2:
        fs_type = mount_lines[1].strip()

    free_inode_pct = None
    _, inode_out, _ = _run(["df", "--output=ipcent", deploy_path])
    inode_lines = inode_out.splitlines()
    if len(inode_lines) >= 2:
        match = re.search(r"(\d+)", inode_lines[1])
        if match:
            free_inode_pct = 100 - int(match.group(1))

    return {
        "available_memory_bytes": available_kb * 1024,
        "free_disk_bytes": usage.free,
        "disk_fs_type": fs_type,
        "free_inode_pct": free_inode_pct,
    }


def _container_runtime():
    if not shutil.which("docker"):
        return {
            "docker_installed": False,
            "docker_version": None,
            "compose_version": None,
            "user_can_run_docker": False,
            "docker_root_free_bytes": None,
            "existing_container_names": [],
            "existing_network_names": [],
        }

    _, docker_version, _ = _run(["docker", "--version"])
    _, compose_version, _ = _run(["docker", "compose", "version"])
    info_code, info_out, _ = _run(["docker", "info", "--format", "{{.DockerRootDir}}"])
    user_can_run_docker = info_code == 0

    docker_root_free_bytes = None
    if user_can_run_docker and info_out:
        try:
            docker_root_free_bytes = shutil.disk_usage(info_out).free
        except OSError:
            pass

    existing_container_names = []
    existing_network_names = []
    if user_can_run_docker:
        _, names_out, _ = _run(["docker", "ps", "-a", "--format", "{{.Names}}"])
        existing_container_names = [n for n in names_out.splitlines() if n]
        _, net_out, _ = _run(["docker", "network", "ls", "--format", "{{.Name}}"])
        existing_network_names = [n for n in net_out.splitlines() if n]

    return {
        "docker_installed": True,
        "docker_version": docker_version or None,
        "compose_version": compose_version or None,
        "user_can_run_docker": user_can_run_docker,
        "docker_root_free_bytes": docker_root_free_bytes,
        "existing_container_names": existing_container_names,
        "existing_network_names": existing_network_names,
    }


def _time_info():
    if shutil.which("timedatectl"):
        _, ntp_raw, _ = _run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
        _, tz, _ = _run(["timedatectl", "show", "-p", "Timezone", "--value"])
        ntp_synchronized = {"yes": True, "no": False}.get(ntp_raw)
    else:
        ntp_synchronized = None
        tz = ""
        try:
            with open("/etc/timezone") as fh:
                tz = fh.read().strip()
        except OSError:
            pass
    return {"ntp_synchronized": ntp_synchronized, "timezone": tz}


def _network_ports():
    listening_ports = set()
    _, ss_out, _ = _run(["ss", "-ltn"])
    for line in ss_out.splitlines()[1:]:
        columns = line.split()
        if len(columns) < 4:
            continue
        match = re.search(r":(\d+)$", columns[3])
        if match:
            listening_ports.add(int(match.group(1)))

    # Who (if anyone) is publishing APP_PORT, so probe_readsb.py can tell
    # "this app's own already-running adsb-api container" apart from a real
    # conflict with an unrelated process.
    app_port = os.environ.get("APP_PORT", "8088")
    port_owner_container_names = []
    if shutil.which("docker"):
        _, owners_out, _ = _run(
            ["docker", "ps", "--filter", f"publish={app_port}", "--format", "{{.Names}}"]
        )
        port_owner_container_names = [n for n in owners_out.splitlines() if n]

    return {
        "listening_ports": sorted(listening_ports),
        "port_owner_container_names": port_owner_container_names,
    }


facts = {
    "os_cpu": _os_cpu(),
    "memory_disk": _memory_disk(),
    "container_runtime": _container_runtime(),
    "time": _time_info(),
    "network_ports": _network_ports(),
}

with open(os.environ["RAW_FACTS_PATH"], "w") as fh:
    json.dump(facts, fh, indent=2)
    fh.write("\n")
PYEOF

PROBE_ARGS=(
    --shell-facts "$RAW_FACTS_PATH"
    --app-port "${APP_PORT:-8088}"
    --wait-seconds "${PHASE0_WAIT_SECONDS:-12}"
    --json-out "$REPORTS_DIR/environment-report.json"
    --md-out "$REPORTS_DIR/environment-report.md"
)
if [[ -n "${READSB_AIRCRAFT_URL:-}" ]]; then
    PROBE_ARGS+=(--url "$READSB_AIRCRAFT_URL")
fi

set +e
python3 "$SCRIPT_DIR/probe_readsb.py" "${PROBE_ARGS[@]}"
PROBE_EXIT=$?
set -e

echo ""
echo "Reports written to $REPORTS_DIR/environment-report.md and $REPORTS_DIR/environment-report.json"

if [[ -f "$REPORTS_DIR/environment-report.json" ]]; then
    REPORT_JSON_PATH="$REPORTS_DIR/environment-report.json" python3 <<'PYEOF'
import json
import os

with open(os.environ["REPORT_JSON_PATH"]) as fh:
    report = json.load(fh)

if report.get("blocking_decisions"):
    print("Decision required before Task 3:", ", ".join(report["blocking_decisions"]))
    print("See reports/environment-report.md for options. Needs explicit approval before any sudo/system change.")
PYEOF
fi

exit "$PROBE_EXIT"
