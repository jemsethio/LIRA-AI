"""
Agents router — exposes all 14 LIRA-AI agents via unified API.
Each agent can be called independently with its required inputs.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.agents.community_agent    import CommunityIntelligenceAgent, CommunityIntelligenceReport
from app.agents.policy_agent       import PolicyAlignmentAgent, PolicyAlignmentReport
from app.agents.investment_agent   import InvestmentPlanningAgent, InvestmentPlanningReport
from app.agents.causal_diagnosis_agent import CausalDiagnosisAgent, CausalDiagnosisReport
from app.models.indicators    import DiagnosticResult, LandscapeIndicators
from app.models.community     import CommunityIntelligence, PolicyAlignment
from app.models.pathways      import PathwaySet
from app.models.climate       import ClimateFuturesReport
from app.engines.indicator_engine import run_indicator_engine

router = APIRouter(prefix="/agents", tags=["Agents"])

_community_agent  = CommunityIntelligenceAgent()
_policy_agent     = PolicyAlignmentAgent()
_investment_agent = InvestmentPlanningAgent()
_causal_agent     = CausalDiagnosisAgent()


# ── Community Intelligence Agent ──────────────────────────────────────────────

class CommunityRequest(BaseModel):
    project_id: str
    community:  Optional[CommunityIntelligence] = None
    diagnostic: Optional[DiagnosticResult]      = None


@router.post("/community-intelligence", response_model=CommunityIntelligenceReport)
def run_community_intelligence(req: CommunityRequest) -> CommunityIntelligenceReport:
    """
    Synthesise community knowledge into equity scores, adoption barriers,
    labor/tenure/conflict risk, and negotiation requirements.
    """
    out = _community_agent.run(
        project_id=req.project_id,
        community=req.community,
        diagnostic=req.diagnostic,
    )
    if not out.success:
        raise HTTPException(500, str(out.result))
    return out.result


# ── Policy Alignment Agent ────────────────────────────────────────────────────

class PolicyRequest(BaseModel):
    project_id:  str
    syndrome_id: str = "mixed_high_risk"
    diagnostic:  Optional[DiagnosticResult] = None
    pathway_set: Optional[PathwaySet]       = None


@router.post("/policy-alignment", response_model=PolicyAlignmentReport)
def run_policy_alignment(req: PolicyRequest) -> PolicyAlignmentReport:
    """
    Score alignment with 10 Ethiopian/CGIAR policy frameworks including
    NDC, NAP, LDN, biodiversity, watershed, carbon/PES targets.
    Generate investment justification and institutional responsibility map.
    """
    out = _policy_agent.run(
        project_id=req.project_id,
        diagnostic=req.diagnostic,
        pathway_set=req.pathway_set,
        syndrome_id=req.syndrome_id,
    )
    if not out.success:
        raise HTTPException(500, str(out.result))
    return out.result


# ── Investment Planning Agent ─────────────────────────────────────────────────

class InvestmentRequest(BaseModel):
    project_id:         str
    package_name:       str = "Integrated Landscape Restoration Package"
    target_geography:   str = "Omo-Ghibe Basin, Ethiopia"
    pathway_components: list[str] = []
    area_ha:            Optional[float] = None
    diagnostic:         Optional[DiagnosticResult]      = None
    climate:            Optional[ClimateFuturesReport]  = None
    community:          Optional[CommunityIntelligence] = None
    policy:             Optional[PolicyAlignment]        = None


@router.post("/investment-planning", response_model=InvestmentPlanningReport)
def run_investment_planning(req: InvestmentRequest) -> InvestmentPlanningReport:
    """
    Generate a full investment portfolio: passport, priority score, GCF/finance
    window screening, cost estimates, co-finance mapping, and MRV framework.
    """
    out = _investment_agent.run(
        project_id=req.project_id,
        package_name=req.package_name,
        target_geography=req.target_geography,
        pathway_components=req.pathway_components,
        area_ha=req.area_ha,
        diagnostic=req.diagnostic,
        climate=req.climate,
        community=req.community,
        policy=req.policy,
    )
    if not out.success:
        raise HTTPException(500, str(out.result))
    return out.result


# ── Causal Diagnosis Agent ────────────────────────────────────────────────────

class CausalRequest(BaseModel):
    project_id: str
    diagnostic: DiagnosticResult


@router.post("/causal-diagnosis", response_model=CausalDiagnosisReport)
def run_causal_diagnosis(req: CausalRequest) -> CausalDiagnosisReport:
    """
    Full causal diagnosis: syndrome + causal graph + driver interactions
    + feedback loops + hotspot/green-spot/transition zone flags + LHII.
    """
    out = _causal_agent.run(
        project_id=req.project_id,
        diagnostic=req.diagnostic,
    )
    if not out.success:
        raise HTTPException(500, str(out.result))
    return out.result


# ── Full pipeline: indicators → causal diagnosis (shortcut) ──────────────────

class FullDiagnosisRequest(BaseModel):
    project_id:  str
    indicators:  LandscapeIndicators
    community:   Optional[CommunityIntelligence] = None


@router.post("/full-diagnosis")
def full_diagnosis(req: FullDiagnosisRequest) -> dict:
    """
    One-call full pipeline:
      Indicators → DiagnosticResult → CausalDiagnosis → CommunityIntelligence → PolicyAlignment
    Returns all four reports.
    """
    # Run indicator engine
    diag = run_indicator_engine(req.indicators)

    # Causal diagnosis
    causal_out = _causal_agent.run(project_id=req.project_id, diagnostic=diag)
    causal = causal_out.result if causal_out.success else None

    # Community intelligence
    comm_out = _community_agent.run(
        project_id=req.project_id,
        community=req.community,
        diagnostic=diag,
    )
    community = comm_out.result if comm_out.success else None

    # Policy alignment (syndrome from causal)
    syndrome_id = causal.primary_syndrome.lower().replace(" ","_") if causal else "mixed_high_risk"
    pol_out = _policy_agent.run(
        project_id=req.project_id,
        diagnostic=diag,
        syndrome_id=syndrome_id,
    )
    policy = pol_out.result if pol_out.success else None

    return {
        "project_id":           req.project_id,
        "diagnostic":           diag.model_dump(),
        "causal_diagnosis":     causal.model_dump() if causal else None,
        "community_intelligence":community.model_dump() if community else None,
        "policy_alignment":     policy.model_dump() if policy else None,
    }


# ── Agent status / registry ───────────────────────────────────────────────────

@router.get("/registry")
def list_agents() -> dict:
    """List all 14 LIRA-AI agents with their status and endpoints."""
    return {
        "total_agents": 14,
        "agents": [
            {"name":"LandscapeEvidenceAgent",    "status":"complete","endpoint":"/evidence/fetch"},
            {"name":"ClimateFuturesAgent",       "status":"complete","endpoint":"/climate/{id}"},
            {"name":"CausalDiagnosisAgent",      "status":"complete","endpoint":"/agents/causal-diagnosis"},
            {"name":"SoilDoctorAgent",           "status":"complete","endpoint":"/evidence/specialist-reports/{id}"},
            {"name":"WaterDoctorAgent",          "status":"complete","endpoint":"/evidence/specialist-reports/{id}"},
            {"name":"VegetationBiodiversityAgent","status":"complete","endpoint":"/evidence/specialist-reports/{id}"},
            {"name":"AgronomyAgent",             "status":"complete","endpoint":"/agronomy/{id}"},
            {"name":"RangelandLivestockAgent",   "status":"complete","endpoint":"/evidence/specialist-reports/{id}"},
            {"name":"CommunityIntelligenceAgent","status":"complete","endpoint":"/agents/community-intelligence"},
            {"name":"PolicyAlignmentAgent",      "status":"complete","endpoint":"/agents/policy-alignment"},
            {"name":"TradeoffMaladaptationAgent","status":"complete","endpoint":"/pathways/{id}/tradeoffs"},
            {"name":"InvestmentPlanningAgent",   "status":"complete","endpoint":"/agents/investment-planning"},
            {"name":"AdaptiveMonitoringAgent",   "status":"complete","endpoint":"/monitoring/run/{id}"},
            {"name":"AdvisoryCommunicationAgent","status":"complete","endpoint":"/advisory/{id}"},
        ],
    }
