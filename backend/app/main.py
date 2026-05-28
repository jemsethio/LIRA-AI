"""
LIRA-AI FastAPI application entrypoint.

Lifespan-managed singletons:
  - VectorStoreService  → ChromaDB + sentence-transformers (loaded once)
  - AsyncLLMService     → httpx.AsyncClient with bounded concurrency
  - ToolRegistry        → typed MCP tool dispatch with input validation

Middleware stack:
  - CORS                → cross-origin from configured frontend origins
  - CorrelationId       → trace_id per request, structured JSON logs
  - RateLimit           → SlowAPI (60/min for /ai, /mcp; 30/min for /rag)

Observability:
  - /metrics             → Prometheus scrape endpoint
  - /health/live         → process is up
  - /health/ready        → all critical dependencies reachable
"""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    projects, diagnosis, climate, pathways,
    investment, community, export, evidence, monitoring, advisory,
    omo_ghibe, climate_data, agronomy, spatial, ai, agents, rag, mcp_router,
)

# Phase 1+: foundation services + observability
from app.services.vector_store import VectorStoreService
from app.services.llm_async import AsyncLLMService
from app.mcp.registry import ToolRegistry
from app.middleware.logging import configure_structlog, CorrelationIdMiddleware
from app.middleware.rate_limit import attach_rate_limiter
from app.observability import metrics as metrics_module
from app.observability import health as health_module

configure_structlog()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: build singleton services and attach to app.state.
    Shutdown: close async resources gracefully.
    """
    # ── Startup ────────────────────────────────────────────────────────────
    logger.info("LIRA-AI starting up")

    # VectorStoreService (loads sentence-transformer model into memory)
    try:
        app.state.vector_store = VectorStoreService()
        logger.info("VectorStoreService initialised")
    except Exception as e:
        logger.warning("VectorStoreService unavailable: %s", e)
        app.state.vector_store = None

    # AsyncLLMService (httpx.AsyncClient with connection pool)
    app.state.llm_service = AsyncLLMService(max_concurrent=4, timeout_s=60.0)
    logger.info("AsyncLLMService initialised")

    # MCP Tool Registry (typed validation)
    try:
        app.state.tool_registry = ToolRegistry.build()
        logger.info("ToolRegistry initialised with %d tools",
                    len(app.state.tool_registry.list_tools()))
    except Exception as e:
        logger.warning("ToolRegistry unavailable: %s", e)
        app.state.tool_registry = None

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("LIRA-AI shutting down")
    if getattr(app.state, "llm_service", None):
        await app.state.llm_service.close()
    if getattr(app.state, "vector_store", None):
        app.state.vector_store.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "LIRA-AI: Predictive Intelligence for Investable Landscape Regeneration. "
        "A Landscape Futures Lab prototype for Ethiopia and CGIAR MFL, CASP landscapes. "
        "Data sources: Microsoft Planetary Computer, SoilGrids, CHIRPS, ERA5."
    ),
    lifespan=lifespan,
)

# ── Middleware stack (order matters: outermost first) ────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation IDs + structured logging
app.add_middleware(CorrelationIdMiddleware)

# Rate limiting (SlowAPI)
attach_rate_limiter(app)


# ── Observability routes (loaded first so they bypass app-specific logic) ────

app.include_router(metrics_module.router)
app.include_router(health_module.router)


# ── Application routers ───────────────────────────────────────────────────────

# Core analysis pipeline
app.include_router(projects.router)
app.include_router(evidence.router)
app.include_router(diagnosis.router)
app.include_router(climate.router)
app.include_router(pathways.router)
app.include_router(investment.router)
app.include_router(community.router)
app.include_router(monitoring.router)
app.include_router(advisory.router)
app.include_router(export.router)
app.include_router(agronomy.router)
app.include_router(spatial.router)
app.include_router(ai.router)
app.include_router(agents.router)
app.include_router(rag.router)
app.include_router(mcp_router.router)
app.include_router(omo_ghibe.router)
app.include_router(climate_data.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "system": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "description": "Landscape Futures Lab — predictive intelligence for landscape regeneration",
        "data_sources": [
            "Microsoft Planetary Computer (Sentinel-2, Landsat, DEM, WorldCover, MODIS, CHIRPS, ERA5)",
            "SoilGrids v2.0 — ISRIC",
            "HLS (Harmonized Landsat Sentinel-2) — NASA LPDAAC",
        ],
        "agents": [
            "LandscapeEvidenceAgent", "ClimateFuturesAgent", "CausalDiagnosisAgent",
            "SoilDoctorAgent", "WaterDoctorAgent", "VegetationBiodiversityAgent",
            "AgronomyAgent", "RangelandLivestockAgent", "CommunityIntelligenceAgent",
            "PolicyAlignmentAgent", "TradeoffMaladaptationAgent",
            "InvestmentPlanningAgent", "AdaptiveMonitoringAgent", "AdvisoryCommunicationAgent",
        ],
        "docs": "/docs",
        "health": "/health/ready",
        "metrics": "/metrics",
    }


# Legacy /health endpoint (alias for /health/live) — preserves backward compat
@app.get("/health", tags=["Health"], include_in_schema=False)
def health_legacy():
    return {"status": "ok"}
