from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.investment import InvestmentPassport, PriorityIndexResult
from app.models.indicators import DiagnosticResult
from app.models.climate import ClimateFuturesReport
from app.models.community import CommunityIntelligence, PolicyAlignment
from app.engines.priority_index import generate_investment_passport, calculate_priority_index

router = APIRouter(prefix="/investment", tags=["Investment Passports"])
_passports: dict[str, InvestmentPassport] = {}
_priority_results: dict[str, PriorityIndexResult] = {}


class PassportRequest(BaseModel):
    package_name: str
    target_geography: str
    pathway_components: list[str]
    diagnostic: DiagnosticResult
    climate: ClimateFuturesReport | None = None
    community: CommunityIntelligence | None = None
    policy: PolicyAlignment | None = None


@router.post("/{project_id}/passport", response_model=InvestmentPassport)
def create_passport(project_id: str, req: PassportRequest) -> InvestmentPassport:
    passport = generate_investment_passport(
        project_id=project_id,
        package_name=req.package_name,
        target_geography=req.target_geography,
        diagnostic=req.diagnostic,
        climate=req.climate,
        community=req.community,
        policy=req.policy,
        pathway_components=req.pathway_components,
    )
    _passports[passport.passport_id] = passport
    return passport


@router.post("/{project_id}/priority-index/{passport_id}", response_model=PriorityIndexResult)
def run_priority_index(
    project_id: str,
    passport_id: str,
    diagnostic: DiagnosticResult,
    climate: ClimateFuturesReport | None = None,
    community: CommunityIntelligence | None = None,
    policy: PolicyAlignment | None = None,
) -> PriorityIndexResult:
    passport = _passports.get(passport_id)
    if not passport:
        raise HTTPException(status_code=404, detail="Passport not found")
    result = calculate_priority_index(passport, diagnostic, climate, community, policy)
    _priority_results[passport_id] = result
    return result


@router.get("/{project_id}/passports", response_model=list[InvestmentPassport])
def list_passports(project_id: str) -> list[InvestmentPassport]:
    return [p for p in _passports.values() if p.project_id == project_id]


@router.get("/{project_id}/priority-index", response_model=list[PriorityIndexResult])
def list_priority_results(project_id: str) -> list[PriorityIndexResult]:
    return [r for r in _priority_results.values() if r.project_id == project_id]
