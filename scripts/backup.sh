#!/usr/bin/env bash
# Logical (pg_dump) backup of adsb-db, run via `docker compose exec` since
# adsb-db never publishes a port to the host (PLAN.md SS8 E-3). Writes into
# BACKUP_DIR (default: backups/, gitignored) as a single custom-format dump
# named with a UTC timestamp, keeps only the most recent BACKUP_KEEP_
# GENERATIONS files, and never leaves a partial file behind on failure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

BACKUP_DIR="${BACKUP_DIR:-$REPO_ROOT/backups}"
BACKUP_KEEP_GENERATIONS="${BACKUP_KEEP_GENERATIONS:-7}"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi

: "${POSTGRES_USER:?POSTGRES_USER must be set (in .env or environment)}"
: "${POSTGRES_DB:?POSTGRES_DB must be set (in .env or environment)}"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
final_path="$BACKUP_DIR/adsb-db-${timestamp}.dump"
tmp_path="${final_path}.tmp"

cleanup() {
  rm -f "$tmp_path"
}
trap cleanup EXIT

echo "backing up ${POSTGRES_DB} to ${final_path} ..."
docker compose exec -T adsb-db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "$tmp_path"

chmod 600 "$tmp_path"
mv "$tmp_path" "$final_path"
trap - EXIT

echo "backup complete: $final_path ($(du -h "$final_path" | cut -f1))"

# Prune old generations, keeping only the most recent BACKUP_KEEP_GENERATIONS.
mapfile -t existing < <(ls -1t "$BACKUP_DIR"/adsb-db-*.dump 2>/dev/null)
if [ "${#existing[@]}" -gt "$BACKUP_KEEP_GENERATIONS" ]; then
  for old in "${existing[@]:$BACKUP_KEEP_GENERATIONS}"; do
    echo "pruning old backup: $old"
    rm -f "$old"
  done
fi
