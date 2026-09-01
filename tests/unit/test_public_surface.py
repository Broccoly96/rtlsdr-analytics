from __future__ import annotations

from httpx import ASGITransport, AsyncClient
from starlette.responses import PlainTextResponse

from app.api.public_surface import PublicSurfaceMiddleware


async def _downstream(scope, receive, send) -> None:
    if scope["type"] == "http":
        await PlainTextResponse("downstream")(scope, receive, send)
        return
    await send({"type": "websocket.accept"})


def _middleware() -> PublicSurfaceMiddleware:
    return PublicSurfaceMiddleware(_downstream, "public.broccolynet.com")


async def test_public_host_allows_only_reviewed_get_routes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_middleware()),
        base_url="https://public.broccolynet.com",
    ) as client:
        assert (await client.get("/")).status_code == 200
        assert (await client.get("/api/status")).status_code == 200
        assert (await client.head("/static/css/public.css")).status_code == 200


async def test_public_host_hides_private_and_unknown_routes() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_middleware()),
        base_url="https://public.broccolynet.com",
    ) as client:
        for path in (
            "/docs",
            "/openapi.json",
            "/health/ready",
            "/api/favorites",
            "/api/receiver/bearing-range",
            "/static/index.html",
            "/missing",
        ):
            response = await client.get(path)
            assert response.status_code == 404
            assert response.headers["cache-control"] == "no-store"


async def test_public_host_rejects_writes_before_downstream() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_middleware()),
        base_url="https://public.broccolynet.com",
    ) as client:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            response = await client.request(method, "/api/status")
            assert response.status_code == 405
            assert response.headers["allow"] == "GET"


async def test_non_public_host_is_unchanged_and_forwarded_host_is_ignored() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_middleware()),
        base_url="https://private.tailnet.example",
        headers={"X-Forwarded-Host": "public.broccolynet.com"},
    ) as client:
        response = await client.post("/api/favorites/abc123")
        assert response.status_code == 200
        assert response.text == "downstream"


async def test_public_host_rejects_encoded_path_alias() -> None:
    sent: list[dict] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/api/status",
        "raw_path": b"/api%2fstatus",
        "query_string": b"",
        "headers": [(b"host", b"public.broccolynet.com")],
        "client": ("127.0.0.1", 1234),
        "server": ("public.broccolynet.com", 443),
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    await _middleware()(scope, receive, send)
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 404


async def test_public_host_rejects_non_ascii_path_without_raw_path() -> None:
    sent: list[dict] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/日本語",
        "query_string": b"",
        "headers": [(b"host", b"public.broccolynet.com")],
        "client": ("127.0.0.1", 1234),
        "server": ("public.broccolynet.com", 443),
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    await _middleware()(scope, receive, send)
    assert sent[0]["status"] == 404


async def test_duplicate_host_mentioning_public_fails_closed() -> None:
    sent: list[dict] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [
            (b"host", b"evil.example"),
            (b"host", b"public.broccolynet.com"),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("public.broccolynet.com", 443),
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    await _middleware()(scope, receive, send)
    assert sent[0]["status"] == 400


async def test_public_host_rejects_every_websocket_before_accept() -> None:
    sent: list[dict] = []
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "wss",
        "path": "/ws/aircraft-positions",
        "raw_path": b"/ws/aircraft-positions",
        "query_string": b"",
        "headers": [(b"host", b"public.broccolynet.com")],
        "client": ("127.0.0.1", 1234),
        "server": ("public.broccolynet.com", 443),
        "subprotocols": [],
    }

    async def receive() -> dict:
        return {"type": "websocket.connect"}

    async def send(message: dict) -> None:
        sent.append(message)

    await _middleware()(scope, receive, send)
    assert sent == [{"type": "websocket.close", "code": 1008, "reason": "not public"}]
