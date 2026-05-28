"""
Tradeoff and Maladaptation Agent.
Scores each regeneration pathway across 13 risk dimensions
and produces a maladaptation radar output.
"""

from __future__ import annotations
from app.agents.base_agent import BaseAgent
from app.models.pathways import RegenerationPathway
from app.models.community import CommunityIntelligence
from pydantic import BaseModel


RISK_DIMENSIONS = [
    "labor_burden",
    "cost",
    "grazing_restriction",
    "water_competition",
    "land_tenure_risk",
    "gender_youth_implications",
    "biodiversity_risk",
    "carbon_permanence_risk",
    "upstream_downstream_effects",
    "conflict_risk",
    "adoption_feasibility",
    "maintenance_burden",
    "maladaptation_risk",
]


class TradeoffRadar(BaseModel):
    pathway_type: str
    scores: dict[str, float]       # 0=low risk, 1=high risk
    risk_levels: dict[str, str]    # low / medium / high / mitigation_needed / field_validation_required
    overall_risk: float
    high_risk_flags: list[str]
    mitigation_needed: list[str]
    field_validation_required: list[str]
    summary: str


class TradeoffReport(BaseModel):
    project_id: str
    radars: list[TradeoffRadar]
    lowest_risk_pathway: str
    highest_risk_pathway: str
    cross_cutting_risks: list[str]
    is_mock: bool


def _score_dimension(dim: str, pathway: RegenerationPathway, community: CommunityIntelligence | None) -> float:
    """Rule-based scoring — deterministic."""
    labor = pathway.labor_burden  # low / medium / high
    cost = pathway.cost_category

    if dim == "labor_burden":
        return {"low": 0.2, "medium": 0.5, "high": 0.8}.get(labor, 0.5)

    if dim == "cost":
        return {"low": 0.2, "medium": 0.5, "high": 0.75, "very_high": 0.9}.get(cost, 0.5)

    if dim == "grazing_restriction":
        pkg_names = " ".join(o.option_name.lower() for o in pathway.recommended_package)
        return 0.8 if "exclos" in pkg_names or "closure" in pkg_names else 0.2

    if dim == "water_competition":
        pkg_names = " ".join(o.option_name.lower() for o in pathway.recommended_package)
        return 0.6 if "reforestation" in pkg_names else 0.2

    if dim == "land_tenure_risk":
        if community and community.tenure_constraints:
            return 0.7
        return 0.4

    if dim == "gender_youth_implications":
        if community and community.gendered_burdens:
            return 0.6
        return 0.3

    if dim == "biodiversity_risk":
        mal_text = " ".join(pathway.maladaptation_risks).lower()
        return 0.7 if "monoculture" in mal_text else 0.2

    if dim == "carbon_permanence_risk":
        pkg_names = " ".join(o.option_name.lower() for o in pathway.recommended_package)
        return 0.6 if "reforestation" in pkg_names else 0.3

    if dim == "upstream_downstream_effects":
        pkg_names = " ".join(o.option_name.lower() for o in pathway.recommended_package)
        return 0.5 if "water_harvest" in pkg_names or "bund" in pkg_names else 0.2

    if dim == "conflict_risk":
        if community and community.local_conflict_risks:
            return 0.7
        return 0.3

    if dim == "adoption_feasibility":
        if community and community.adoption_barriers:
            return min(len(community.adoption_barriers) / 5, 1.0)
        return 0.4

    if dim == "maintenance_burden":
        pkg_names = " ".join(o.option_name.lower() for o in pathway.recommended_package)
        return 0.7 if "dam" in pkg_names or "bund" in pkg_names else 0.3

    if dim == "maladaptation_risk":
        return min(len(pathway.maladaptation_risks) / 6, 1.0)

    return 0.5


def _level(score: float) -> str:
    if score < 0.25:
        return "low_risk"
    elif score < 0.5:
        return "medium_risk"
    elif score < 0.75:
        return "high_risk"
    elif score < 0.9:
        return "mitigation_needed"
    return "field_validation_required"


class TradeoffMaladaptationAgent(BaseAgent):
    name = "TradeoffMaladaptationAgent"

    def _execute(
        self,
        project_id: str,
        pathways: list[RegenerationPathway],
        community: CommunityIntelligence | None = None,
        **kwargs,
    ) -> TradeoffReport:
        radars: list[TradeoffRadar] = []

        for pathway in pathways:
            scores = {d: round(_score_dimension(d, pathway, community), 2) for d in RISK_DIMENSIONS}
            levels = {d: _level(s) for d, s in scores.items()}
            overall = round(sum(scores.values()) / len(scores), 3)

            high_risk = [d for d, l in levels.items() if l == "high_risk"]
            mitigation = [d for d, l in levels.items() if l == "mitigation_needed"]
            field_val = [d for d, l in levels.items() if l == "field_validation_required"]

            summary = (
                f"Overall risk: {'High' if overall > 0.6 else 'Medium' if overall > 0.35 else 'Low'} "
                f"({overall:.2f}). "
            )
            if high_risk:
                summary += f"High-risk dimensions: {', '.join(high_risk)}. "
            if mitigation:
                summary += f"Mitigation required: {', '.join(mitigation)}."

            radars.append(TradeoffRadar(
                pathway_type=pathway.pathway_type.value,
                scores=scores,
                risk_levels=levels,
                overall_risk=overall,
                high_risk_flags=high_risk,
                mitigation_needed=mitigation,
                field_validation_required=field_val,
                summary=summary,
            ))

        radars.sort(key=lambda r: r.overall_risk)
        lowest = radars[0].pathway_type if radars else "unknown"
        highest = radars[-1].pathway_type if radars else "unknown"

        cross_cutting = [
            d for d in RISK_DIMENSIONS
            if sum(1 for r in radars if r.scores.get(d, 0) > 0.5) >= len(radars) // 2
        ]

        return TradeoffReport(
            project_id=project_id,
            radars=radars,
            lowest_risk_pathway=lowest,
            highest_risk_pathway=highest,
            cross_cutting_risks=cross_cutting,
            is_mock=kwargs.get("is_mock", False),
        )

    def _confidence(self) -> str:
        return "medium"

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Risk scores are rule-based estimates — community consultation required.",
            "ASSUMPTION: Gender and tenure risks default to medium when no community data provided.",
        ]
