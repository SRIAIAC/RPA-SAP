"""RateLimitMiddleware, tested against its own minimal app.

The shared `app` fixture (see conftest.py) runs with rate limiting
effectively disabled because the full test suite fires far more than any
sane per-minute limit through one shared middleware instance. So this file
builds its own tiny FastAPI app with a small limit to verify the actual
429 behavior deterministically, independent of test execution order/count.
"""

import asyncio
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import RateLimitMiddleware


def _make_app(limit: int) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=limit)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/thing")
    def thing():
        return {"ok": True}

    return app


def test_requests_under_the_limit_succeed():
    client = TestClient(_make_app(limit=5))
    for _ in range(5):
        resp = client.get("/api/thing")
        assert resp.status_code == 200


def test_requests_over_the_limit_are_rejected_with_429():
    client = TestClient(_make_app(limit=5))
    for _ in range(5):
        assert client.get("/api/thing").status_code == 200

    resp = client.get("/api/thing")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert "too many requests" in resp.json()["detail"].lower()


def test_health_endpoint_is_exempt_from_rate_limiting():
    client = TestClient(_make_app(limit=2))
    for _ in range(10):
        assert client.get("/api/health").status_code == 200


def _fake_request(ip: str, path: str = "/api/thing"):
    return SimpleNamespace(client=SimpleNamespace(host=ip), url=SimpleNamespace(path=path))


async def _ok_call_next(request):
    return SimpleNamespace(status_code=200)


def test_limit_is_tracked_per_client_ip_separately():
    middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
    middleware.limit = 2
    middleware.window_seconds = 60.0
    middleware._hits = {}

    dispatch = lambda req: asyncio.run(middleware.dispatch(req, _ok_call_next))

    assert dispatch(_fake_request("10.0.0.1")).status_code == 200
    assert dispatch(_fake_request("10.0.0.1")).status_code == 200
    # IP A is now at the limit...
    assert dispatch(_fake_request("10.0.0.1")).status_code == 429
    # ...but IP B, which has made no requests, is unaffected.
    assert dispatch(_fake_request("10.0.0.2")).status_code == 200
    assert dispatch(_fake_request("10.0.0.2")).status_code == 200
    assert dispatch(_fake_request("10.0.0.2")).status_code == 429


def test_zero_limit_disables_rate_limiting():
    client = TestClient(_make_app(limit=0))
    for _ in range(20):
        assert client.get("/api/thing").status_code == 200
