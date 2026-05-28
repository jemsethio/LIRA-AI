from pydantic import BaseModel
from typing import Optional


class SyndromeMatch(BaseModel):
    syndrome_id: str
    name: str
    risk_level: str
    confidence: str
    triggering_indicators: list[str]
    main_symptoms: list[str]
    likely_drivers: list[str]
    data_gaps: list[str] = []
    suggested_validation: list[str] = []
    match_score: float  # 0–1


class SyndromeDiagnosis(BaseModel):
    project_id: str
    primary_syndrome: SyndromeMatch
    secondary_syndromes: list[SyndromeMatch]
    all_syndromes: list[SyndromeMatch]
    causal_narrative: str  # LLM or template-based
    assumptions: list[str]
    needs_validation: list[str]
    is_mock: bool
