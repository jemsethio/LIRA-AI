"""
Climate Data router — CMIP6 projections + GARDIAN evidence.
Serves pre-computed CMIP6 data from disk and exposes GARDIAN search.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
import json

from app.data_adapters.cmip6_adapter import (
    fetch_cmip6_scenario, cmip6_to_lira_risk_indicators,
    CMIP6_MODELS, SCENARIOS, OMO_GHIBE_BBOX,
)
from app.data_adapters.gardian_adapter import (
    _cgspace_search, fetch_gardian_datasets,
)

router = APIRouter(prefix="/climate-data", tags=["CMIP6 & Climate Data"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ethiopia" / "omo_ghibe"


def _load(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"{filename} not found — run scripts/prepare_cmip6_gardian.py")
    with open(path) as f:
        return json.load(f)


# ── CMIP6 endpoints ───────────────────────────────────────────────────────────

@router.get("/cmip6/projections", summary="All CMIP6 projections for Omo-Ghibe")
def get_cmip6_projections() -> dict:
    return _load("cmip6_projections.json")


@router.get("/cmip6/risk-indicators", summary="LIRA-AI risk scores from CMIP6")
def get_risk_indicators() -> dict:
    return _load("cmip6_risk_indicators.json")


@router.get("/cmip6/models", summary="Available CMIP6 models and descriptions")
def list_models() -> dict:
    return {
        "models": CMIP6_MODELS,
        "collection": "nasa-nex-gddp-cmip6",
        "catalog": "https://planetarycomputer.microsoft.com/dataset/nasa-nex-gddp-cmip6",
        "pc_examples": "https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets",
        "variables": ["pr (precipitation)", "tas (mean temp)", "tasmax (max temp)",
                      "tasmin (min temp)", "hurs (humidity)", "sfcWind"],
        "scenarios": SCENARIOS,
        "bbox_omo_ghibe": OMO_GHIBE_BBOX,
    }


@router.post("/cmip6/fetch-live", summary="Fetch real CMIP6 data live from Planetary Computer")
def fetch_live_cmip6(
    background_tasks: BackgroundTasks,
    model: str = "MIROC6",
    scenario: str = "ssp245",
    year: int = 2050,
) -> dict:
    """
    Fetch a single CMIP6 year/scenario/model combination live.
    For full multi-model runs, use the background script.
    """
    if model not in CMIP6_MODELS:
        raise HTTPException(400, f"Unknown model. Choose from: {list(CMIP6_MODELS.keys())}")
    if scenario not in ["historical", "ssp245", "ssp585", "ssp126", "ssp370"]:
        raise HTTPException(400, "Unknown scenario")

    result = fetch_cmip6_scenario(scenario, year, [model], verbose=True)
    return {
        "model": model,
        "scenario": scenario,
        "year": year,
        "result": result,
        "source": "nasa-nex-gddp-cmip6 — Microsoft Planetary Computer",
        "catalog": "https://planetarycomputer.microsoft.com/dataset/nasa-nex-gddp-cmip6",
    }


@router.get("/cmip6/summary/{scenario}/{year}", summary="Quick climate risk summary")
def climate_summary(scenario: str, year: int) -> dict:
    """Quick derived risk indicators for a given scenario/year."""
    try:
        data = _load("cmip6_projections.json")
    except HTTPException:
        raise HTTPException(404, "Run scripts/prepare_cmip6_gardian.py first")

    hist = data.get("historical", {})
    proj = data.get("scenarios", {}).get(scenario, {}).get(str(year))
    if not proj:
        raise HTTPException(404, f"No projection for {scenario} {year}")

    risks = cmip6_to_lira_risk_indicators(hist, proj)
    return {
        "scenario": scenario, "year": year,
        "indicators": proj.get("indicators", {}),
        "deltas_vs_historical": proj.get("deltas_vs_historical", {}),
        "lira_ai_risk_scores": risks,
        "ensemble_models": proj.get("model_ensemble", []),
        "is_real": proj.get("is_real", False),
    }


# ── GARDIAN / CGSpace endpoints ───────────────────────────────────────────────

@router.get("/gardian/evidence", summary="CGIAR evidence library from CGSpace")
def get_gardian_evidence() -> dict:
    return _load("gardian_evidence.json")


@router.get("/gardian/search", summary="Live search CGSpace for Ethiopia evidence")
def search_cgspace(
    q: str = "Ethiopia landscape degradation",
    page: int = 0,
    size: int = 10,
) -> dict:
    """
    Live search of CGIAR CGSpace repository.
    Source: https://cgspace.cgiar.org (DSpace 7+ REST API)
    """
    results, total = _cgspace_search(q, page=page, size=size)
    return {
        "query": q,
        "total_results": total,
        "page": page,
        "results": results,
        "source": "CGIAR CGSpace — https://cgspace.cgiar.org",
        "api": "DSpace 7+ REST API",
        "gardian_platform": "https://gardian.bigdata.cgiar.org",
    }


@router.get("/gardian/datasets", summary="CGIAR datasets for Ethiopia")
def get_ethiopia_datasets(keyword: str = "Ethiopia Omo landscape") -> dict:
    return fetch_gardian_datasets(keyword, verbose=False)


@router.get("/sources/verified", summary="Verified data sources status")
def get_sources_verified() -> dict:
    return _load("data_sources_verified.json")
