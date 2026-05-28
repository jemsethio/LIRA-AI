"""
Adaptive Monitoring & MELIA router.
Tracks recovery, triggers re-prescription alerts, and produces MELIA reports.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.agents.adaptive_monitoring_agent import AdaptiveMonitoringAgent, AdaptiveMonitoringReport
from app.engines.melia import generate_melia_report, MELIAReport
from app.engines.landscape_health_index import compute_lhii, LandscapeHealthIndex
from app.models.indicators import DiagnosticResult
from app.models.climate import ClimateFuturesReport
from app.models.community import CommunityIntelligence

router = APIRouter(prefix="/monitoring", tags=["Adaptive Monitoring & MELIA"])

_monitoring_agent = AdaptiveMonitoringAgent()
_monitoring_reports: dict[str, AdaptiveMonitoringReport] = {}
_melia_reports: dict[str, MELIAReport] = {}
_lhii_results: dict[str, LandscapeHealthIndex] = {}


class MonitoringRequest(BaseModel):
    project_id: str
    bbox: list[float]
    baseline_date_range: str = "2020-01-01/2021-01-01"
    current_date_range: str = "2023-01-01/2024-01-01"
    predicted_recovery_ndvi: Optional[float] = None
    community_acceptance_score: Optional[float] = None


class MELIARequest(BaseModel):
    project_id: str
    syndromes_classified: int = 0
    pathways_generated: int = 0
    passports_created: int = 0
    community_score: Optional[float] = None
    field_validation_done: bool = False
    policy_briefs_generated: int = 0
    re_prescriptions: int = 0


class LHIIRequest(BaseModel):
    diagnostic: dict
    climate: Optional[dict] = None
    community: Optional[dict] = None


@router.post("/run/{project_id}", response_model=AdaptiveMonitoringReport)
def run_monitoring(project_id: str, req: MonitoringRequest) -> AdaptiveMonitoringReport:
    output = _monitoring_agent.run(
        project_id=project_id,
        bbox=req.bbox,
        baseline_date_range=req.baseline_date_range,
        current_date_range=req.current_date_range,
        predicted_recovery_ndvi=req.predicted_recovery_ndvi,
        community_score=req.community_acceptance_score,
    )
    if not output.success:
        raise HTTPException(status_code=500, detail=str(output.result))
    report: AdaptiveMonitoringReport = output.result
    _monitoring_reports[project_id] = report
    return report


@router.get("/report/{project_id}", response_model=AdaptiveMonitoringReport)
def get_monitoring_report(project_id: str) -> AdaptiveMonitoringReport:
    r = _monitoring_reports.get(project_id)
    if not r:
        raise HTTPException(status_code=404, detail="No monitoring report — run POST first")
    return r


@router.post("/melia/{project_id}", response_model=MELIAReport)
def generate_melia(project_id: str, req: MELIARequest) -> MELIAReport:
    report = generate_melia_report(
        project_id=project_id,
        syndromes_classified=req.syndromes_classified,
        pathways_generated=req.pathways_generated,
        passports_created=req.passports_created,
        community_score=req.community_score,
        field_validation_done=req.field_validation_done,
        policy_briefs_generated=req.policy_briefs_generated,
        re_prescriptions=req.re_prescriptions,
    )
    _melia_reports[project_id] = report
    return report


@router.get("/melia/{project_id}", response_model=MELIAReport)
def get_melia(project_id: str) -> MELIAReport:
    r = _melia_reports.get(project_id)
    if not r:
        raise HTTPException(status_code=404, detail="No MELIA report generated yet")
    return r


@router.post("/lhii/{project_id}", response_model=LandscapeHealthIndex)
def compute_landscape_health(project_id: str, req: LHIIRequest) -> LandscapeHealthIndex:
    try:
        diagnostic = DiagnosticResult(**req.diagnostic)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid diagnostic: {e}")

    climate  = ClimateFuturesReport(**req.climate)  if req.climate  else None
    community = CommunityIntelligence(**req.community) if req.community else None

    lhii = compute_lhii(diagnostic, climate, community)
    _lhii_results[project_id] = lhii
    return lhii


@router.get("/lhii/{project_id}", response_model=LandscapeHealthIndex)
def get_lhii(project_id: str) -> LandscapeHealthIndex:
    r = _lhii_results.get(project_id)
    if not r:
        raise HTTPException(status_code=404, detail="No LHII computed — run POST first")
    return r
