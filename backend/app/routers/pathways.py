from fastapi import APIRouter, HTTPException
from app.models.pathways import PathwaySet
from app.models.syndromes import SyndromeDiagnosis
from app.models.climate import ClimateFuturesReport
from app.engines.pathway_generator import generate_pathways
from app.agents.tradeoff_agent import TradeoffMaladaptationAgent, TradeoffReport
from app.models.community import CommunityIntelligence

router = APIRouter(prefix="/pathways", tags=["Regeneration Pathways"])
_agent = TradeoffMaladaptationAgent()
_pathway_sets: dict[str, PathwaySet] = {}
_tradeoff_reports: dict[str, TradeoffReport] = {}


@router.post("/{project_id}/generate", response_model=PathwaySet)
def generate(
    project_id: str,
    syndrome: SyndromeDiagnosis,
    climate: ClimateFuturesReport | None = None,
) -> PathwaySet:
    pathway_set = generate_pathways(syndrome, climate)
    _pathway_sets[project_id] = pathway_set
    return pathway_set


@router.post("/{project_id}/tradeoffs", response_model=TradeoffReport)
def run_tradeoffs(
    project_id: str,
    community: CommunityIntelligence | None = None,
) -> TradeoffReport:
    pathway_set = _pathway_sets.get(project_id)
    if not pathway_set:
        raise HTTPException(status_code=404, detail="Generate pathways first")
    output = _agent.run(
        project_id=project_id,
        pathways=pathway_set.pathways,
        community=community,
        is_mock=pathway_set.is_mock,
    )
    if not output.success:
        raise HTTPException(status_code=500, detail=output.result)
    report: TradeoffReport = output.result
    _tradeoff_reports[project_id] = report
    return report


@router.get("/{project_id}", response_model=PathwaySet)
def get_pathways(project_id: str) -> PathwaySet:
    ps = _pathway_sets.get(project_id)
    if not ps:
        raise HTTPException(status_code=404, detail="No pathways found")
    return ps


@router.get("/{project_id}/tradeoffs", response_model=TradeoffReport)
def get_tradeoffs(project_id: str) -> TradeoffReport:
    tr = _tradeoff_reports.get(project_id)
    if not tr:
        raise HTTPException(status_code=404, detail="No tradeoff report found")
    return tr
