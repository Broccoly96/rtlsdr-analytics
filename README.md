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
  position-acquired counts, a track map with an optional density heatmap
  (also available full-screen at `/static/fullmap.html`), a traffic chart
  (day/week/month granularity, CSV export), and hour-of-day / altitude /
  speed distribution charts, plus farthest/closest/recently-observed
  tables.
- **Aircraft detail sidebar** — click any aircraft's callsign anywhere in
  the app (dashboard, daily report, history) for a tar1090-style detail
  panel: registration/type/photo, this app's own last-known position/
  speed/distance/RSSI, and a live feed of squawk, NAC/SIL/NIC accuracy,
  FMS-selected altitude/heading, wind, and mach straight from readsb (see
  [Security & Privacy](#security--privacy)).
- **Receiver performance** (`/static/receiver.html`) — how far you're
  actually receiving, broken down by compass bearing and by altitude band,
  a distance-vs-signal-strength (RSSI) heatmap, an interactive 3D
  "reception hemisphere" (bearing/elevation/distance, drag to rotate),
  plus a message-rate/position-rate trend over 24h/7d/30d.
- **Daily report** (`/static/daily.html`) — one day's summary (unique
  aircraft, max concurrent, message count, farthest/closest/most-observed)
  with day-over-day and same-weekday-last-week comparisons, plus a top-10
  aircraft-type chart. Optionally posted once a day to a Slack- or
  Discord-compatible webhook.
- **Aircraft revisit history** (`/static/history.html`) — which aircraft
  come back the most, with a per-aircraft first/last-seen, pass count, and
  callsign history; supports a browser-local (no account, no server write)
  favorites list.
- **Raw data** (`/static/rawdata.html`) — a live, ephemeral view of
  readsb's raw Beast-format stream with a simple decode (downlink format,
  ICAO24, ADS-B message-type category), for learning the frame structure.
  Nothing shown here is stored anywhere.
- **3D flight globe** (`/static/globe.html`) — every currently-live aircraft
  shown at once in a real 3D scene (satellite imagery ground, CesiumJS) as
  a 3D aircraft model, color-tinted by altitude band and oriented by
  heading/roll (and an approximated pitch), drag to orbit. Every aircraft
  draws its own historical + live-extending track (opacity configurable in
  Settings, default 50%). Shift+click one aircraft to isolate it; hover
  for a callsign/altitude/speed tooltip; a checkbox picker filters which
  aircraft are shown; an optional camera-follow mode locks onto whichever
  aircraft is isolated.
- **Health checks** that actually mean something — `/health/ready` reflects
  real DB connectivity and recent ingestion success, not just "the process
  is running."
- No accounts, no auth, no telemetry. Your browser fetches from the
  internet only when you ask it to: map tiles (always, to render the map
  — see [Configuration](#configuration-reference) to point that at a
  self-hosted style instead), and, only if you click an aircraft's "機体
  情報を見る" link, registration/type from adsbdb.com (the photo comes
  from this app's own server instead — see below). The server itself
  only ever talks to your own `readsb` instance, `api.adsbdb.com` (once a
  day per newly-seen aircraft, plus proxying the photo lookup on click),
  and `api.planespotters.net` (proxying the photo lookup on click) — see
  [Security & Privacy](#security--privacy) for the exact scope of each.

## Architecture

```
   readsb (existing, on the host)
          │  aircraft.json over HTTP
          ▼
   adsb-collector ──────► adsb-db (PostgreSQL)
                                │
        ┌───────────────┬──────┼──────────────┬──────────────────┐
        ▼                ▼      ▼              ▼                   ▼
 adsb-retention  adsb-daily-rollup  adsb-type-lookup      adsb-api (FastAPI)
 (prunes old raw  (daily summaries,  (aircraft type/reg.        │
  observations)    optional webhook)  cache, every ~15min)       ▼
                                                          Web UI (static HTML/JS,
                                                          served by adsb-api)
```

Seven Docker Compose services, defined in [`compose.yaml`](compose.yaml):

| Service | Role |
|---|---|
| `adsb-db` | PostgreSQL. Never exposed on a host port — reachable only on the internal Docker network. |
| `adsb-migrate` | One-shot Alembic `upgrade head`. Every other app service waits for this to succeed before starting. |
| `adsb-collector` | Polls `readsb`, normalizes records, writes to Postgres with exponential backoff on failure. |
| `adsb-retention` | Deletes `observations`/`ingestion_status` rows older than `RAW_RETENTION_DAYS`, in small batches. |
| `adsb-daily-rollup` | Once a day, computes the previous day's summary and (optionally) sends the webhook. |
| `adsb-type-lookup` | Every ~15 minutes, caches type/registration info for any newly-seen aircraft against `api.adsbdb.com`. |
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
| `READSB_BEAST_HOST` | `READSB_AIRCRAFT_URL`'s hostname | Only needed if readsb's Beast-format output (used by `/static/rawdata.html`) is served from a different host. |
| `READSB_BEAST_PORT` | `30005` | readsb's standard Beast-out port. |

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
of week — also available full-screen at `/static/fullmap.html`), a
traffic chart with day/week/month zoom and a CSV download link,
distribution charts (by hour of day, altitude, speed), and
farthest/closest/recently-observed tables. Click any aircraft's callsign
to open its detail sidebar (see
[Aircraft detail sidebar](#aircraft-detail-sidebar) below and
[Security & Privacy](#security--privacy)). Everything refreshes
automatically (every 5s for status/rankings, 30s for the map/traffic) and
pauses while the browser tab is hidden.

### Aircraft detail sidebar

Click any aircraft's callsign anywhere in the app (dashboard, daily
report, history) to open a persistent left sidebar, styled after
tar1090's own info panel:

- **Registration / type / photo** — registration, ICAO type code, and
  manufacturer from adsbdb.com; a photo with photographer credit from
  Planespotters.net (proxied through this app's own server — see
  [Security & Privacy](#security--privacy) for why).
- **自局データ (this app's own data)** — this receiver's last-known
  altitude, ground speed, track, vertical rate, distance, bearing, and
  RSSI for that aircraft, straight from this app's own database.
- **Live data** — squawk, message count, last-position age, MLAT/TIS-B
  flags, barometric/geometric altitude, ground/air speed, mach, track/
  magnetic heading, roll, climb rate, FMS-selected altitude/heading, QNH,
  NIC/NACp/NACv/SIL accuracy indicators, and wind/OAT/TAT where the
  aircraft broadcasts them — streamed live from readsb while the sidebar
  is open (not everything is available for every aircraft; unavailable
  fields show `--`, same as tar1090).

### Receiver performance (`/static/receiver.html`)

Answers "how good is my antenna/siting, really?" — a bearing-vs-range
chart (max distance received per compass sector), an altitude-vs-range
chart, a distance-vs-RSSI heatmap (how signal strength falls off with
range), a message-count/position-rate trend, and a 3D "reception
hemisphere": every (bearing, elevation) direction's max reception
distance plotted as a point around the receiver at the center — drag to
rotate, color shows distance. Built with
[`echarts-gl`](https://github.com/ecomfe/echarts-gl) (BSD-3-Clause,
vendored the same way as `echarts`/`maplibre-gl` — no CDN). All over
24h/7d/30d.

### Daily report (`/static/daily.html`)

One calendar day's numbers with comparisons: vs. yesterday and vs. the
same weekday last week, plus a "top 10 aircraft type" chart. If you
enable the webhook (`NOTIFY_WEBHOOK_ENABLED=true` /
`NOTIFY_WEBHOOK_URL=...`), the summary (not the type chart) is posted
once a day (after the previous day's rollup completes, around 00:10 in
`DISPLAY_TIMEZONE`) to Slack or Discord automatically.

The aircraft-type chart reads from a small self-populating cache
(`aircraft_type_cache`): every ~15 minutes, `adsb-type-lookup` looks up
any aircraft it hasn't seen before against `api.adsbdb.com` and caches
the result permanently (a type/registration essentially never changes).
A brand-new aircraft typically shows up in the chart within a lookup
cycle or two, not the next calendar day.

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

### Raw data (`/static/rawdata.html`)

A live table of readsb's raw Beast-format frames as they arrive, decoded
just enough to be readable — downlink format (DF), ICAO24 address,
capability (CA), and, for ADS-B extended squitters (DF17/18), the message
category (identification / position / velocity / etc.). This is
intentionally a *simple* decode for learning the frame structure, not a
replacement for readsb's own (correct, complete) decoding — no
CPR position or velocity math happens here. Nothing is stored: closing
the tab loses the history, and the server never writes any of it to the
database. Pause to read, or clear the table, with the buttons at the top;
it reconnects automatically if the connection drops.

### 3D flight globe (`/static/globe.html`)

By default, every currently-live aircraft is shown at once as a 3D
aircraft model (color-tinted by altitude band, same bands/colors as the
2D map) over satellite imagery (ArcGIS World Imagery), streamed from a
single shared `WS /ws/aircraft-positions` broadcast connection (one
server-side readsb poll, fanned out to every open tab — see
[Security & Privacy](#security--privacy)). Each model is oriented by
heading (compass track) and roll/bank angle when readsb reports it
(often absent — equipage-dependent); pitch has no equivalent readsb
field and is approximated from vertical rate and ground speed, so treat
it as a visual cue, not real flight dynamics. Every aircraft draws its
own historical track (last several hours, cyan) plus a live-extending
track (yellow) picking up exactly where the historical one left off, at
an opacity you can change on the [Settings](#settings-staticsettingshtml)
page (default 50%):

- **Click** an aircraft to open the same shared aircraft detail sidebar
  every other page uses.
- **Shift+click** an aircraft to isolate it: every other aircraft (model
  and track) is hidden and the camera flies to it. Shift+click it again,
  or use the "全機体表示に戻す" button, to return to the full view.
- **Hover** an aircraft for a callsign/altitude/speed tooltip.
- **機体選択** opens a checkbox picker to show/hide specific aircraft
  (defaults to all shown); **一覧更新** refreshes it against recently-seen
  aircraft.
- **カメラ自動追従** locks the camera onto whichever aircraft is currently
  isolated, following it as it moves (Cesium's built-in entity tracking —
  turns off automatically if you manually pan/zoom).

Drag to orbit, scroll to zoom, click the home icon to reset the view.
Unlike the receiver-performance page's 3D reception-hemisphere chart
(which is `echarts-gl`, an aggregate view of reception range), this is
[CesiumJS](https://github.com/CesiumGS/cesium) — built for exactly this
"real aircraft, real 3D scene" use case. Nothing here is persisted.

The aircraft model (`app/static/models/aircraft.glb`) is Cesium's own
`Cesium_Air.glb` sample model from the
[CesiumGS/cesium](https://github.com/CesiumGS/cesium) repository
(`Apps/SampleData/models/CesiumAir/`), covered by the same
Apache License 2.0 as CesiumJS itself, which this app already vendors —
one generic model for every aircraft, not per-type.

### Settings (`/static/settings.html`)

Distance unit (kilometers / nautical miles) and altitude unit (feet /
meters), applied everywhere a distance or altitude is displayed
(dashboard rankings, daily report, aircraft detail sidebar, receiver
performance charts, map popups). Also: the 3D globe's track-line opacity
(default 50%). Pure client-side `localStorage`, same zero-backend
precedent as [aircraft revisit history](#aircraft-revisit-history-statichistoryhtml)'s
favorites — nothing is sent to the server, and already-open tabs need a
reload to pick up a change. Language selection was considered but
deferred (would require i18n-keying every string across every page).

### API

All HTTP endpoints are `GET`-only, unauthenticated (intended for
localhost/LAN use — see [Security & Privacy](#security--privacy)), and
input-bounded with server-side timeouts. Interactive docs at `/docs` once
running. There are also two WebSocket endpoints (not in `/docs`, since
OpenAPI doesn't describe WebSocket routes): `WS /ws/rawdata` (backing the
[raw data](#raw-data-staticrawdatahtml) page) and
`WS /ws/aircraft/{icao}` (backing the
[aircraft detail sidebar](#aircraft-detail-sidebar) and the 3D flight
globe — live tar1090-parity fields for one aircraft, polled from readsb
independently at the collector's own cadence, never persisted).

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
| `GET /api/aircraft/{icao}/history` | — | One aircraft's revisit history (includes this app's own last-known position/speed/RSSI) |
| `GET /api/aircraft/{icao}/positions` | `hours` (1–720, default 6) | One aircraft's own position history (gap-segmented, unlike `/api/tracks`'s all-aircraft view) |
| `GET /api/aircraft/{icao}/photo` | — | Server-side proxy to Planespotters.net (see Security & Privacy) |
| `GET /api/aircraft/frequent` | `days`, `limit` | Most frequently observed aircraft |
| `GET /api/config` | — | Non-secret UI config (map style, timezone, version) |
| `GET /api/receiver/bearing-range` | `hours` | Max reception distance per compass sector |
| `GET /api/receiver/altitude-range` | `hours` | Max reception distance per altitude band |
| `GET /api/receiver/reception` | `hours` | Message-count / position-rate trend |
| `GET /api/receiver/rssi-by-distance` | `hours` | Reception-strength (RSSI) vs. distance heatmap cells |
| `GET /api/receiver/bearing-elevation-range` | `hours` | Max reception distance per (bearing, elevation) cell, for the 3D chart |
| `GET /api/distribution/hour-of-day` | `days` | Unique aircraft per hour of day |
| `GET /api/distribution/altitude` | `hours` | Altitude histogram |
| `GET /api/distribution/speed` | `hours` | Ground-speed histogram |
| `GET /api/distribution/aircraft-type` | `day`, `limit` | Top aircraft types for a day (from `aircraft_type_cache`) |
| `GET /api/heatmap` | `hours`, `altitude_band`, `hour_of_day`, `day_of_week` | Position-density grid cells |

## Operations

**Logs:**

```bash
docker compose logs -f adsb-collector
docker compose logs -f adsb-api
docker compose logs -f adsb-daily-rollup
docker compose logs -f adsb-type-lookup
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
- **Raw data page shows a connection error**: `readsb`'s Beast-format
  output (default port `30005`) either isn't enabled or isn't reachable
  at `READSB_BEAST_HOST`/`READSB_BEAST_PORT`. This is a separate port
  from `READSB_AIRCRAFT_URL` (HTTP, for `aircraft.json`) — confirm it's
  actually listening on the host (`ss -ltn | grep 30005`) before assuming
  it's a container-networking issue.
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
- `/static/receiver.html`'s Content-Security-Policy adds `'unsafe-eval'`
  to `script-src` — every other page stays without it. `echarts-gl`'s
  internal shader/expression compiler needs it for the 3D reception
  chart (confirmed by reproducing and fixing the exact failure). This app
  never uses `eval()`/`Function()` itself and never renders API/user data
  as HTML (always `textContent`), so the realistic added risk is narrow —
  worth knowing if you're auditing this page specifically.
- `/static/globe.html`'s CSP similarly adds `'unsafe-eval'` (CesiumJS's
  own script eagerly compiles WebAssembly for terrain/imagery decoding;
  without it, Cesium's own top-level script throws mid-execution and
  never finishes loading at all) and `blob:` to `script-src` (Cesium
  bootstraps its web workers via a small in-memory blob: script) — again,
  only this one page, confirmed by reproducing and fixing the exact
  failure rather than added speculatively.
- `/static/globe.html` fetches satellite imagery (ArcGIS World Imagery,
  attribution shown on-page) continuously while it's open — not just on
  click, the same posture as the dashboard's map tiles, just a different
  provider and only on this one page.
- Your receiver's coordinates are used server-side for distance
  calculations and are never returned at full precision by the API; the
  optional map marker is rounded (`MAP_RECEIVER_MARKER_PRECISION`) and off
  by default (`MAP_SHOW_RECEIVER_MARKER=false`).
- Clicking an aircraft's "機体情報を見る" (aircraft info) link fetches
  registration/type from `api.adsbdb.com` **directly from your browser**
  — the server is never involved and never sees which aircraft you
  looked up for this part. This is strictly opt-in per click; nothing is
  prefetched, and results aren't cached server-side.
- The **photo** lookup (`api.planespotters.net`) is different: it's
  proxied through this app's own server (`GET /api/aircraft/{icao}/photo`)
  rather than called directly from your browser. This was discovered
  during real-browser testing, not decided upfront: Planespotters
  requires a descriptive User-Agent with a contact URL and rejects
  generic ones, and a browser's own `fetch()` can never override its
  User-Agent (a forbidden header) — so the original direct-from-browser
  version shipped silently non-functional for every user. The trade-off:
  the server now sees which aircraft's photo you requested (still nothing
  persisted, still strictly opt-in per click) — narrower than before, but
  the feature actually works now.
- The **aircraft detail sidebar**'s live section
  (`WS /ws/aircraft/{icao}`) is a second, separate real-time exception:
  while the sidebar is open for a specific aircraft, the server
  independently polls your own `readsb` instance at the same cadence as
  the collector and streams the result to your browser. Nothing is
  persisted; this is scoped to one explicitly-selected aircraft.
- The **3D flight globe**'s default view is a third, broader exception:
  it genuinely is a live map of every currently-received aircraft's
  position/callsign/altitude/track/speed/roll/vertical-rate (not the
  sidebar's full tar1090-parity field set, and confined to this one
  page). A single shared `WS /ws/aircraft-positions` broadcast (one
  server-side readsb poll, fanned out to every connected client — never
  one poll per
  aircraft) drives it. Nothing is persisted (see `CLAUDE.md`).
- The daily-report's aircraft-type chart is a third, narrower server-side
  exception: every ~15 minutes, `adsb-type-lookup` looks up any newly-seen
  aircraft's type against `api.adsbdb.com` and caches the result
  permanently in its own database — never per page view, never
  re-queried once cached.
- The raw-data page (`/static/rawdata.html`) has the server open a plain
  TCP connection to your own `readsb` instance's Beast port
  (`READSB_BEAST_HOST`/`READSB_BEAST_PORT`) and relay it live over a
  WebSocket — this isn't a third-party call (it's the same `readsb` this
  app already depends on), and nothing from it is ever written to the
  database.
- `.env` is gitignored — never commit it. Only `.env.example` (with blank
  lat/lon and a placeholder password) is tracked.
- Backups (`scripts/backup.sh`) are written `chmod 600` into a `chmod 700`
  directory.

## Project status

Both the original Phase 1 MVP (collector, storage, API, dashboard) and a
set of Phase 2 extensions (receiver performance, distributions, heatmap,
daily rollups + webhook, aircraft revisit history, live raw-data view,
aircraft photo/type lookup, a tar1090-style live aircraft sidebar, and a
3D flight globe) are implemented — see `PLAN.md` for the full
milestone-by-milestone history.

Explicitly out of scope: runway/arrival/departure inference, go-around/
holding detection, ML anomaly detection, user accounts, multi-receiver
support, public hosting, replacing tar1090/fr24feed, Kubernetes, storing
raw Beast frames or a full position/velocity decoder (the raw-data page
is live/display-only with a simple DF/ICAO/category-only decode — see
[Raw data](#raw-data-staticrawdatahtml)), and bundling/redistributing an
offline aircraft metadata database (the realistic options turned out
unlicensed for redistribution — see
[Security & Privacy](#security--privacy) for what's used instead).

## Contributing

`CLAUDE.md` has the condensed operating rules for anyone (human or AI
agent) working in this repo — read it before making changes, especially
the constraints around never touching the host's existing
`readsb`/`tar1090`/`fr24feed` services. `PLAN.md` has the full design
rationale. Run `make lint` and `make test` before opening a PR.

## License

[MIT](LICENSE)
