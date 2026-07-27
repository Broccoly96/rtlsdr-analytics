"""Dependency-injection helpers for the FastAPI app.

The read-side pool is owned by the API app itself (created/closed in
main.py's lifespan) -- separate from the collector's own PostgresStore
pool, per PLAN.md Milestone C-1's "don't couple the write Store to the
read path."
"""

from __future__ import annotations

import asyncpg
from fastapi import Request


async def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


async def get_settings(request: Request):
    return request.app.state.settings
