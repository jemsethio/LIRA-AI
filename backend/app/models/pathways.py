from pydantic import BaseModel
from typing import Optional
from enum import Enum


class PathwayType(str, Enum):
    low_cost = "low_cost"
    climate_robust = "climate_robust"
    food_feed_security = "food_feed_security"
    water_sediment_reduction = "water_sediment_reduction"
    biodiversity_carbon = "biodiversity_carbon"
    community_preferred = "community_preferred"
    investment_ready = "investment_ready"


class RestorationOptionCard(BaseModel):
    option_name: str
    target_symptoms: list[str]
    suitable_conditions: list[str]
    unsuitable_conditions: list[str]
    land_use: list[str]
    slope_range: str
    rainfall_range: str
    soil_conditions: list[str]
    required_inputs: list[str]
    labor_requirements: str
    community_requirements: list[str]
    benefits: list[str]
    risks: list[str]
    maladaptation_risks: list[str]
    complementary_options: list[str]
    monitoring_indicators: list[str]
    evidence_sources: list[str]
    confidence_level: str
    is_assumption: bool = False


class RegenerationPathway(BaseModel):
    pathway_type: PathwayType
    diagnosis_summary: str
    target_area: str
    recommended_package: list[RestorationOptionCard]
    why_it_fits: str
    enabling_conditions: list[str]
    cost_category: str          # low / medium / high / very_high
    labor_burden: str           # low / medium / high
    expected_benefits: list[str]
    tradeoffs: list[str]
    maladaptation_risks: list[str]
    policy_alignment: list[str]
    monitoring_indicators: list[str]
    confidence_level: str
    evidence_sources: list[str]
    assumptions: list[str]


class PathwaySet(BaseModel):
    project_id: str
    pathways: list[RegenerationPathway]
    recommended_primary: str    # pathway_type of best fit
    rationale: str
    is_mock: bool
