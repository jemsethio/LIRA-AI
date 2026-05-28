from pydantic import BaseModel
from typing import Optional


class InvestmentPassport(BaseModel):
    passport_id: str
    project_id: str
    package_name: str
    target_geography: str
    problem_diagnosis: str
    future_climate_rationale: str
    intervention_components: list[str]
    expected_ecosystem_benefits: list[str]
    expected_livelihood_benefits: list[str]
    beneficiaries: list[str]
    estimated_cost_category: str          # low / medium / high / very_high
    estimated_cost_usd_range: Optional[str] = None  # ASSUMPTION if present
    implementation_partners: list[str]
    community_acceptance_status: str
    policy_alignment: list[str]
    investment_readiness_score: float     # 0–1
    climate_robustness_score: float       # 0–1
    risk_safeguard_notes: list[str]
    maladaptation_alerts: list[str]
    monitoring_indicators: list[str]
    evidence_trail: list[str]
    uncertainty_score: float              # 0=low uncertainty, 1=high
    confidence_score: float              # 0–1
    assumptions: list[str]
    is_mock: bool


class PriorityIndexResult(BaseModel):
    project_id: str
    passport_id: str
    package_name: str
    scores: dict[str, float]             # component scores
    weighted_score: float                # 0–1
    rank: int
    explanation: str
    weight_sensitivity: dict[str, float] # score change per +0.1 weight
    data_gaps: list[str]
