"""FastAPI application factory.

Deliberately has no module-level side effects (no eager Settings() or pool
construction) so `create_app` can be imported freely by tests with a custom
Settings instance. The real, eagerly-constructed app for uvicorn lives in
app/api/asgi.py.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_exception_handlers
from app.api.public_surface import PublicSurfaceMiddleware, is_public_scope
from app.api.routers import (
    aircraft,
    aircraft_history,
    aircraft_live,
    aircraft_positions,
    badges,
    config,
    distribution,
    favorites,
    health,
    heatmap,
    rankings,
    rawdata,
    receiver,
    status,
    tracks,
    traffic,
    weather,
)
from app.api.routers.aircraft_positions import PositionBroadcaster
from app.config import Settings
from app.db.pool import close_pool, create_pool

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
}


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        app.state.pool = await create_pool(resolved_settings.database_url)
        app.state.position_broadcaster = PositionBroadcaster(
            resolved_settings.readsb_aircraft_url,
            resolved_settings.poll_interval_seconds,
            resolved_settings.receiver_lat,
            resolved_settings.receiver_lon,
        )
        await app.state.position_broadcaster.start()
        try:
            yield
        finally:
            await app.state.position_broadcaster.stop()
            await close_pool(app.state.pool)

    app = FastAPI(title="ADS-B Analytics API", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(status.router)
    app.include_router(traffic.router)
    app.include_router(tracks.router)
    app.include_router(rankings.router)
    app.include_router(aircraft.router)
    app.include_router(aircraft_history.router)
    app.include_router(config.router)
    app.include_router(receiver.router)
    app.include_router(distribution.router)
    app.include_router(heatmap.router)
    app.include_router(rawdata.router)
    app.include_router(aircraft_live.router)
    app.include_router(aircraft_positions.router)
    app.include_router(favorites.router)
    app.include_router(badges.router)
    app.include_router(weather.router)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def dashboard(request: Request) -> FileResponse:
        filename = (
            "public.html"
            if is_public_scope(request.scope, resolved_settings.public_hostname)
            else "index.html"
        )
        return FileResponse(STATIC_DIR / filename)

    # Served at the root (not /static/manifest.json or /static/sw.js) so
    # the service worker's default scope covers the whole app (/), not
    # just /static/ -- PWA installability needs start_url within scope.
    @app.get("/manifest.json", include_in_schema=False)
    async def pwa_manifest() -> FileResponse:
        return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker() -> FileResponse:
        return FileResponse(STATIC_DIR / "sw.js", media_type="text/javascript")

    @app.middleware("http")
    async def response_policy(request: Request, call_next):
        # This dashboard is small, low-traffic, and actively iterated on --
        # a stale cached copy of index.html/JS/CSS silently showing an old
        # build (with no visible sign anything is wrong) is a worse outcome
        # than the browser re-fetching a few hundred KB on every load.
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        if (
            request.url.path == "/"
            or request.url.path.startswith("/static/")
            or request.url.path in ("/manifest.json", "/sw.js", "/api/status")
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.add_middleware(
        PublicSurfaceMiddleware,
        public_hostname=resolved_settings.public_hostname,
    )

    return app
