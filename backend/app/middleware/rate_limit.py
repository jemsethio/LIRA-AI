"""
Rate Limiting Middleware — LIRA-AI
=====================================
SlowAPI-based rate limiting for expensive endpoints.

Limits (per IP):
  - /ai/*       60 requests / minute  (LLM is expensive)
  - /mcp/call   60 requests / minute  (calls MCP tools)
  - /rag/*      30 requests / minute  (vector ops)
  - default    300 requests / minute  (general API)

Skip:
  - /health/*, /metrics, /docs   (must always be reachable)
"""

from __future__ import annotations
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300/minute"],
    headers_enabled=False,    # Avoid requiring `response: Response` in every endpoint
)

# Predefined limits — apply via @limiter.limit(...) decorator on routes
LIMITS = {
    "ai":   "60/minute",
    "mcp":  "60/minute",
    "rag":  "30/minute",
}


def attach_rate_limiter(app: FastAPI) -> None:
    """Attach SlowAPI middleware to FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
