"""Deny-by-default boundary for an optional anonymous public hostname."""

from __future__ import annotations

from urllib.parse import unquote

from starlette.datastructures import Headers
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

PUBLIC_HTTP_ROUTES: dict[str, frozenset[str]] = {
    "/": frozenset({"GET"}),
    "/api/status": frozenset({"GET"}),
    "/static/public.html": frozenset({"GET", "HEAD"}),
    "/static/css/public.css": frozenset({"GET", "HEAD"}),
    "/static/js/public.js": frozenset({"GET", "HEAD"}),
    "/static/icons/favicon-32.png": frozenset({"GET", "HEAD"}),
}


def _normalized_host_value(host: str) -> str:
    host = host.strip().lower().rstrip(".")
    if host.startswith("["):
        end = host.find("]")
        return host[1:end] if end >= 0 else host
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def normalized_host(scope: Scope) -> str:
    """Return one normalized Host, or empty for missing/duplicate headers."""
    hosts = Headers(scope=scope).getlist("host")
    return _normalized_host_value(hosts[0]) if len(hosts) == 1 else ""


def is_public_scope(scope: Scope, public_hostname: str | None) -> bool:
    return public_hostname is not None and normalized_host(scope) == public_hostname


class PublicSurfaceMiddleware:
    """Restrict one exact Host to a reviewed, read-only HTTP surface."""

    def __init__(self, app: ASGIApp, public_hostname: str | None) -> None:
        self.app = app
        self.public_hostname = public_hostname

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"} or self.public_hostname is None:
            await self.app(scope, receive, send)
            return

        hosts = Headers(scope=scope).getlist("host")
        targets_public = any(_normalized_host_value(host) == self.public_hostname for host in hosts)
        if not targets_public:
            await self.app(scope, receive, send)
            return

        # A request mentioning the public Host more than once is ambiguous.
        # Fail closed instead of letting it bypass the public-only policy.
        if len(hosts) != 1:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008, "reason": "invalid host"})
            else:
                await _policy_response(400, "invalid_host", "Invalid Host header")(
                    scope, receive, send
                )
            return

        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008, "reason": "not public"})
            return

        raw_path = scope.get("raw_path")
        if raw_path is None:
            raw_path = scope["path"].encode("utf-8")
        if b"%" in raw_path:
            await self._not_found(scope, receive, send)
            return
        try:
            path = unquote(raw_path.decode("ascii"), errors="strict")
        except (UnicodeDecodeError, UnicodeEncodeError):
            await self._not_found(scope, receive, send)
            return
        if path != scope["path"]:
            await self._not_found(scope, receive, send)
            return

        method = scope["method"].upper()
        allowed_methods = PUBLIC_HTTP_ROUTES.get(path)
        if allowed_methods is None:
            await self._not_found(scope, receive, send)
            return
        if method not in allowed_methods:
            await self._method_not_allowed(scope, receive, send, allowed_methods)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _not_found(scope: Scope, receive: Receive, send: Send) -> None:
        await _policy_response(404, "not_found", "Not found")(scope, receive, send)

    @staticmethod
    async def _method_not_allowed(
        scope: Scope, receive: Receive, send: Send, allowed_methods: frozenset[str]
    ) -> None:
        response = _policy_response(405, "method_not_allowed", "Method not allowed")
        response.headers["Allow"] = ", ".join(sorted(allowed_methods))
        await response(scope, receive, send)


def _policy_response(status_code: int, error: str, detail: str) -> Response:
    return JSONResponse(
        {"error": error, "detail": detail},
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
        },
    )
