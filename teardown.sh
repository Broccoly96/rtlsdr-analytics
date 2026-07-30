#!/usr/bin/env bash
# One-click bring-down for rtlsdr-analytics -- the counterpart to setup.sh.
#
# By default this only stops containers; the database volume (all your
# collected observation history) is kept, so running ./setup.sh again
# later picks up right where you left off. Never touches the host's own
# readsb/tar1090/fr24feed services.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DELETE_VOLUMES=0
SKIP_CONFIRM=0
for arg in "$@"; do
  case "$arg" in
    --volumes|-v)
      DELETE_VOLUMES=1
      ;;
    --yes)
      SKIP_CONFIRM=1
      ;;
    --help|-h)
      cat <<'EOF'
Usage: ./teardown.sh [--volumes] [--yes]

Stops all rtlsdr-analytics containers (docker compose down). The database
volume is kept by default.

  --volumes, -v   Also delete the database volume (PERMANENT: all
                   collected observation history is gone). Prompts for
                   confirmation unless --yes is also given.
  --yes           Skip the --volumes confirmation prompt (scripted use
                   only -- never pass this against data you want to keep).
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

if [[ "$DELETE_VOLUMES" -eq 1 ]]; then
  echo "This stops every container AND permanently deletes the database"
  echo "volume -- all collected observation history is gone, unrecoverable"
  echo "without a backup."
  echo "To back up first (in another terminal): scripts/backup.sh"
  echo
  if [[ "$SKIP_CONFIRM" -ne 1 ]]; then
    read -r -p "Type 'delete' to confirm: " confirm </dev/tty
    if [[ "$confirm" != "delete" ]]; then
      echo "confirmation did not match, aborting. Nothing was stopped or deleted."
      exit 1
    fi
  fi
  docker compose down --volumes
  echo "stopped, and the database volume was deleted."
else
  docker compose down
  echo "stopped. The database volume was kept -- run ./setup.sh to start again."
fi
