"""
MCP Router — LIRA-AI
======================
HTTP façade for the MCP tool registry with typed input validation.

Improvements over v1:
  - Per-tool Pydantic schema validation (eliminates `fn(**req.inputs)` DoS)
  - Singleton ToolRegistry (no per-call import overhead)
  - Rate limiting (60/min per IP)
  - Prometheus metrics per tool call
  - Latency tracking
"""

from __future__ import annotations
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any

from app.middleware.rate_limit import limiter, LIMITS
from app.observability.metrics import mcp_tool_calls_total, mcp_tool_duration_seconds

router = APIRouter(prefix="/mcp", tags=["MCP Tools"])


@router.get("/tools", summary="List all available MCP tools")
def list_tools(request: Request) -> dict:
    """List all scientific tools exposed via the LIRA-AI MCP server."""
    return {
        "mcp_server": "LIRA-AI Landscape Futures Lab",
        "transport":  "HTTP (REST) + stdio (for MCP clients)",
        "run_standalone": "python -m app.mcp.server",
        "tools": [
            {"name": "diagnose_landscape",   "description": "Full indicator engine + syndrome classifier + LHII",
             "inputs": ["project_id", "soil_loss_rate", "ndvi", "rainfall", "slope", "..."]},
            {"name": "compute_rusle",        "description": "Enhanced RUSLE soil erosion — Ethiopia-calibrated (Hurni 1985)",
             "inputs": ["rainfall_mm", "slope_deg", "ndvi", "soil_texture", "soc_g_per_kg"]},
            {"name": "fetch_soilgrids",      "description": "Real SoilGrids v2.0 — SOC, clay, pH, bulk density",
             "inputs": ["lon", "lat"]},
            {"name": "fetch_sentinel2_ndvi", "description": "Real Sentinel-2 L2A NDVI — Planetary Computer (EPSG:32637)",
             "inputs": ["west", "south", "east", "north", "date_range"]},
            {"name": "get_climate_risk",     "description": "NASA NEX GDDP CMIP6 risk scores — SSP245/SSP585",
             "inputs": ["scenario", "horizon", "model", "west/south/east/north"]},
            {"name": "search_cgspace",       "description": "CGIAR CGSpace evidence search — DSpace 7+ API",
             "inputs": ["query", "n_results"]},
            {"name": "retrieve_rag",         "description": "Semantic search over indexed project documents",
             "inputs": ["project_id", "query", "n_results"]},
            {"name": "generate_pathways",    "description": "7 restoration pathway packages for a diagnosed syndrome",
             "inputs": ["project_id", "primary_syndrome", "degradation_severity"]},
            {"name": "get_zone_data",        "description": "Real indicator data for Omo-Ghibe zones (highland/midland/lowland/riverine)",
             "inputs": ["zone_id"]},
            {"name": "narrate_summary",      "description": "AI narrative via Ollama — 120-word data-grounded summary",
             "inputs": ["narrative_type", "context (dict or stringified JSON)"]},
        ],
    }


class ToolCallRequest(BaseModel):
    tool:   str
    inputs: dict[str, Any] = {}


@router.post("/call", summary="Call an MCP tool via REST")
@limiter.limit(LIMITS["mcp"])
def call_tool(request: Request, req: ToolCallRequest) -> dict:
    """
    Invoke an MCP tool by name. Inputs are validated against the tool's
    Pydantic schema before the tool function is called.

    Returns: {tool, result, _meta: {tool_version, latency_ms}}
    """
    registry = getattr(request.app.state, "tool_registry", None)
    if registry is None:
        raise HTTPException(503, "ToolRegistry not initialised")

    t0 = time.time()
    try:
        result = registry.call(req.tool, req.inputs)
        status = "ok"
    except HTTPException as e:
        status = f"http_{e.status_code}"
        mcp_tool_calls_total.labels(tool=req.tool, status=status).inc()
        mcp_tool_duration_seconds.labels(tool=req.tool).observe(time.time() - t0)
        raise

    latency_s = time.time() - t0
    mcp_tool_calls_total.labels(tool=req.tool, status=status).inc()
    mcp_tool_duration_seconds.labels(tool=req.tool).observe(latency_s)

    return {
        "tool":    req.tool,
        "result":  result,
        "_meta": {
            "tool_version": "1.0",
            "latency_ms":   int(latency_s * 1000),
        },
    }
