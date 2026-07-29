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
from app.api.routers import (
    aircraft,
    config,
    distribution,
    health,
    rankings,
    receiver,
    status,
    tracks,
    traffic,
)
from app.config import Settings
from app.db.pool import close_pool, create_pool

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        app.state.pool = await create_pool(resolved_settings.database_url)
        try:
            yield
        finally:
            await close_pool(app.state.pool)

    app = FastAPI(title="ADS-B Analytics API", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(status.router)
    app.include_router(traffic.router)
    app.include_router(tracks.router)
    app.include_router(rankings.router)
    app.include_router(aircraft.router)
    app.include_router(config.router)
    app.include_router(receiver.router)
    app.include_router(distribution.router)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.middleware("http")
    async def no_cache_for_dashboard_assets(request: Request, call_next):
        # This dashboard is small, low-traffic, and actively iterated on --
        # a stale cached copy of index.html/JS/CSS silently showing an old
        # build (with no visible sign anything is wrong) is a worse outcome
        # than the browser re-fetching a few hundred KB on every load.
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
