"""Unified JSON error responses.

No secrets, DB URLs, or tracebacks are ever returned to the client -- the
real exception is logged server-side and a generic message goes out
instead (PLAN.md Milestone C-1).
"""

from __future__ import annotations

import logging

import asyncpg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.schemas import ErrorResponse

logger = logging.getLogger(__name__)


def _error_response(status_code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content=ErrorResponse(error=error, detail=detail).model_dump()
    )


async def _http_exception(request: Request, exc: StarletteHTTPException):
    return _error_response(exc.status_code, "http_error", str(exc.detail))


async def _validation_error(request: Request, exc: RequestValidationError):
    return _error_response(422, "invalid_request", "one or more query parameters were invalid")


async def _timeout_error(request: Request, exc: TimeoutError):
    logger.warning("query timed out on %s", request.url.path)
    return _error_response(503, "database_unavailable", "the database did not respond in time")


async def _db_error(request: Request, exc: Exception):
    logger.exception("database error on %s", request.url.path)
    return _error_response(503, "database_unavailable", "the database is temporarily unavailable")


async def _unhandled_error(request: Request, exc: Exception):
    logger.exception("unhandled error on %s", request.url.path)
    return _error_response(500, "internal_error", "an unexpected error occurred")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(TimeoutError, _timeout_error)
    app.add_exception_handler(asyncpg.PostgresError, _db_error)
    app.add_exception_handler(OSError, _db_error)
    app.add_exception_handler(Exception, _unhandled_error)
