"""
MCP Tool Schemas — LIRA-AI
============================
Pydantic input schemas per MCP tool.
Used by the ToolRegistry to validate /mcp/call request bodies BEFORE
spreading them into the tool function (eliminates **kwargs DoS attack
surface from the legacy unchecked `fn(**req.inputs)` pattern).

Backwards-compat:
  - All field names match the existing MCP tool parameter names verbatim.
  - Defaults match what was in app/mcp/server.py.
  - narrate_summary accepts BOTH dict and str for `context` (transition).
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Union


# ── Tool 1: diagnose_landscape ────────────────────────────────────────────────

class DiagnoseLandscapeInput(BaseModel):
    project_id: str
    soil_loss_rate_t_ha_yr:       Optional[float] = None
    soil_moisture_pct:            Optional[float] = None
    soil_organic_carbon_g_per_kg: Optional[float] = None
    land_productivity_index:      Optional[float] = None
    ndvi_mean:                    Optional[float] = None
    slope_mean_degrees:           Optional[float] = None
    rainfall_mm_annual:           Optional[float] = None
    overgrazing_proxy:            Optional[float] = None
    is_mock: bool = False


# ── Tool 2: compute_rusle ─────────────────────────────────────────────────────

class ComputeRusleInput(BaseModel):
    rainfall_mm:      float = Field(..., ge=0, le=10000)
    slope_deg:        float = Field(..., ge=0, le=90)
    ndvi:             float = Field(..., ge=-1, le=1)
    soil_texture:     str   = "clay-loam"
    soc_g_per_kg:     float = Field(20.0, ge=0, le=200)
    forest_cover_pct: float = Field(0.0, ge=0, le=100)


# ── Tool 3: fetch_soilgrids ───────────────────────────────────────────────────

class FetchSoilgridsInput(BaseModel):
    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)


# ── Tool 4: fetch_sentinel2_ndvi ──────────────────────────────────────────────

class FetchSentinel2Input(BaseModel):
    west:  float = Field(..., ge=-180, le=180)
    south: float = Field(..., ge=-90,  le=90)
    east:  float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90,  le=90)
    date_range: str = "2022-06-01/2023-10-31"


# ── Tool 5: get_climate_risk ──────────────────────────────────────────────────

class GetClimateRiskInput(BaseModel):
    scenario: str   = "ssp245"
    horizon:  int   = Field(2050, ge=2020, le=2100)
    model:    str   = "MIROC6"
    west:     float = 33.0
    south:    float =  3.0
    east:     float = 42.0
    north:    float = 10.0


# ── Tool 6: search_cgspace ────────────────────────────────────────────────────

class SearchCgspaceInput(BaseModel):
    query:     str = Field(..., min_length=2, max_length=400)
    n_results: int = Field(8, ge=1, le=50)


# ── Tool 7: retrieve_rag ──────────────────────────────────────────────────────

class RetrieveRagInput(BaseModel):
    project_id: str
    query:      str = Field(..., min_length=2, max_length=400)
    n_results:  int = Field(5, ge=1, le=50)


# ── Tool 8: generate_pathways ─────────────────────────────────────────────────

class GeneratePathwaysInput(BaseModel):
    project_id:           str
    primary_syndrome:     str
    degradation_severity: str = "moderate"


# ── Tool 9: get_zone_data ─────────────────────────────────────────────────────

class GetZoneDataInput(BaseModel):
    zone_id: str = Field(..., pattern=r"^(highland|midland|lowland_pastoral|riverine)$")


# ── Tool 10: narrate_summary ──────────────────────────────────────────────────

class NarrateSummaryInput(BaseModel):
    """
    BACKWARDS-COMPATIBLE: accepts BOTH dict and str for `context`.
    - Old MCP clients pass stringified JSON (still works).
    - New clients pass dict directly (preferred).
    """
    narrative_type: str = Field(..., pattern=r"^(syndrome|climate|pathway|tradeoffs|investment|monitoring|lhii|agronomy|advisory|comparison)$")
    context:        Union[dict, str]


# ── Registry mapping ──────────────────────────────────────────────────────────

INPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "diagnose_landscape":   DiagnoseLandscapeInput,
    "compute_rusle":        ComputeRusleInput,
    "fetch_soilgrids":      FetchSoilgridsInput,
    "fetch_sentinel2_ndvi": FetchSentinel2Input,
    "get_climate_risk":     GetClimateRiskInput,
    "search_cgspace":       SearchCgspaceInput,
    "retrieve_rag":         RetrieveRagInput,
    "generate_pathways":    GeneratePathwaysInput,
    "get_zone_data":        GetZoneDataInput,
    "narrate_summary":      NarrateSummaryInput,
}
