"""
Logging Middleware — LIRA-AI
==============================
Structlog-based JSON logger with per-request correlation IDs.
Each HTTP request gets a unique trace_id propagated through all log lines.
"""

from __future__ import annotations
import time
import uuid
import logging
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def configure_structlog() -> None:
    """Call once at app startup."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger("lira-ai")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Attach a trace_id to every request, log start/end with duration.
    Skips /health/* and /metrics to keep logs clean.
    """

    SKIP_PATHS = ("/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico")

    async def dispatch(self, request: Request, call_next):
        # Re-use upstream trace id (e.g. from a proxy) or generate fresh
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex[:12]

        # Bind to all logs in this request via contextvars
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
        )

        should_log = not any(request.url.path.startswith(p) for p in self.SKIP_PATHS)
        if should_log:
            logger.info("request.start")

        t0 = time.time()
        try:
            response: Response = await call_next(request)
        except Exception:
            logger.exception("request.error", duration_ms=int((time.time() - t0) * 1000))
            structlog.contextvars.clear_contextvars()
            raise

        duration_ms = int((time.time() - t0) * 1000)
        response.headers["X-Trace-Id"] = trace_id

        if should_log:
            logger.info(
                "request.end",
                status=response.status_code,
                duration_ms=duration_ms,
            )

        structlog.contextvars.clear_contextvars()
        return response
