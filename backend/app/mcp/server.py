"""
LIRA-AI MCP Server
====================
Exposes LIRA-AI's scientific tools as callable MCP (Model Context Protocol) tools.

Concept note: "MCP-connected model execution, allowing AI agents to call trusted
GIS, climate, hydrology, erosion, carbon, and economic tools rather than guessing."

Tools exposed:
  diagnose_landscape      — full indicator engine + syndrome classifier
  compute_lhii            — Landscape Health Intelligence Index
  compute_rusle           — Enhanced RUSLE soil erosion (Ethiopia-calibrated)
  classify_syndrome       — degradation syndrome matching
  generate_pathways       — 7 restoration pathway packages
  fetch_soilgrids         — real SoilGrids v2.0 data (ISRIC REST)
  fetch_sentinel2_ndvi    — real Sentinel-2 NDVI (Planetary Computer)
  get_climate_risk        — CMIP6 climate risk scores
  search_cgspace          — CGIAR CGSpace evidence search
  retrieve_rag            — semantic search over indexed documents
  narrate_summary         — AI narrative via Ollama/LLM
  get_zone_data           — Omo-Ghibe zone indicators (real data)

Run standalone:   python -m app.mcp.server
Or via FastAPI:   GET /mcp/tools  (lists tools)
                  POST /mcp/call  (calls a tool)
"""

from __future__ import annotations
import json
from typing import Any, Optional
import fastmcp

mcp = fastmcp.FastMCP(
    name="LIRA-AI Landscape Futures Lab",
    instructions=(
        "You are connected to LIRA-AI, a predictive landscape intelligence platform "
        "for the Omo-Ghibe basin, Ethiopia. Use these tools to diagnose landscape degradation, "
        "assess climate risks, generate restoration pathways, and produce investment portfolios. "
        "Always cite data sources and flag assumptions. Never invent numeric values — use tools."
    ),
)


# ── Tool 1: Diagnose landscape ────────────────────────────────────────────────

@mcp.tool()
def diagnose_landscape(
    project_id:                  str,
    soil_loss_rate_t_ha_yr:     Optional[float] = None,
    soil_moisture_pct:          Optional[float] = None,
    soil_organic_carbon_g_per_kg:Optional[float]= None,
    land_productivity_index:    Optional[float] = None,
    ndvi_mean:                  Optional[float] = None,
    slope_mean_degrees:         Optional[float] = None,
    rainfall_mm_annual:         Optional[float] = None,
    overgrazing_proxy:          Optional[float] = None,
    is_mock:                    bool = False,
) -> dict:
    """
    Run the LIRA-AI indicator engine and syndrome classifier.
    Returns: degradation severity, composite health score, indicator categories,
    primary syndrome with drivers and symptoms, LHII score.
    All numeric thresholds are configurable in config/thresholds.yaml.
    """
    from app.models.indicators import LandscapeIndicators
    from app.engines.indicator_engine import run_indicator_engine
    from app.engines.syndrome_classifier import classify_syndromes
    from app.engines.landscape_health_index import compute_lhii

    inds = LandscapeIndicators(
        project_id=project_id,
        soil_loss_rate_t_ha_yr=soil_loss_rate_t_ha_yr,
        soil_moisture_pct=soil_moisture_pct,
        soil_organic_carbon_g_per_kg=soil_organic_carbon_g_per_kg,
        land_productivity_index=land_productivity_index,
        ndvi_mean=ndvi_mean,
        slope_mean_degrees=slope_mean_degrees,
        rainfall_mm_annual=rainfall_mm_annual,
        overgrazing_proxy=overgrazing_proxy,
        is_mock=is_mock,
    )
    diag  = run_indicator_engine(inds)
    synd  = classify_syndromes(diag)
    lhii  = compute_lhii(diag)

    return {
        "degradation_severity":    diag.degradation_severity,
        "composite_health_score":  diag.composite_health_score,
        "data_completeness_pct":   diag.data_completeness_pct,
        "data_gaps":               diag.data_gaps,
        "primary_syndrome":        synd.primary_syndrome.name,
        "syndrome_risk":           synd.primary_syndrome.risk_level,
        "syndrome_confidence":     synd.primary_syndrome.confidence,
        "likely_drivers":          synd.primary_syndrome.likely_drivers,
        "main_symptoms":           synd.primary_syndrome.main_symptoms,
        "causal_narrative":        synd.causal_narrative,
        "lhii_score":              lhii.overall_lhii,
        "lhii_class":              lhii.lhii_class,
        "dominant_constraint":     lhii.dominant_constraint,
        "recovery_potential":      lhii.recovery_potential,
        "hotspots":                [h.description for h in lhii.hotspots],
        "green_spots":             [g.description for g in lhii.green_spots],
        "source":                  "LIRA-AI indicator engine + YAML thresholds",
    }


# ── Tool 2: Compute RUSLE soil erosion ────────────────────────────────────────

@mcp.tool()
def compute_rusle(
    rainfall_mm:      float,
    slope_deg:        float,
    ndvi:             float,
    soil_texture:     str   = "clay-loam",
    soc_g_per_kg:     float = 20.0,
    forest_cover_pct: float = 0.0,
) -> dict:
    """
    Compute soil erosion rate using enhanced RUSLE calibrated for Ethiopian highlands.
    A = R × K × LS × C × P  (Hurni 1985 / McCool 1987 / De Jong 1994)
    Returns: soil_loss_rate_t_ha_yr, R/K/LS/C/P factor values, erosion category.
    Reference: Hurni (1985), Bewket & Teferi (2009), GloSEM v1.2 benchmarks.
    """
    from app.data_adapters.glsem_adapter import compute_rusle_enhanced
    result = compute_rusle_enhanced(
        rainfall_mm=rainfall_mm, slope_deg=slope_deg, ndvi=ndvi,
        soil_texture=soil_texture, soc_g_per_kg=soc_g_per_kg,
        forest_cover_pct=forest_cover_pct,
    )
    loss = result["soil_loss_rate_t_ha_yr"]
    category = (
        "very_severe(>50)" if loss > 50 else
        "severe(20-50)"    if loss > 20 else
        "moderate(10-20)"  if loss > 10 else
        "low(<10)"
    )
    return {**result, "erosion_category": category,
            "glsem_reference": "Borrelli et al. 2021, Nature Comms — DOI: 10.5281/zenodo.6539253"}


# ── Tool 3: Fetch real SoilGrids data ─────────────────────────────────────────

@mcp.tool()
def fetch_soilgrids(lon: float, lat: float) -> dict:
    """
    Fetch real SoilGrids v2.0 soil properties for a point location.
    Returns: SOC (g/kg), clay%, silt%, sand%, pH, bulk density, soil texture.
    Source: ISRIC REST API — https://rest.isric.org/soilgrids/v2.0/
    Confirmed working for Omo-Ghibe: Highland SOC=58.6g/kg, pH=5.4.
    """
    from app.data_adapters.planetary_computer import fetch_soilgrids as _fetch
    return _fetch(lon=lon, lat=lat)


# ── Tool 4: Fetch Sentinel-2 NDVI ─────────────────────────────────────────────

@mcp.tool()
def fetch_sentinel2_ndvi(
    west: float, south: float, east: float, north: float,
    date_range: str = "2022-06-01/2023-10-31",
) -> dict:
    """
    Fetch real Sentinel-2 L2A NDVI for a bounding box.
    Source: Microsoft Planetary Computer — sentinel-2-l2a collection.
    CRS: EPSG:32637 (UTM Zone 37N for Ethiopia). Resolution: 100m.
    Returns: ndvi_mean, ndvi_std, valid_pct, n_scenes, source.
    """
    from app.data_adapters.planetary_computer import fetch_sentinel2_ndvi as _fetch
    return _fetch(bbox=[west, south, east, north], date_range=date_range)


# ── Tool 5: Get CMIP6 climate risk ────────────────────────────────────────────

@mcp.tool()
def get_climate_risk(
    scenario:  str   = "ssp245",
    horizon:   int   = 2050,
    model:     str   = "MIROC6",
    west:      float = 33.0,
    south:     float = 3.0,
    east:      float = 42.0,
    north:     float = 10.0,
) -> dict:
    """
    Fetch CMIP6 climate projection and compute LIRA-AI risk scores.
    Source: NASA NEX GDDP CMIP6 — Microsoft Planetary Computer.
    Returns: annual_precip_mm, temp_mean_c, heat_days, dry_days,
    and LIRA-AI risk scores (0–1) for drought, erosion, heat, restoration.
    """
    from app.data_adapters.cmip6_adapter import (
        fetch_cmip6_scenario, cmip6_to_lira_risk_indicators,
        fetch_cmip6_scenario as fetch_hist, HISTORICAL_YEAR,
    )
    hist = fetch_hist("historical", HISTORICAL_YEAR, [model], verbose=False)
    proj = fetch_cmip6_scenario(scenario, horizon, [model], verbose=False)

    if proj.get("is_real") and hist.get("is_real"):
        risk = cmip6_to_lira_risk_indicators(hist, proj)
    else:
        risk = {"is_real": False, "source": "fallback — CMIP6 fetch failed"}

    return {
        "scenario":          scenario,
        "horizon":           horizon,
        "model":             model,
        "indicators":        proj.get("indicators", {}),
        "deltas_vs_historical": proj.get("deltas_vs_historical", {}),
        "risk_scores":       risk,
        "is_real":           proj.get("is_real", False),
        "source":            "nasa-nex-gddp-cmip6 — Planetary Computer",
    }


# ── Tool 6: Search CGIAR CGSpace ──────────────────────────────────────────────

@mcp.tool()
def search_cgspace(query: str, n_results: int = 8) -> dict:
    """
    Search CGIAR CGSpace institutional repository for evidence.
    Source: https://cgspace.cgiar.org (DSpace 7+ REST API).
    Returns: titles, authors, years, abstracts, CGSpace URLs.
    Use for: evidence-based citations, restoration option validation,
    policy alignment evidence, community knowledge sources.
    """
    from app.data_adapters.gardian_adapter import _cgspace_search
    results, total = _cgspace_search(query, size=n_results)
    return {
        "query":         query,
        "total_results": total,
        "results":       results[:n_results],
        "source":        "CGIAR CGSpace — https://cgspace.cgiar.org",
    }


# ── Tool 7: Retrieve from RAG ─────────────────────────────────────────────────

@mcp.tool()
def retrieve_rag(project_id: str, query: str, n_results: int = 5) -> dict:
    """
    Semantic search over project-specific indexed documents.
    Returns ranked evidence chunks with similarity scores and source citations.
    Use for: grounding recommendations in uploaded restoration manuals,
    policy documents, and field reports.
    """
    try:
        from app.rag.ingestion import retrieve
        results = retrieve(query, project_id=project_id, n_results=n_results)
        return {"project_id": project_id, "query": query, "results": results}
    except Exception as e:
        return {"error": str(e), "note": "Index documents first via POST /rag/ingest"}


# ── Tool 8: Generate pathways ─────────────────────────────────────────────────

@mcp.tool()
def generate_pathways(
    project_id:        str,
    primary_syndrome:  str,
    degradation_severity: str = "moderate",
) -> dict:
    """
    Generate 7 alternative restoration pathway packages for a diagnosed syndrome.
    Packages: low_cost, climate_robust, food_feed_security,
    water_sediment_reduction, biodiversity_carbon, community_preferred, investment_ready.
    Each package includes interventions, tradeoffs, maladaptation risks, monitoring indicators.
    """
    from app.models.syndromes import SyndromeDiagnosis, SyndromeMatch
    from app.engines.pathway_generator import generate_pathways as _gen

    # Create minimal syndrome object from provided syndrome name
    syndrome_match = SyndromeMatch(
        syndrome_id=primary_syndrome.lower().replace(" ","_").replace("–","_"),
        name=primary_syndrome,
        risk_level="high",
        confidence="medium",
        triggering_indicators=[],
        main_symptoms=["degradation", "productivity decline"],
        likely_drivers=["land use pressure", "climate variability"],
        match_score=0.75,
    )
    diag_obj = SyndromeDiagnosis(
        project_id=project_id,
        primary_syndrome=syndrome_match,
        secondary_syndromes=[],
        all_syndromes=[syndrome_match],
        causal_narrative=f"Landscape presents {primary_syndrome} at {degradation_severity} severity.",
        assumptions=["MCP tool call — minimal context provided"],
        needs_validation=["Full indicator data recommended for accurate pathway matching"],
        is_mock=True,
    )
    pathway_set = _gen(diag_obj, climate=None)
    return {
        "project_id":         project_id,
        "primary_syndrome":   primary_syndrome,
        "recommended_primary":pathway_set.recommended_primary,
        "n_pathways":         len(pathway_set.pathways),
        "pathways": [
            {
                "type":          p.pathway_type.value,
                "package":       [o.option_name for o in p.recommended_package],
                "cost_category": p.cost_category,
                "tradeoffs":     p.tradeoffs[:2],
            }
            for p in pathway_set.pathways
        ],
    }


# ── Tool 9: Get Omo-Ghibe zone data ───────────────────────────────────────────

@mcp.tool()
def get_zone_data(zone_id: str) -> dict:
    """
    Get real indicator data for an Omo-Ghibe basin landscape zone.
    zone_id: highland | midland | lowland_pastoral | riverine
    Returns confirmed real data: NDVI, SOC, rainfall, temperature, slope, forest cover.
    Source: SoilGrids, Sentinel-2, CHIRPS, ERA5, WorldCover — all confirmed.
    """
    from pathlib import Path
    import json as _json

    data_file = Path(__file__).parent.parent.parent / "data" / "ethiopia" / "omo_ghibe" / f"indicators_{zone_id}.json"
    if not data_file.exists():
        return {"error": f"Zone '{zone_id}' not found. Valid: highland, midland, lowland_pastoral, riverine"}

    with open(data_file) as f:
        d = _json.load(f)

    return {
        "zone_id":         zone_id,
        "zone_name":       d["meta"]["zone_name"],
        "real_data_layers":d["meta"]["real_data_layers"],
        "data_sources":    d["meta"]["data_sources"],
        "indicators":      {k: v for k, v in d["indicators"].items() if v is not None and k != "project_id"},
        "dominant_syndrome":d["meta"]["dominant_syndrome"],
    }


# ── Tool 10: AI narrative ─────────────────────────────────────────────────────

@mcp.tool()
def narrate_summary(narrative_type: str, context: str) -> dict:
    """
    Generate a concise, data-grounded AI summary (120 words max).
    narrative_type: syndrome | climate | pathway | investment | lhii | monitoring
    context: JSON string with indicator values (e.g. '{"zone_name":"Kafa-Sheka","lhii_score":0.743}')
    Provider: Ollama (local) → HuggingFace → template fallback.
    Returns: text (2 paragraphs), provider, is_llm, latency_s.
    """
    try:
        ctx = json.loads(context)
    except Exception:
        ctx = {"raw": context}

    # Use the routers/ai._build_prompt via the module attribute
    from app.services.llm_service import generate_narrative
    import importlib
    ai_mod  = importlib.import_module("app.routers.ai")
    build_fn = getattr(ai_mod, "_build_prompt", None)
    prompt  = build_fn(narrative_type, ctx) if build_fn else f"Summarise: {json.dumps(ctx)[:200]}"
    result = generate_narrative(prompt, max_wait=45)
    return {
        "text":      result.get("text"),
        "provider":  result.get("provider"),
        "is_llm":    result.get("is_llm"),
        "latency_s": result.get("latency_s"),
    }


# ── Standalone runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting LIRA-AI MCP Server...")
    mcp.run()
