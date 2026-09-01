#!/usr/bin/env bash
# One-time production hardening for installations that still use the original
# `changeme` database password. The database itself is not restarted. Existing
# client containers are recreated only after a migration connection succeeds
# with the new credential.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f .env ]; then
  echo "error: $REPO_ROOT/.env does not exist" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a; source .env; set +a

: "${POSTGRES_USER:?POSTGRES_USER must be set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"
: "${POSTGRES_DB:?POSTGRES_DB must be set}"
: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${APP_BIND_HOST:?APP_BIND_HOST must be set}"
: "${APP_PORT:?APP_PORT must be set}"

if [ "$POSTGRES_PASSWORD" != "changeme" ] || [[ "$DATABASE_URL" != *":changeme@"* ]]; then
  echo "refusing: this one-time script only rotates the original default credential" >&2
  exit 1
fi

if [[ ! "$POSTGRES_USER" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
  echo "error: unsupported POSTGRES_USER format" >&2
  exit 1
fi

if [[ ! "$POSTGRES_DB" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
  echo "error: unsupported POSTGRES_DB format" >&2
  exit 1
fi

for command_name in docker openssl curl; do
  command -v "$command_name" >/dev/null || {
    echo "error: required command not found: $command_name" >&2
    exit 1
  }
done

docker compose exec -T adsb-db \
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -Atqc 'SELECT 1' >/dev/null

new_password="$(openssl rand -hex 32)"
new_database_url="postgresql://${POSTGRES_USER}:${new_password}@adsb-db:5432/${POSTGRES_DB}"
old_database_url="$DATABASE_URL"
env_backup="$(mktemp)"
env_replacement="$(mktemp "$REPO_ROOT/.env.rotate.XXXXXX")"
chmod 0600 "$env_backup" "$env_replacement"
cp .env "$env_backup"

db_changed=false
env_changed=false
complete=false

restore_clients() {
  docker compose run --rm --no-deps adsb-migrate >/dev/null
  docker compose up -d --no-deps --force-recreate \
    adsb-collector adsb-retention adsb-daily-rollup adsb-type-lookup adsb-api >/dev/null
}

cleanup() {
  status=$?
  if [ "$complete" != true ]; then
    echo "rotation failed; restoring the previous credential" >&2
    if [ "$db_changed" = true ]; then
      printf '%s\n' "ALTER ROLE \"$POSTGRES_USER\" WITH PASSWORD 'changeme';" \
        | docker compose exec -T adsb-db \
          psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null || true
    fi
    if [ "$env_changed" = true ]; then
      cp "$env_backup" .env
      chmod 0600 .env
      export POSTGRES_PASSWORD=changeme
      export DATABASE_URL="$old_database_url"
      restore_clients || true
    fi
  fi
  rm -f "$env_backup" "$env_replacement"
  unset new_password new_database_url
  exit "$status"
}
trap cleanup EXIT

printf '%s\n' "ALTER ROLE \"$POSTGRES_USER\" WITH PASSWORD '$new_password';" \
  | docker compose exec -T adsb-db \
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null
db_changed=true

password_lines=0
url_lines=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    POSTGRES_PASSWORD=*)
      printf 'POSTGRES_PASSWORD=%s\n' "$new_password" >>"$env_replacement"
      password_lines=$((password_lines + 1))
      ;;
    DATABASE_URL=*)
      printf 'DATABASE_URL=%s\n' "$new_database_url" >>"$env_replacement"
      url_lines=$((url_lines + 1))
      ;;
    *)
      printf '%s\n' "$line" >>"$env_replacement"
      ;;
  esac
done <.env

if [ "$password_lines" -ne 1 ] || [ "$url_lines" -ne 1 ]; then
  echo "error: expected exactly one POSTGRES_PASSWORD and DATABASE_URL line" >&2
  exit 1
fi

mv "$env_replacement" .env
chmod 0600 .env
env_changed=true
export POSTGRES_PASSWORD="$new_password"
export DATABASE_URL="$new_database_url"

# Prove the new credential works before replacing any long-running client.
docker compose run --rm --no-deps adsb-migrate >/dev/null
docker compose up -d --no-deps --force-recreate \
  adsb-collector adsb-retention adsb-daily-rollup adsb-type-lookup adsb-api >/dev/null

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18088/health/ready >/dev/null \
    && curl -fsS "http://${APP_BIND_HOST}:${APP_PORT}/health/ready" >/dev/null; then
    complete=true
    echo "database credential rotation: OK"
    exit 0
  fi
  sleep 2
done

echo "error: API readiness did not recover within 60 seconds" >&2
exit 1
