# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

Phase 0 and Phase 1 are both implemented, plus a set of Phase 2 extensions
beyond the original MVP scope (receiver-performance page, daily
report/webhook, aircraft revisit history, heatmap, CSV export — see
`README.md` for the current feature list). `PLAN.md` (written in Japanese)
is the authoritative design record and session log; **read it in full
before starting non-trivial work**, and update its task checkboxes
(`- [ ]`) as work progresses. Build/lint/test commands exist today: `make
install`, `make lint`, `make fmt`, `make test` (see `Makefile`). Do not
invent commands or a directory layout that contradicts what's actually in
the repo; treat the structure below as broadly accurate, not aspirational.

## What this project is

A personal web app that pulls ADS-B decode data from a `readsb` instance already running on a Linux x86-64 server, stores history, and displays it. It is explicitly **not** a tar1090 replacement and does not do real-time tracking — it's a historical-storage-and-analytics layer alongside the existing `readsb` / `tar1090` / `fr24feed` setup.

Work is split into two phases:
- **Phase 0 — Environment check**: read-only inspection of the server, `readsb`, network, disk, and runtime, producing `reports/environment-report.md` and `reports/environment-report.json` with PASS/WARN/FAIL/UNKNOWN verdicts per check.
- **Phase 1 — MVP**: a collector that polls `readsb`'s `aircraft.json`, a Postgres store, a FastAPI backend, and a single-page dashboard (current aircraft, 24h traffic chart, recent tracks map, farthest/closest rankings, data-freshness/error state).

## Critical operating constraints (from PLAN.md §4)

These are hard rules for this repo, not suggestions, because this app runs alongside live production services on a real server:

- **Never stop, restart, or reconfigure the existing `readsb`, `tar1090`, or `fr24feed` services or their config/comms paths** without explicit necessity and approval.
- Phase 0 tooling must be **read-only** — no file, package, or service-config changes — and runnable as a normal (non-root) user.
- Any change requiring `sudo`, firewall edits, new exposed ports, or DNS/TLS setup must be presented (target + impact) **before** execution, not applied silently.
- Never write secrets to git, logs, the screen, or test artifacts. Commit only `.env.example`, never `.env`.
- If real `readsb` data is captured as a test fixture, anonymize it first (ICAO addresses, callsigns, coordinates).
- Check existing container names and ports on the target server before choosing new ones for this app.
- Internet/LAN exposure is out of scope for the Phase 1 MVP — get it working on localhost/LAN first; external exposure is an explicit later choice.
- If the real environment doesn't match the assumed defaults, **adapt the app's config**, not the existing system.
- On a FAIL verdict in Phase 0, stop and report cause/impact/minimal fix — don't silently work around it. WARN-only results can proceed after adjusting to a safe configuration.

## Planned architecture

```
readsb aircraft.json
        |
        v
   collector ─────> PostgreSQL
                        |
                        v
                  FastAPI (API + static serving)
                        |
                        v
                     Web UI
```

Six Docker Compose services today (collector, retention, daily-rollup, and
API share one image, built once from `Dockerfile` — see `compose.yaml`'s
`command:` per service for which process each one runs):
- `adsb-db` — PostgreSQL, never exposed on a host port
- `adsb-migrate` — one-shot Alembic `upgrade head`, gates all app services
- `adsb-collector` — polls `readsb`, normalizes, writes to Postgres
- `adsb-retention` — deletes old `observations`/`ingestion_status` rows in batches
- `adsb-daily-rollup` — computes the previous day's summary, sends the optional webhook
- `adsb-api` — FastAPI, serves the UI and health checks

Directory layout: `app/{api,collector,db,domain,static}/`, `migrations/`,
`scripts/` (`check_environment.sh`, `probe_readsb.py`, `backup.sh`,
`restore_test.sh`, `db_status.py`, `reset_db.py`), `tests/{fixtures,unit,
integration,contract}/`, `reports/`. `app/templates/` exists but is empty
and unused — the UI is plain static HTML/JS (`app/static/`), not
server-rendered templates.

### Data flow / collector rules
- Poll `aircraft.json` on a short interval (default 5s) with a short HTTP timeout; use exponential backoff on failure and return to normal cadence on recovery — never hammer `readsb` with retries.
- Normalize `hex` as the aircraft identifier; exclude aircraft whose `seen`/`seen_pos` are stale from "currently received" counts.
- Don't persist a position on every poll — sample per-aircraft roughly every 30s or on significant position/altitude change.
- Don't store raw full HTTP responses. Ingestion must be idempotent (reprocessing the same observation shouldn't duplicate it) and must not grow memory unbounded while the DB is down.

### Data model (minimum)
- `aircraft(icao PK, first_seen_at, last_seen_at, last_callsign)`
- `observations(id, observed_at, icao, callsign, lat, lon, altitude_ft, ground_speed_kt, track_deg, vertical_rate_fpm, rssi, distance_km, bearing_deg, source_age_seconds)` — indexed on `(icao, observed_at)`, `(observed_at)`, `(distance_km, observed_at)`
- `traffic_minute(bucket_at, active_aircraft_count, position_aircraft_count, message_count_delta)`
- `ingestion_status(checked_at, success, latency_ms, aircraft_count, error_code)`

### Metric definitions (exact semantics — don't drift from these)
- **Currently received**: unique ICAOs in the latest poll with `seen <= 15s`.
- **Position acquired**: currently-received aircraft with a valid lat/lon and `seen_pos <= 30s`.
- **1-minute concurrent count**: max "currently received" count observed within that minute.
- **1h/1d unique aircraft**: distinct ICAOs that were "currently received" at least once in the window.
- **Farthest / closest**: great-circle distance from the configured receiver location, over observations with valid positions; exclude invalid coordinates, out-of-range altitude, and future timestamps (and track how many records get excluded).

### Retention
Raw observations: 30 days default. Minute aggregates: kept long-term (1+ year). Logs: rotated, ~14 days. Deletion must run in small batches (no long DB locks).

### Configuration (env vars)
`READSB_AIRCRAFT_URL`, `RECEIVER_LAT`, `RECEIVER_LON`, `DISPLAY_TIMEZONE` (default `Asia/Tokyo`), `POLL_INTERVAL_SECONDS` (5), `TRACK_SAMPLE_SECONDS` (30), `RAW_RETENTION_DAYS` (30), `DATABASE_URL`, `APP_BIND_HOST` (default `127.0.0.1`), `APP_PORT` (8088), `MAP_STYLE_URL`. Validate all of these at startup and fail with a clear message rather than starting in a bad state.

### API surface (planned)
`GET /health/live`, `GET /health/ready` (must reflect DB connectivity and recent `readsb` fetch success — go unhealthy if no successful fetch recently), `GET /api/status`, `GET /api/traffic?hours=24`, `GET /api/tracks?hours=6` (must cap/decimate points), `GET /api/rankings?hours=24&limit=10`, `GET /api/aircraft/recent`. All endpoints need input bounds and timeouts.

### Tech defaults assumed (confirm/adjust in Phase 0 rather than treating as fixed)
x86-64 Linux with systemd, Docker Engine + Compose v2, PostgreSQL, Python + FastAPI, plain HTML/JS frontend with Apache ECharts and MapLibre GL JS, UTC storage with display-side timezone conversion.

### Explicitly out of scope for this MVP
Runway/arrival/departure inference, go-around/holding detection, ML anomaly detection, user accounts, multi-receiver support, public hosting, replacing tar1090/fr24feed, Kubernetes.

Two items from the original MVP scope were revisited later, at the user's explicit request, and are now *partially* in scope — read the qualification before assuming either is fully open-ended:
- **Raw Beast frame storage or a full decoder**: still out of scope. What exists instead (`/static/rawdata.html`, `app/domain/beast.py`, `app/api/routers/rawdata.py`) is a live, ephemeral, display-only relay with a deliberately *simple* decode (DF/ICAO24/CA/ADS-B type-code category only) — nothing is ever persisted to the DB, and CPR position/velocity decoding remains readsb's job, not this app's.
- **Aircraft/airline metadata enrichment**: still out of scope as an *offline bundled dataset* (the realistic options turned out unlicensed for redistribution — see `aircraft_lookup.py`'s docstring). What exists instead is registration/type/photo lookup against two free third-party APIs (`api.adsbdb.com`, `api.planespotters.net`) — click-triggered from the browser almost everywhere, plus one narrow server-side cache (`aircraft_type_cache`, populated once per aircraft ever, only from `app/dailyrollup.py`'s loop) backing the daily aircraft-type chart. See README's Security & Privacy section for the exact scope of each.

## Testing expectations once implemented

Per PLAN.md §8, exercise these scenarios: normal ingest→store→aggregate→API→UI flow; `readsb` outage (collector backs off without crash-looping, UI shows "data stopped", auto-recovers) — **use a mock/disabled test URL, never the production `readsb` service**; DB outage (bounded memory, `/health/ready` goes unhealthy, auto-recovery on DB return); malformed data (empty array, missing fields, lat-only, `alt_baro: "ground"`, future timestamps, out-of-range coordinates, duplicate ICAOs, huge aircraft counts) — none of these should take down the whole service, only the affected record.
