import logging
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.logging_config import new_request_id, request_id_ctx

logger = logging.getLogger("app.request")

# Health-check paths are hit continuously by Docker healthchecks and monitoring
# and carry no abuse risk, so they never count against the limit.
RATE_LIMIT_EXEMPT_PATHS = {"/api/health", "/api/system/health"}


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        rid = incoming or new_request_id()
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        logger.info(f"{request.method} {request.url.path} -> {response.status_code}")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window-per-client rate limit, in-memory.

    Deliberately not Redis-backed: this app runs as a single backend
    instance (see docker-compose.yml), so a per-process in-memory window is
    sufficient and avoids a new infra dependency. If the backend is ever
    scaled to multiple instances, this must move to a shared store (e.g.
    Redis) since each instance would otherwise enforce its own independent
    limit — documented in PRODUCTION.md.
    """

    def __init__(self, app, requests_per_minute: int | None = None):
        super().__init__(app)
        self.limit = requests_per_minute if requests_per_minute is not None else settings.rate_limit_per_minute
        self.window_seconds = 60.0
        self._hits: dict[str, deque] = {}

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0 or request.url.path in RATE_LIMIT_EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits.setdefault(client_ip, deque())
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = max(1, int(self.window_seconds - (now - hits[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again shortly."},
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if settings.app_env != "development":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
