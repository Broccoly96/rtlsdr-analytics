# ADS-B Analytics

A personal web app that polls a `readsb` instance's `aircraft.json`, stores
observation history in PostgreSQL, and serves a dashboard: current aircraft
count, 24h traffic chart, recent tracks map, and farthest/closest rankings.

This is **not** a replacement for tar1090 or fr24feed — it runs alongside
them, read-only against `readsb`'s JSON output, and does not touch their
configuration or service state. Full requirements and design rationale live
in `PLAN.md`; `CLAUDE.md` is the condensed guide for AI coding agents working
in this repo.

## Prerequisites

- Docker Engine + Docker Compose v2
- A reachable `readsb` `aircraft.json` HTTP endpoint (same host or LAN)
- The receiver's latitude/longitude

## First-time setup

```bash
cp .env.example .env
# edit .env: set RECEIVER_LAT / RECEIVER_LON and confirm READSB_AIRCRAFT_URL
docker compose build
docker compose up -d
```

## Health checks

- Liveness: `curl http://127.0.0.1:${APP_PORT}/health/live`
- Readiness (DB + recent ingest check): `curl http://127.0.0.1:${APP_PORT}/health/ready`
- Dashboard: open `http://127.0.0.1:${APP_PORT}/` in a browser

## Logs

```bash
docker compose logs -f adsb-collector
docker compose logs -f adsb-api
docker compose logs -f adsb-db
```

## Backup and restore

```bash
scripts/backup.sh          # writes a pg_dump to backups/
scripts/restore_test.sh    # restores the latest backup into a throwaway
                            # container and sanity-checks row counts
```

## Updating

```bash
git pull
docker compose build
docker compose up -d
```

## Stopping

```bash
docker compose down          # stops containers, keeps the data volume
docker compose down -v       # also deletes the database volume (destructive)
```

## Troubleshooting

- **Dashboard shows "data stopped"**: the collector can't reach
  `READSB_AIRCRAFT_URL`. Check `docker compose logs adsb-collector` and that
  `readsb`/`tar1090` are still running (`systemctl status readsb tar1090`) —
  this app never restarts those services itself.
- **`/health/ready` returns 503**: either the database is unreachable or no
  successful ingest has happened recently. Check `docker compose ps` and
  `docker compose logs adsb-db`.
- **Map tiles don't load**: the browser (not the server) fetches map tiles
  directly from a public OSM tile server; check the browser's own network
  connectivity. The traffic chart and rankings work independently of the map.

## Development

```bash
make install   # pip install -e ".[dev]"
make lint
make fmt
make test
```

## Local Phase 0 environment check

Before deploying to a new host, run:

```bash
scripts/check_environment.sh
python3 scripts/probe_readsb.py
```

These are read-only and produce `reports/environment-report.md` /
`reports/environment-report.json` (gitignored — see
`reports/environment-report.example.md` for the expected shape).
