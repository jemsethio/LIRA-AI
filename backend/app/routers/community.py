from fastapi import APIRouter
from app.models.community import CommunityIntelligence, PolicyAlignment

router = APIRouter(prefix="/community", tags=["Community & Policy"])
_community: dict[str, CommunityIntelligence] = {}
_policy: dict[str, PolicyAlignment] = {}


@router.post("/{project_id}/intelligence", response_model=CommunityIntelligence)
def save_community_intelligence(project_id: str, payload: CommunityIntelligence) -> CommunityIntelligence:
    payload.project_id = project_id
    _community[project_id] = payload
    return payload


@router.get("/{project_id}/intelligence", response_model=CommunityIntelligence)
def get_community_intelligence(project_id: str) -> CommunityIntelligence:
    return _community.get(project_id, CommunityIntelligence(project_id=project_id))


@router.post("/{project_id}/policy", response_model=PolicyAlignment)
def save_policy(project_id: str, payload: PolicyAlignment) -> PolicyAlignment:
    payload.project_id = project_id
    # Compute overall policy score as mean of all sub-scores
    scores = [
        payload.national_restoration_score,
        payload.climate_adaptation_score,
        payload.food_security_score,
        payload.watershed_management_score,
        payload.biodiversity_score,
        payload.land_degradation_neutrality_score,
        payload.carbon_pes_opportunity_score,
        payload.local_development_score,
    ]
    payload.overall_policy_score = round(sum(scores) / len(scores), 3)
    _policy[project_id] = payload
    return payload


@router.get("/{project_id}/policy", response_model=PolicyAlignment)
def get_policy(project_id: str) -> PolicyAlignment:
    return _policy.get(project_id, PolicyAlignment(project_id=project_id))
