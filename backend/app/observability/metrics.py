"""
Prometheus Metrics — LIRA-AI
==============================
Counters, histograms, gauges for system observability.
Mounted at /metrics for Prometheus scraping.
"""

from __future__ import annotations
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response


# ── Registry & metrics ───────────────────────────────────────────────────────

REGISTRY = CollectorRegistry()

# HTTP request counter
http_requests_total = Counter(
    "lira_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)

# HTTP request latency
http_request_duration_seconds = Histogram(
    "lira_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY,
)

# MCP tool calls
mcp_tool_calls_total = Counter(
    "lira_mcp_tool_calls_total",
    "MCP tool invocations",
    ["tool", "status"],
    registry=REGISTRY,
)

mcp_tool_duration_seconds = Histogram(
    "lira_mcp_tool_duration_seconds",
    "MCP tool execution latency",
    ["tool"],
    registry=REGISTRY,
)

# LLM calls
llm_calls_total = Counter(
    "lira_llm_calls_total",
    "LLM provider invocations",
    ["provider", "is_llm"],
    registry=REGISTRY,
)

llm_latency_seconds = Histogram(
    "lira_llm_latency_seconds",
    "LLM call latency",
    ["provider"],
    registry=REGISTRY,
)

# Vector store
vector_store_documents = Gauge(
    "lira_vector_store_documents",
    "Number of chunks in the vector store",
    registry=REGISTRY,
)

rag_retrievals_total = Counter(
    "lira_rag_retrievals_total",
    "RAG retrieval calls",
    ["project_id"],
    registry=REGISTRY,
)


# ── /metrics endpoint ────────────────────────────────────────────────────────

router = APIRouter(tags=["Observability"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Prometheus scrape endpoint."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
