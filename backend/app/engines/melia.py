"""
MELIA — Monitoring, Evaluation, Learning and Impact Assessment framework.
Tracks research quality, practical decision impact, and adaptive learning
as specified in the concept note Section 18.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class MELIAIndicator(BaseModel):
    result_area: str
    indicator: str
    target: str
    current_value: Optional[str | float] = None
    status: str                # on_track / lagging / not_started / exceeded
    data_source: str
    last_updated: str


class LearningRecord(BaseModel):
    date: str
    finding: str
    source: str               # field_validation / monitoring / expert_review / community
    action_taken: str
    rule_updated: bool


class MELIAReport(BaseModel):
    project_id: str
    reporting_period: str
    indicators: list[MELIAIndicator]
    learning_records: list[LearningRecord]
    overall_progress: str     # on_track / partial / lagging
    diagnosis_accuracy: Optional[float] = None
    restoration_validation_pct: Optional[float] = None
    policy_decisions_informed: int = 0
    investment_portfolios_generated: int = 0
    community_legitimacy_score: Optional[float] = None
    rules_updated_count: int = 0
    re_prescriptions_triggered: int = 0
    summary: str
    next_review_date: str


def generate_melia_report(
    project_id: str,
    syndromes_classified: int = 0,
    pathways_generated: int = 0,
    passports_created: int = 0,
    community_score: Optional[float] = None,
    field_validation_done: bool = False,
    policy_briefs_generated: int = 0,
    re_prescriptions: int = 0,
) -> MELIAReport:
    """
    Generate a MELIA progress report from current system state.
    """
    now = datetime.utcnow()
    today = now.date().isoformat()

    def status(achieved: bool, partial: bool = False) -> str:
        return "on_track" if achieved else "partial" if partial else "not_started"

    indicators = [
        MELIAIndicator(
            result_area="Diagnosis accuracy",
            indicator="Agreement between AI diagnosis and expert/field validation",
            target="≥ 70% expert-validated syndrome classification",
            current_value="Pending expert validation" if not field_validation_done else "In progress",
            status=status(field_validation_done, syndromes_classified > 0),
            data_source="Expert review + field survey",
            last_updated=today,
        ),
        MELIAIndicator(
            result_area="Predictive performance",
            indicator="Observed vs predicted NDVI and erosion trend",
            target="NDVI prediction within ±0.05 of observed",
            current_value="Baseline established" if syndromes_classified > 0 else "Not started",
            status=status(False, syndromes_classified > 0),
            data_source="Sentinel-2 NDVI — Planetary Computer",
            last_updated=today,
        ),
        MELIAIndicator(
            result_area="Restoration suitability",
            indicator="% of recommendations validated by experts and communities",
            target="≥ 80% validation rate",
            current_value=f"{pathways_generated} pathways generated",
            status=status(pathways_generated > 0 and field_validation_done, pathways_generated > 0),
            data_source="Pathway generator + community validation",
            last_updated=today,
        ),
        MELIAIndicator(
            result_area="Community legitimacy",
            indicator="Local acceptance score, inclusion score, conflict-risk score",
            target="Community acceptance > 0.6",
            current_value=community_score if community_score else "Not assessed",
            status=status(community_score is not None and community_score > 0.6,
                          community_score is not None),
            data_source="Community Intelligence Agent",
            last_updated=today,
        ),
        MELIAIndicator(
            result_area="Policy relevance",
            indicator="Number of plans, strategies, or briefs informed by LIRA-AI outputs",
            target="≥ 2 policy documents informed",
            current_value=policy_briefs_generated,
            status=status(policy_briefs_generated >= 2, policy_briefs_generated > 0),
            data_source="Advisory Communication Agent",
            last_updated=today,
        ),
        MELIAIndicator(
            result_area="Investment readiness",
            indicator="Number of costed investment portfolios and concept notes generated",
            target="≥ 1 investment passport per pilot landscape",
            current_value=passports_created,
            status=status(passports_created >= 1),
            data_source="Investment Planning Agent",
            last_updated=today,
        ),
        MELIAIndicator(
            result_area="Learning outcomes",
            indicator="Number of rules updated through field validation and monitoring",
            target="Iterative re-prescription at 6-month intervals",
            current_value=re_prescriptions,
            status=status(re_prescriptions > 0),
            data_source="Adaptive Monitoring Agent",
            last_updated=today,
        ),
    ]

    # Calculate overall progress
    on_track = sum(1 for i in indicators if i.status == "on_track")
    partial   = sum(1 for i in indicators if i.status == "partial")
    total     = len(indicators)

    if on_track >= total * 0.6:
        overall = "on_track"
    elif (on_track + partial) >= total * 0.4:
        overall = "partial"
    else:
        overall = "lagging"

    # Learning records
    learning = []
    if syndromes_classified > 0:
        learning.append(LearningRecord(
            date=today,
            finding="Rule-based syndrome classifier active — awaiting expert validation",
            source="system",
            action_taken="Syndrome definitions documented in syndromes.yaml for expert review",
            rule_updated=False,
        ))
    if re_prescriptions > 0:
        learning.append(LearningRecord(
            date=today,
            finding=f"{re_prescriptions} re-prescription(s) triggered by monitoring alerts",
            source="monitoring",
            action_taken="Adaptive management review initiated",
            rule_updated=True,
        ))

    summary = (
        f"LIRA-AI MELIA Report — {today}. "
        f"Overall progress: {overall.replace('_', ' ')}. "
        f"{on_track}/{total} MELIA indicators on track. "
        f"{passports_created} investment passport(s) generated. "
        f"{policy_briefs_generated} policy briefs produced. "
        f"Community legitimacy: {'assessed' if community_score else 'pending'}. "
        f"Field validation: {'completed' if field_validation_done else 'pending'}."
    )

    return MELIAReport(
        project_id=project_id,
        reporting_period=today,
        indicators=indicators,
        learning_records=learning,
        overall_progress=overall,
        restoration_validation_pct=None,
        policy_decisions_informed=policy_briefs_generated,
        investment_portfolios_generated=passports_created,
        community_legitimacy_score=community_score,
        rules_updated_count=re_prescriptions,
        re_prescriptions_triggered=re_prescriptions,
        summary=summary,
        next_review_date=f"{now.year + 1}-01-01" if now.month >= 7 else f"{now.year}-07-01",
    )
