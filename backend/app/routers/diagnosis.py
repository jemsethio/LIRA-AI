import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.models.indicators import LandscapeIndicators, DiagnosticResult
from app.models.syndromes import SyndromeDiagnosis
from app.engines.indicator_engine import run_indicator_engine
from app.engines.syndrome_classifier import classify_syndromes
from app.engines.causal_graph import build_causal_graph

router = APIRouter(prefix="/diagnosis", tags=["Diagnosis"])

_diagnostics: dict[str, DiagnosticResult] = {}
_syndromes: dict[str, SyndromeDiagnosis] = {}

_ZONE_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ethiopia" / "omo_ghibe"
_VALID_ZONES = {"highland", "midland", "lowland_pastoral", "riverine"}


@router.post("/indicators", response_model=DiagnosticResult)
def run_diagnosis(indicators: LandscapeIndicators) -> DiagnosticResult:
    result = run_indicator_engine(indicators)
    _diagnostics[indicators.project_id] = result
    return result


@router.post("/syndromes/{project_id}", response_model=SyndromeDiagnosis)
def classify(project_id: str) -> SyndromeDiagnosis:
    diagnostic = _diagnostics.get(project_id)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Run indicator diagnosis first")
    syndrome = classify_syndromes(diagnostic)
    _syndromes[project_id] = syndrome
    return syndrome


@router.get("/causal-graph/{project_id}")
def get_causal_graph(project_id: str) -> dict:
    syndrome = _syndromes.get(project_id)
    if not syndrome:
        raise HTTPException(status_code=404, detail="Run syndrome classification first")
    return build_causal_graph(syndrome)


@router.get("/indicators/{project_id}", response_model=DiagnosticResult)
def get_diagnostic(project_id: str) -> DiagnosticResult:
    result = _diagnostics.get(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="No diagnostic found")
    return result


@router.get("/syndromes/{project_id}", response_model=SyndromeDiagnosis)
def get_syndrome(project_id: str) -> SyndromeDiagnosis:
    syndrome = _syndromes.get(project_id)
    if not syndrome:
        raise HTTPException(status_code=404, detail="No syndrome classification found")
    return syndrome


@router.post("/bootstrap/{zone_id}", response_model=SyndromeDiagnosis)
def bootstrap_from_zone(zone_id: str) -> SyndromeDiagnosis:
    """Run the full diagnosis pipeline from pre-loaded Omo-Ghibe zone data.
    No project creation needed — uses real Sentinel-2/SoilGrids/CHIRPS indicators.
    Returns SyndromeDiagnosis and caches it as project_id=omo-ghibe-{zone_id}.
    """
    if zone_id not in _VALID_ZONES:
        raise HTTPException(status_code=404, detail=f"Zone must be one of {sorted(_VALID_ZONES)}")
    f = _ZONE_DATA_DIR / f"indicators_{zone_id}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail=f"Zone data file not found: {f.name}")
    with open(f) as fp:
        data = json.load(fp)
    inds = data["indicators"]
    project_id = str(inds.get("project_id") or f"omo-ghibe-{zone_id}")
    li = LandscapeIndicators(**inds)
    result = run_indicator_engine(li)
    _diagnostics[project_id] = result
    syndrome = classify_syndromes(result)
    _syndromes[project_id] = syndrome
    return syndrome
