"""
ToolRegistry — LIRA-AI MCP
==============================
Typed registry that validates inputs against per-tool Pydantic schemas
BEFORE calling the underlying function.

Replaces the unchecked `fn(**req.inputs)` pattern in mcp_router.py which
exposed a TypeError-DoS surface.

The actual tool functions in app/mcp/server.py are unchanged — this is a
defensive wrapper. Tool names, signatures, and return shapes are preserved.
"""

from __future__ import annotations
import logging
from typing import Any, Callable
from fastapi import HTTPException
from pydantic import ValidationError

from app.mcp.schemas import INPUT_SCHEMAS

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Singleton registry of MCP tools.

    Usage:
      registry = ToolRegistry.build()       # in main.py lifespan
      result   = registry.call(name, inputs)
    """

    _instance: "ToolRegistry | None" = None

    def __init__(self, tools: dict[str, Callable]) -> None:
        self._tools = tools

    # ── Construction ──────────────────────────────────────────────────────────

    @classmethod
    def build(cls) -> "ToolRegistry":
        """Lazy import of server.py to avoid circular dependencies on cold start."""
        from app.mcp.server import (
            diagnose_landscape, compute_rusle, fetch_soilgrids,
            fetch_sentinel2_ndvi, get_climate_risk, search_cgspace,
            retrieve_rag, generate_pathways, get_zone_data, narrate_summary,
        )
        tools: dict[str, Callable] = {
            "diagnose_landscape":   diagnose_landscape,
            "compute_rusle":        compute_rusle,
            "fetch_soilgrids":      fetch_soilgrids,
            "fetch_sentinel2_ndvi": fetch_sentinel2_ndvi,
            "get_climate_risk":     get_climate_risk,
            "search_cgspace":       search_cgspace,
            "retrieve_rag":         retrieve_rag,
            "generate_pathways":    generate_pathways,
            "get_zone_data":        get_zone_data,
            "narrate_summary":      narrate_summary,
        }
        instance = cls(tools)
        cls._instance = instance
        logger.info("ToolRegistry built with %d tools", len(tools))
        return instance

    # ── Public API ────────────────────────────────────────────────────────────

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def get_schema(self, tool_name: str) -> type | None:
        return INPUT_SCHEMAS.get(tool_name)

    def call(self, tool_name: str, inputs: dict[str, Any]) -> dict:
        """
        Validate inputs against the tool's Pydantic schema, then invoke.
        Raises HTTPException on validation failure (422) or unknown tool (404).
        """
        # 1. Tool exists?
        fn = self._tools.get(tool_name)
        if not fn:
            raise HTTPException(
                404,
                f"Tool '{tool_name}' not found. Available: {self.list_tools()}",
            )

        # 2. Validate inputs against schema
        schema = INPUT_SCHEMAS.get(tool_name)
        if schema is not None:
            try:
                validated = schema(**(inputs or {}))
            except ValidationError as e:
                raise HTTPException(
                    422,
                    {"tool": tool_name, "errors": e.errors()},
                )
            # Use validated values (Pydantic-coerced types)
            call_kwargs = validated.model_dump()
        else:
            # Tool has no schema (should not happen) — fail safe
            raise HTTPException(
                500,
                f"Internal: no schema registered for tool '{tool_name}'",
            )

        # 3. Special handling: narrate_summary accepts dict OR str for context
        if tool_name == "narrate_summary":
            ctx = call_kwargs.get("context")
            if isinstance(ctx, dict):
                import json as _json
                call_kwargs["context"] = _json.dumps(ctx, default=str)

        # 4. Invoke
        try:
            result = fn(**call_kwargs)
        except TypeError as e:
            raise HTTPException(
                422,
                {"tool": tool_name, "error": f"Invalid inputs after validation: {e}"},
            )
        except Exception as e:
            logger.exception("Tool '%s' execution failed", tool_name)
            raise HTTPException(500, f"Tool execution failed: {e}")

        return result
