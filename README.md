# rtlsdr-analytics

A personal ADS-B history and analytics dashboard that sits on top of an
existing [`readsb`](https://github.com/wiedehopf/readsb) instance. It polls
`readsb`'s `aircraft.json`, stores observation history in PostgreSQL, and
serves a small dashboard with traffic charts, recent tracks, reception
rankings, receiver-performance stats, and per-aircraft revisit history.

**This is not a replacement for [tar1090](https://github.com/wiedehopf/tar1090)
or `fr24feed`.** It runs alongside them, read-only against `readsb`'s JSON
output, and never touches their configuration, process state, or comms
paths. If you want live real-time tracking, tar1090 already does that well
— this project is about what happened *over time*.

Full design rationale, data model, and the session-by-session build log
live in [`PLAN.md`](PLAN.md) (Japanese). `CLAUDE.md` is the condensed
reference for AI coding agents working in this repo.

## Features

- **Dashboard** (`/`) — live ingestion status, currently-received /
  position-acquired counts, a track map with an optional density heatmap,
  a traffic chart (day/week/month granularity, CSV export), and
  hour-of-day / altitude / speed distribution charts, plus
  farthest/closest/recently-observed tables.
- **Receiver performance** (`/static/receiver.html`) — how far you're
  actually receiving, broken down by compass bearing and by altitude band,
  plus a message-rate/position-rate trend over 24h/7d/30d.
- **Daily report** (`/static/daily.html`) — one day's summary (unique
  aircraft, max concurrent, message count, farthest/closest/most-observed)
  with day-over-day and same-weekday-last-week comparisons. Optionally
  posted once a day to a Slack- or Discord-compatible webhook.
- **Aircraft revisit history** (`/static/history.html`) — which aircraft
  come back the most, with a per-aircraft first/last-seen, pass count, and
  callsign history; supports a browser-local (no account, no server write)
  favorites list.
- **Health checks** that actually mean something — `/health/ready` reflects
  real DB connectivity and recent ingestion success, not just "the process
  is running."
- No accounts, no auth, no telemetry. The server itself never calls out
  anywhere. Your browser fetches from the internet only when you ask it
  to: map tiles (always, to render the map — see
  [Configuration](#configuration-reference) to point that at a
  self-hosted style instead), and, only if you click an aircraft's "機体
  情報を見る" link, registration/type from adsbdb.com and a photo from
  Planespotters.net (see [Security & Privacy](#security--privacy)).

## Architecture

```
   readsb (existing, on the host)
          │  aircraft.json over HTTP
          ▼
   adsb-collector ──────► adsb-db (PostgreSQL)
                                │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                   ▼
      adsb-retention     adsb-daily-rollup      adsb-api (FastAPI)
      (prunes old raw    (daily summaries,           │
       observations)      optional webhook)           ▼
                                              Web UI (static HTML/JS,
                                              served by adsb-api)
```

Six Docker Compose services, defined in [`compose.yaml`](compose.yaml):

| Service | Role |
|---|---|
| `adsb-db` | PostgreSQL. Never exposed on a host port — reachable only on the internal Docker network. |
| `adsb-migrate` | One-shot Alembic `upgrade head`. Every other app service waits for this to succeed before starting. |
| `adsb-collector` | Polls `readsb`, normalizes records, writes to Postgres with exponential backoff on failure. |
| `adsb-retention` | Deletes `observations`/`ingestion_status` rows older than `RAW_RETENTION_DAYS`, in small batches. |
| `adsb-daily-rollup` | Once a day, computes the previous day's summary and (optionally) sends the webhook. |
| `adsb-api` | FastAPI app: serves the API and the static UI, on `APP_BIND_HOST:APP_PORT`. |

## Quick Start

```bash
git clone https://github.com/Broccoly96/rtlsdr-analytics.git
cd rtlsdr-analytics
./setup.sh
```

`setup.sh` walks you through the required settings (your receiver's
location and where to reach `readsb`), generates a database password, runs
a read-only environment check, then builds and starts everything. It
prints the dashboard URL when the stack is healthy. Re-running it later
(e.g. after `git pull`) skips the wizard and just rebuilds/restarts.

To bring everything back down: `./teardown.sh` (see
[Stopping](#operations)).

## Prerequisites

- A Linux x86-64 host with Docker Engine + Docker Compose v2
- A `readsb` (or `tar1090`/`dump1090-fa`) instance already running on that
  host or reachable over the LAN, serving `aircraft.json` over HTTP
- Your receiver's latitude/longitude (used for distance calculations only
  — see [privacy notes](#security--privacy))
- A little disk headroom: raw observations are kept 30 days by default
  (`RAW_RETENTION_DAYS`); `scripts/db_status.py` (see [Operations](#operations))
  reports actual growth once you're running so you can tune this

## Installation Guide

`setup.sh` automates everything below — read this section if you want to
understand or customize what it does, or if you're setting up without an
interactive terminal.

1. **Copy the env template and fill it in:**

   ```bash
   cp .env.example .env
   ```

   The one setting most likely to trip you up: **`READSB_AIRCRAFT_URL` must
   use `host.docker.internal`, not `127.0.0.1`.** The collector runs inside
   a container, so `127.0.0.1` from its point of view means the container
   itself, not the host running `readsb`. `compose.yaml` adds the
   `extra_hosts` entry needed for `host.docker.internal` to resolve on
   Docker Engine for Linux. If you're not sure what path `readsb` serves
   `aircraft.json` on, see step 2.

   At minimum, also set `RECEIVER_LAT` and `RECEIVER_LON` — the app fails
   to start without them (see [Configuration](#configuration-reference)).

2. **(Recommended) Run the Phase 0 environment check** — read-only, makes
   no changes, safe to run as a normal user:

   ```bash
   scripts/check_environment.sh
   ```

   This also tries the common `aircraft.json` paths
   (`/tar1090/...`, `/readsb/...`, `/dump1090-fa/...`) against your host if
   `READSB_AIRCRAFT_URL` isn't confirmed reachable yet, and writes
   `reports/environment-report.md` / `.json` with PASS/WARN/FAIL/UNKNOWN
   verdicts. On a FAIL, stop and fix the underlying cause before
   continuing — don't work around it.

3. **Set a real database password.** Generate one and put it in both
   `POSTGRES_PASSWORD` and the credential inside `DATABASE_URL` — they
   must match:

   ```bash
   PW=$(openssl rand -hex 20)
   sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${PW}/" .env
   sed -i "s#^DATABASE_URL=.*#DATABASE_URL=postgresql://adsb:${PW}@adsb-db:5432/adsb#" .env
   ```

4. **Build and start:**

   ```bash
   docker compose build
   docker compose up -d
   ```

   This also runs `adsb-migrate` automatically (it's a dependency of every
   other app service, so a failed migration blocks bring-up instead of
   letting the app run against an outdated schema).

5. **Verify:**

   ```bash
   curl http://127.0.0.1:${APP_PORT:-8088}/health/live
   curl http://127.0.0.1:${APP_PORT:-8088}/health/ready
   ```

   Then open `http://127.0.0.1:${APP_PORT:-8088}/` in a browser.

## Configuration reference

All settings live in `.env` (copied from `.env.example`, never committed —
see `.gitignore`). The app validates every value at startup and refuses to
start with a clear error rather than running misconfigured.

**Required — startup fails without these:**

| Variable | Notes |
|---|---|
| `READSB_AIRCRAFT_URL` | Must be `http://` or `https://`. See the `host.docker.internal` note above. |
| `RECEIVER_LAT` | −90 to 90 |
| `RECEIVER_LON` | −180 to 180 |
| `DATABASE_URL` | `postgresql://user:pass@adsb-db:5432/db`; must agree with `POSTGRES_*` below |

**Optional, with defaults:**

| Variable | Default | Notes |
|---|---|---|
| `DISPLAY_TIMEZONE` | `Asia/Tokyo` | Any IANA zone. All DB timestamps are UTC regardless — this is display-only. |
| `POLL_INTERVAL_SECONDS` | `5` | Collector poll interval. |
| `TRACK_SAMPLE_SECONDS` | `30` | Roughly how often a position is persisted per aircraft (or sooner on a significant move). |
| `RAW_RETENTION_DAYS` | `30` | How long raw `observations` are kept; minute/day aggregates are kept indefinitely. |
| `APP_BIND_HOST` | `127.0.0.1` | **Don't set this to `0.0.0.0`** unless you've deliberately decided to expose the app — there is no login on any endpoint. For remote-but-private access, bind to one specific interface's address (e.g. a Tailscale IP). |
| `APP_PORT` | `8088` | |
| `MAP_STYLE_URL` | OpenFreeMap "positron" | Fetched client-side by the browser only — the server never calls out to this. Override with a MapTiler style (your own key) or a self-hosted style. |
| `MAP_SHOW_RECEIVER_MARKER` | `false` | Whether to plot your receiver's location on the map. |
| `MAP_RECEIVER_MARKER_PRECISION` | `1` | Decimal places shown if the marker is enabled. |
| `NOTIFY_WEBHOOK_ENABLED` | `false` | Enables the daily-summary webhook. Requires `NOTIFY_WEBHOOK_URL` if `true`. |
| `NOTIFY_WEBHOOK_URL` | unset | Slack "Incoming Webhook" URL, or a Discord webhook URL with `/slack` appended (both accept this app's `{"text": "..."}` payload). |

**Also read directly from the environment (not part of app `Settings`):**

| Variable | Default | Used by |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `adsb` / — / `adsb` | The `adsb-db` container itself, and `scripts/backup.sh`. Must match the credentials embedded in `DATABASE_URL`. |
| `BACKUP_DIR` | `backups/` | `scripts/backup.sh`, `scripts/restore_test.sh` |
| `BACKUP_KEEP_GENERATIONS` | `7` | `scripts/backup.sh` — how many dumps to keep |

## How to Use

### The dashboard (`/`)

The main page. A status badge shows whether ingestion is healthy, stale,
erroring, or has no data yet. Four cards show currently-received aircraft,
aircraft with a position, unique aircraft in the last 24h, and time since
the last successful fetch. Below that: a track map (1h/6h/24h, with an
optional density heatmap filterable by altitude band / hour of day / day
of week), a traffic chart with day/week/month zoom and a CSV download
link, distribution charts (by hour of day, altitude, speed), and
farthest/closest/recently-observed tables. Everything refreshes
automatically and pauses while the browser tab is hidden.

### Receiver performance (`/static/receiver.html`)

Answers "how good is my antenna/siting, really?" — a bearing-vs-range
chart (max distance received per compass sector) and an altitude-vs-range
chart, plus a message-count/position-rate trend, over 24h/7d/30d.

### Daily report (`/static/daily.html`)

One calendar day's numbers with comparisons: vs. yesterday and vs. the
same weekday last week. If you enable the webhook
(`NOTIFY_WEBHOOK_ENABLED=true` / `NOTIFY_WEBHOOK_URL=...`), this same
summary is posted once a day (after the previous day's rollup completes,
around 00:10 in `DISPLAY_TIMEZONE`) to Slack or Discord automatically.
Manual invocation for backfilling a specific past day:

```bash
docker compose run --rm adsb-daily-rollup python3 -m app.dailyrollup --day 2026-07-28 --dry-run
```

(drop `--dry-run` to actually write it).

### Aircraft revisit history (`/static/history.html`)

A "most frequently observed" ranking (7/30/90-day windows) with a
favorites star — favorites are stored only in your browser's
`localStorage`, never sent to the server. Click an aircraft (or visit
`?icao=<hex>`) for its first/last-seen, days observed, pass count, and
callsign history.

### API

All endpoints are `GET`-only, unauthenticated (intended for
localhost/LAN use — see [Security & Privacy](#security--privacy)), and
input-bounded with server-side timeouts. Interactive docs at `/docs` once
running.

| Endpoint | Query params | Returns |
|---|---|---|
| `GET /health/live` | — | Process liveness |
| `GET /health/ready` | — | 200 only if DB reachable and a recent ingest succeeded, else 503 |
| `GET /api/status` | — | Current ingestion state and live counts |
| `GET /api/traffic` | `hours` (1–168, default 24) | Zero-filled per-minute traffic buckets |
| `GET /api/traffic.csv` | `hours` | Same data as a CSV download |
| `GET /api/traffic/daily` | `days` (1–365, default 30) | Per-day summaries, ending yesterday |
| `GET /api/traffic/daily-summary` | `day` (YYYY-MM-DD) | One day's summary; today is computed live |
| `GET /api/tracks` | `hours` (1–24, default 6) | Decimated per-aircraft track lines (capped at 100 aircraft / 10k points) |
| `GET /api/rankings` | `hours`, `limit` | Farthest / closest aircraft |
| `GET /api/aircraft/recent` | `hours`, `limit`, `offset` | Recently-seen aircraft |
| `GET /api/aircraft/{icao}/history` | — | One aircraft's revisit history |
| `GET /api/aircraft/frequent` | `days`, `limit` | Most frequently observed aircraft |
| `GET /api/config` | — | Non-secret UI config (map style, timezone, version) |
| `GET /api/receiver/bearing-range` | `hours` | Max reception distance per compass sector |
| `GET /api/receiver/altitude-range` | `hours` | Max reception distance per altitude band |
| `GET /api/receiver/reception` | `hours` | Message-count / position-rate trend |
| `GET /api/distribution/hour-of-day` | `days` | Unique aircraft per hour of day |
| `GET /api/distribution/altitude` | `hours` | Altitude histogram |
| `GET /api/distribution/speed` | `hours` | Ground-speed histogram |
| `GET /api/heatmap` | `hours`, `altitude_band`, `hour_of_day`, `day_of_week` | Position-density grid cells |

## Operations

**Logs:**

```bash
docker compose logs -f adsb-collector
docker compose logs -f adsb-api
docker compose logs -f adsb-daily-rollup
```

**DB status** (read-only — sizes, row counts, growth, projected size, last
ingestion result; never prints a connection string or row-level data):

```bash
docker compose run --rm adsb-api python3 scripts/db_status.py
```

**Retention** — enforced continuously by `adsb-retention`; to preview what
a run would delete without deleting anything:

```bash
docker compose run --rm adsb-retention python3 -m app.retention --dry-run
```

**Backup and restore:**

```bash
scripts/backup.sh          # pg_dump to backups/ (gitignored, chmod 600)
scripts/restore_test.sh    # restores the latest backup into a throwaway
                            # container and sanity-checks row counts —
                            # never touches the live database
```

**Reset the database (dev/testing only — irreversible):**

```bash
docker compose run --rm adsb-api python3 scripts/reset_db.py
```

Truncates every table (schema kept). Requires typing the database name
back to confirm. Deliberately not wired into the API or any UI button —
the API has no auth, so a destructive action must never be one request
away.

**Updating:**

```bash
git pull
./setup.sh          # or: docker compose build && docker compose up -d
```

**Stopping:**

```bash
./teardown.sh                # stops everything, keeps the data volume
./teardown.sh --volumes      # also deletes the database volume (destructive,
                              # confirmation-gated) -- everything collected
                              # is gone unless you ran scripts/backup.sh first
```

Equivalent to `docker compose down` / `docker compose down -v` directly, if
you'd rather skip the wrapper.

## Development

```bash
make install   # pip install -e ".[dev]"
make lint
make fmt
make test
```

Tests that need Docker (the Postgres-container contract tests, Playwright
integration tests) skip rather than fail when Docker isn't available, so a
green `make test` on a Docker-less machine doesn't mean full coverage ran.

## Troubleshooting

- **Dashboard shows "data stopped"**: the collector can't reach
  `READSB_AIRCRAFT_URL`. Check `docker compose logs adsb-collector` and
  that `readsb`/`tar1090` are still running (`systemctl status readsb
  tar1090`) — this app never restarts those services itself.
- **`/health/ready` returns 503**: either the database is unreachable or
  no successful ingest has happened recently. Check `docker compose ps`
  and `docker compose logs adsb-db`.
- **Bring-up seems stuck / `adsb-api` never starts**: check
  `docker compose logs adsb-migrate` first — every app service waits for
  the migration to succeed, by design, so a schema migration failure
  blocks everything rather than letting the app run against a stale
  schema.
- **Daily report / aircraft history pages show all zeros**: these read
  from the daily-rollup tables, which only get populated once
  `adsb-daily-rollup` has completed at least one run (once a day, or
  manually via `--day`/`--dry-run` — see [How to Use](#daily-report-staticdailyhtml)).
  The dashboard's live numbers are unaffected.
- **Map tiles don't load**: the browser (not the server) fetches map tiles
  directly from `MAP_STYLE_URL` (OpenFreeMap by default); check the
  browser's own network connectivity. The traffic chart and rankings work
  independently of the map.
- **After a host reboot, `adsb-api` exits immediately**: if `APP_BIND_HOST`
  is bound to an interface that isn't up yet at boot (e.g. a VPN/Tailscale
  address assigned after Docker starts), the container can fail to bind
  and exit. Recover with `docker compose up -d --force-recreate adsb-api`;
  to fix permanently, either bind to `127.0.0.1`/a static address, or add
  a systemd unit/override that starts Docker Compose after the relevant
  network interface is up.

## Security & Privacy

- **No authentication on any endpoint, by design** — this is meant for
  localhost or a trusted LAN/VPN, not the public internet. Don't set
  `APP_BIND_HOST=0.0.0.0` without deliberately deciding to expose it (and
  putting something in front of it, e.g. a reverse proxy with auth).
- No mutating API routes exist. The one destructive tool
  (`scripts/reset_db.py`) is a manual, confirmation-gated CLI script, never
  reachable over the network.
- Your receiver's coordinates are used server-side for distance
  calculations and are never returned at full precision by the API; the
  optional map marker is rounded (`MAP_RECEIVER_MARKER_PRECISION`) and off
  by default (`MAP_SHOW_RECEIVER_MARKER=false`).
- Clicking an aircraft's "機体情報を見る" (aircraft info) link fetches
  registration/type from `api.adsbdb.com` and a photo from
  `api.planespotters.net` **directly from your browser** — the server is
  never involved and never sees which aircraft you looked up. This is
  strictly opt-in per click; nothing is prefetched, and results aren't
  cached server-side. It's the only outbound call this app makes besides
  map tiles.
- The daily-report's aircraft-type chart is the one exception where the
  *server* calls out: once a day, `adsb-daily-rollup` looks up any
  newly-seen aircraft's type against `api.adsbdb.com` and caches the
  result permanently in its own database — never per page view, never
  re-queried once cached.
- `.env` is gitignored — never commit it. Only `.env.example` (with blank
  lat/lon and a placeholder password) is tracked.
- Backups (`scripts/backup.sh`) are written `chmod 600` into a `chmod 700`
  directory.

## Project status

Both the original Phase 1 MVP (collector, storage, API, dashboard) and a
set of Phase 2 extensions (receiver performance, distributions, heatmap,
daily rollups + webhook, aircraft revisit history) are implemented — see
`PLAN.md` for the full milestone-by-milestone history.

Explicitly out of scope: raw Beast/Mode-S frame storage or a custom
decoder, aircraft/airline metadata enrichment, runway/arrival/departure
inference, go-around/holding detection, ML anomaly detection, user
accounts, multi-receiver support, public hosting, replacing
tar1090/fr24feed, Kubernetes.

## Contributing

`CLAUDE.md` has the condensed operating rules for anyone (human or AI
agent) working in this repo — read it before making changes, especially
the constraints around never touching the host's existing
`readsb`/`tar1090`/`fr24feed` services. `PLAN.md` has the full design
rationale. Run `make lint` and `make test` before opening a PR.

## License

[MIT](LICENSE)
