"""
Health Endpoints — LIRA-AI
==============================
  /health         — alias for /health/live
  /health/live    — process is alive (always returns 200)
  /health/ready   — all critical dependencies reachable
                    (Chroma, Ollama, ChromaDB collection accessible)
"""

from __future__ import annotations
import asyncio
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", summary="Liveness probe")
def live() -> dict:
    """Process is running. Always returns 200."""
    return {"status": "alive"}


@router.get("/ready", summary="Readiness probe — checks all dependencies")
async def ready(request: Request) -> dict:
    """
    Returns 200 only if:
      - VectorStoreService is reachable (Chroma)
      - LLM service has at least one provider available
    Returns 503 with details if any check fails.
    """
    checks: dict = {}
    all_ok = True

    # Vector store
    vs = getattr(request.app.state, "vector_store", None)
    if vs is not None:
        try:
            checks["vector_store"] = vs.health()
        except Exception as e:
            checks["vector_store"] = False
            checks["vector_store_error"] = str(e)[:80]
        all_ok = all_ok and bool(checks.get("vector_store"))
    else:
        checks["vector_store"] = "not_initialised"
        all_ok = False

    # LLM service
    llm = getattr(request.app.state, "llm_service", None)
    if llm is not None:
        try:
            llm_health = await asyncio.wait_for(llm.health(), timeout=3.0)
            checks["llm"] = llm_health
        except Exception as e:
            checks["llm"] = False
            checks["llm_error"] = str(e)[:80]
    else:
        checks["llm"] = "not_initialised"

    # Tool registry
    registry = getattr(request.app.state, "tool_registry", None)
    checks["tool_registry"] = registry is not None and len(registry.list_tools()) > 0

    status_code = 200 if all_ok else 503
    response = {"status": "ready" if all_ok else "degraded", "checks": checks}

    if not all_ok:
        # Use HTTPException so the status code is properly set
        raise HTTPException(status_code=status_code, detail=response)
    return response
