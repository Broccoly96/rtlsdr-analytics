#!/usr/bin/env bash
# One-click installer/bring-up for rtlsdr-analytics.
#
# Safe to re-run: if .env already exists, the configuration wizard is
# skipped entirely and this just (re)builds and (re)starts the stack --
# useful after `git pull` to pick up new code. Never touches the host's
# own readsb/tar1090/fr24feed services, never uses sudo, and never prints
# or logs secret values (the generated Postgres password is written only
# into .env, which is gitignored).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SKIP_CHECK=0
for arg in "$@"; do
  case "$arg" in
    --skip-check)
      SKIP_CHECK=1
      ;;
    --help|-h)
      cat <<'EOF'
Usage: ./setup.sh [--skip-check]

First-time setup: builds a .env via an interactive wizard, optionally runs
the read-only Phase 0 environment check, then builds and starts the full
Docker Compose stack.

Re-run any time (e.g. after `git pull`): if .env already exists, the
wizard is skipped and this just rebuilds/restarts the stack.

  --skip-check   Skip the Phase 0 read-only environment check
                 (scripts/check_environment.sh) even on first-time setup.
EOF
      exit 0
      ;;
    *)
      echo "unknown argument: $arg (try --help)" >&2
      exit 1
      ;;
  esac
done

if [[ ! -f compose.yaml ]]; then
  echo "compose.yaml not found -- run this script from the repo root." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker was not found on PATH. Install Docker Engine first:" >&2
  echo "  https://docs.docker.com/engine/install/" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "the 'docker compose' (v2) plugin was not found. Install it:" >&2
  echo "  https://docs.docker.com/compose/install/linux/" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "cannot reach the Docker daemon -- is it running, and is this user" >&2
  echo "allowed to talk to it (e.g. a member of the 'docker' group)?" >&2
  exit 1
fi

# --- .env in place: skip the wizard, jump straight to bring-up -------------
if [[ -f .env ]]; then
  echo "found existing .env, skipping configuration wizard (remove .env to reconfigure)"
else
  echo "no .env found -- starting first-time configuration wizard"
  echo

  cp .env.example .env

  # Portable in-place edit of KEY=value lines in .env. Values are escaped
  # for sed's special characters (backslash, the '|' delimiter used here so
  # URLs containing '/' don't need escaping, and '&' which sed treats as
  # "whole match" in a replacement).
  env_set() {
    local key="$1" value="$2" escaped
    escaped=$(printf '%s' "$value" | sed -e 's/[\\|&]/\\&/g')
    sed -i "s|^${key}=.*|${key}=${escaped}|" .env
  }

  prompt_default() {
    local message="$1" default="$2" input
    read -r -p "$message [$default]: " input </dev/tty
    printf '%s' "${input:-$default}"
  }

  prompt_required() {
    local message="$1" pattern="$2" input
    while true; do
      read -r -p "$message: " input </dev/tty
      if [[ -n "$input" && "$input" =~ $pattern ]]; then
        printf '%s' "$input"
        return
      fi
      echo "  that doesn't look right, try again." >&2
    done
  }

  echo "-- readsb connection --"
  echo "The collector runs inside a container and reaches the host's readsb"
  echo "via host.docker.internal (not 127.0.0.1 -- see .env.example for why)."
  readsb_url=$(prompt_default "aircraft.json URL" \
    "http://host.docker.internal/tar1090/data/aircraft.json")
  env_set READSB_AIRCRAFT_URL "$readsb_url"
  echo

  echo "-- receiver location (used for distance calculations, not displayed publicly) --"
  receiver_lat=$(prompt_required "Receiver latitude (decimal degrees)" \
    '^-?[0-9]+(\.[0-9]+)?$')
  env_set RECEIVER_LAT "$receiver_lat"
  receiver_lon=$(prompt_required "Receiver longitude (decimal degrees)" \
    '^-?[0-9]+(\.[0-9]+)?$')
  env_set RECEIVER_LON "$receiver_lon"
  echo

  echo "-- display --"
  display_tz=$(prompt_default "Display timezone (IANA name)" "Asia/Tokyo")
  env_set DISPLAY_TIMEZONE "$display_tz"
  echo

  echo "-- network --"
  app_bind_host=$(prompt_default "Bind address (127.0.0.1 = this machine only)" "127.0.0.1")
  if [[ "$app_bind_host" == "0.0.0.0" ]]; then
    echo "  WARNING: 0.0.0.0 exposes the dashboard, unauthenticated, on every"
    echo "  network interface (including any public one). This app has no"
    echo "  login. For remote-but-private access, bind to a specific"
    echo "  interface's own address instead (e.g. a Tailscale IP)."
    confirm=$(prompt_default "  type 'yes' to really bind to 0.0.0.0" "no")
    if [[ "$confirm" != "yes" ]]; then
      app_bind_host="127.0.0.1"
      echo "  keeping 127.0.0.1 instead."
    fi
  fi
  env_set APP_BIND_HOST "$app_bind_host"
  app_port=$(prompt_default "Port" "8088")
  env_set APP_PORT "$app_port"
  echo

  echo "-- optional: daily-summary webhook (Slack/Discord) --"
  webhook_choice=$(prompt_default "Send a daily summary to a webhook? (y/N)" "N")
  if [[ "$webhook_choice" =~ ^[Yy] ]]; then
    webhook_url=$(prompt_required "Webhook URL" '^https?://')
    env_set NOTIFY_WEBHOOK_ENABLED "true"
    env_set NOTIFY_WEBHOOK_URL "$webhook_url"
  fi
  echo

  # Generate a random Postgres password and keep POSTGRES_PASSWORD and
  # DATABASE_URL in sync (they must agree -- .env.example warns about this).
  if command -v openssl >/dev/null 2>&1; then
    pg_password=$(openssl rand -hex 20)
  else
    pg_password=$(head -c 40 /dev/urandom | od -An -tx1 | tr -d ' \n')
  fi
  pg_user=$(sed -n 's/^POSTGRES_USER=//p' .env)
  pg_db=$(sed -n 's/^POSTGRES_DB=//p' .env)
  env_set POSTGRES_PASSWORD "$pg_password"
  env_set DATABASE_URL "postgresql://${pg_user}:${pg_password}@adsb-db:5432/${pg_db}"

  echo "wrote .env (never committed to git -- see .gitignore)"
  echo
fi

# --- Phase 0 read-only environment check ------------------------------------
if [[ "$SKIP_CHECK" -eq 0 ]]; then
  echo "running read-only environment check (scripts/check_environment.sh) ..."
  if ! scripts/check_environment.sh; then
    echo
    echo "environment check reported a FAIL -- stopping here." >&2
    echo "see reports/environment-report.md for the cause and a minimal fix" >&2
    echo "before re-running ./setup.sh (or pass --skip-check to bypass this)." >&2
    exit 1
  fi
  echo
fi

# --- build and start ---------------------------------------------------------
echo "building images ..."
# Bakes the current commit into the version footer shown in every page's
# header (see CLAUDE.md's Versioning section) -- falls back to "unknown"
# harmlessly if this isn't a git checkout.
export GIT_REVISION
GIT_REVISION="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
docker compose build

echo "starting the stack ..."
docker compose up -d

# shellcheck disable=SC1091
set -a; source .env; set +a
base_url="http://${APP_BIND_HOST}:${APP_PORT}"

echo "waiting for ${base_url}/health/live ..."
live_ok=0
for _ in $(seq 1 30); do
  if curl -fsS "${base_url}/health/live" >/dev/null 2>&1; then
    live_ok=1
    break
  fi
  printf '.'
  sleep 2
done
echo

if [[ "$live_ok" -ne 1 ]]; then
  echo "adsb-api never became live. Recent logs:" >&2
  docker compose logs --tail=50 adsb-api adsb-migrate >&2
  exit 1
fi

echo "waiting for ${base_url}/health/ready (DB + recent ingest) ..."
ready_ok=0
for _ in $(seq 1 30); do
  if curl -fsS "${base_url}/health/ready" >/dev/null 2>&1; then
    ready_ok=1
    break
  fi
  printf '.'
  sleep 2
done
echo

if [[ "$ready_ok" -ne 1 ]]; then
  echo "adsb-api is live but not ready yet (DB or collector still catching up)." >&2
  echo "this can be normal in the first ~30s. Check with:" >&2
  echo "  docker compose logs -f adsb-collector adsb-db" >&2
  echo "  curl ${base_url}/health/ready" >&2
  exit 1
fi

echo "checking the raw Beast stream from inside adsb-api ..."
if ! docker compose exec -T adsb-api python3 -c \
  "import socket; from app.config import Settings; c=Settings(); s=socket.create_connection((c.readsb_beast_host, c.readsb_beast_port), 5); s.settimeout(5); assert s.recv(1)"; then
  cat >&2 <<'EOF'
WARNING: the dashboard is ready, but the raw-data page cannot reach readsb.
The HTTP aircraft feed and Beast TCP feed use separate host ports, so one can
work while a host firewall drops the other. Allow the configured Beast port only from this
Compose network's subnet to its host gateway; see README.md Troubleshooting.
EOF
fi

cat <<EOF

rtlsdr-analytics is up.

  Dashboard:           ${base_url}/
  Receiver performance: ${base_url}/static/receiver.html
  Daily report:         ${base_url}/static/daily.html
  Aircraft history:     ${base_url}/static/history.html

Logs:    docker compose logs -f adsb-collector adsb-api
Backup:  scripts/backup.sh
Docs:    README.md
EOF
