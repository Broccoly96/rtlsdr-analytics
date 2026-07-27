"""FastAPI application factory.

Deliberately has no module-level side effects (no eager Settings() or pool
construction) so `create_app` can be imported freely by tests with a custom
Settings instance. The real, eagerly-constructed app for uvicorn lives in
app/api/asgi.py.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routers import aircraft, health, rankings, status, tracks, traffic
from app.config import Settings
from app.db.pool import close_pool, create_pool


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
    return app
