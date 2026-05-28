"""Agronomy Agent router."""
from fastapi import APIRouter, HTTPException
from app.agents.agronomy_agent import AgronomyAgent, AgronomyReport
from app.models.indicators import DiagnosticResult

router = APIRouter(prefix="/agronomy", tags=["Agronomy"])
_agent = AgronomyAgent()
_reports: dict[str, AgronomyReport] = {}


@router.post("/{project_id}", response_model=AgronomyReport)
def run_agronomy(
    project_id: str,
    diagnostic: DiagnosticResult,
    soil_texture: str = "clay-loam",
) -> AgronomyReport:
    output = _agent.run(project_id=project_id, diagnostic=diagnostic, soil_texture=soil_texture)
    if not output.success:
        raise HTTPException(500, str(output.result))
    report: AgronomyReport = output.result
    _reports[project_id] = report
    return report


@router.get("/{project_id}", response_model=AgronomyReport)
def get_agronomy(project_id: str) -> AgronomyReport:
    r = _reports.get(project_id)
    if not r:
        raise HTTPException(404, "No agronomy report — run POST first")
    return r
