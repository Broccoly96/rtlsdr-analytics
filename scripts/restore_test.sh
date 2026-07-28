#!/usr/bin/env bash
# Restores a backup (most recent by default, or a path given as $1) into a
# disposable, host-only PostgreSQL container -- never into the running
# adsb-db -- and sanity-checks the result with row counts and one
# representative query (PLAN.md SS8 E-3). pg_dump --format=custom captures
# schema and data together, so no separate `alembic upgrade` step is needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

BACKUP_DIR="${BACKUP_DIR:-$REPO_ROOT/backups}"

if [ -n "${1:-}" ]; then
  dump_path="$1"
else
  dump_path="$(ls -1t "$BACKUP_DIR"/adsb-db-*.dump 2>/dev/null | head -n1 || true)"
fi

if [ -z "$dump_path" ] || [ ! -f "$dump_path" ]; then
  echo "no backup found to restore (looked in $BACKUP_DIR; pass a path explicitly to restore a specific file)" >&2
  exit 1
fi

container_name="adsb-restore-test-$$"
port=15433

cleanup() {
  docker rm -f "$container_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "restoring $dump_path into a throwaway container ($container_name) ..."
docker run --rm -d --name "$container_name" \
  -p "127.0.0.1:${port}:5432" \
  -e POSTGRES_USER=restoretest \
  -e POSTGRES_PASSWORD=restoretest \
  -e POSTGRES_DB=restoretest \
  postgres:16 >/dev/null

echo "waiting for throwaway DB to accept connections ..."
ready=0
for _ in $(seq 1 30); do
  if docker exec "$container_name" pg_isready -U restoretest >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "throwaway DB never became ready" >&2
  exit 1
fi

docker exec -i "$container_name" pg_restore -U restoretest -d restoretest --no-owner --no-privileges < "$dump_path"

echo
echo "=== row counts after restore ==="
docker exec "$container_name" psql -U restoretest -d restoretest -t -c "
  SELECT 'aircraft', count(*) FROM aircraft
  UNION ALL SELECT 'observations', count(*) FROM observations
  UNION ALL SELECT 'traffic_minute', count(*) FROM traffic_minute
  UNION ALL SELECT 'ingestion_status', count(*) FROM ingestion_status;
"

echo "=== representative query: most recent observation ==="
docker exec "$container_name" psql -U restoretest -d restoretest -t -c "
  SELECT icao, callsign, observed_at FROM observations ORDER BY observed_at DESC LIMIT 1;
"

echo
echo "restore test complete: $dump_path"
