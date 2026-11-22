"""Request ID, access log and RED metrics for every HTTP request."""

import re
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_ID_HEADER = "X-Request-ID"
METRICS_PATH = "/metrics"
QUIET_PATHS = frozenset({METRICS_PATH, "/api/health/live", "/api/health/ready"})
UNMATCHED_ROUTE = "unmatched"
# A client-supplied ID ends up in the logs, so only a harmless form is accepted.
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{8,64}")

REQUESTS = Counter("http_requests", "HTTP requests", ["method", "route", "status"])
DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 2.5, 5, 10),
)

log = structlog.get_logger(__name__)


def resolve_request_id(supplied: str | None) -> str:
    if supplied and REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return str(uuid.uuid4())


def route_template(request: Request) -> str:
    """The route pattern instead of the path, which keeps metric cardinality bounded."""
    path = getattr(request.scope.get("route"), "path", None)
    return path if isinstance(path, str) else UNMATCHED_ROUTE


def install_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def observe(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        except Exception:
            log.exception("request_failed")
            raise
        finally:
            elapsed = time.perf_counter() - started
            route = route_template(request)
            if request.url.path not in QUIET_PATHS:
                REQUESTS.labels(request.method, route, str(status_code)).inc()
                DURATION.labels(request.method, route).observe(elapsed)
                log.info(
                    "http_request",
                    method=request.method,
                    route=route,
                    status=status_code,
                    duration_ms=round(elapsed * 1000, 1),
                )

    @app.get(METRICS_PATH, include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
