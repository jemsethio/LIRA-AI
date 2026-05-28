from pydantic import BaseModel
from typing import Optional


class CommunityIntelligence(BaseModel):
    project_id: str
    community_preferred_future: Optional[str] = None
    local_degradation_memory: Optional[str] = None
    grazing_rules: Optional[str] = None
    labor_constraints: Optional[str] = None
    gendered_burdens: Optional[str] = None
    youth_opportunities: Optional[str] = None
    local_conflict_risks: Optional[str] = None
    tenure_constraints: Optional[str] = None
    restoration_preferences: list[str] = []
    adoption_barriers: list[str] = []
    local_success_indicators: list[str] = []
    notes: Optional[str] = None


class PolicyAlignment(BaseModel):
    project_id: str
    national_restoration_score: float = 0.0   # 0–1
    climate_adaptation_score: float = 0.0
    food_security_score: float = 0.0
    watershed_management_score: float = 0.0
    biodiversity_score: float = 0.0
    land_degradation_neutrality_score: float = 0.0
    carbon_pes_opportunity_score: float = 0.0
    local_development_score: float = 0.0
    overall_policy_score: float = 0.0
    aligned_policies: list[str] = []
    misaligned_risks: list[str] = []
    evidence_sources: list[str] = []
    is_mock: bool = True
