"""
Multifunctional Investment Priority Index.
Formula and weights are fully configurable via thresholds.yaml.
All calculations are transparent Python arithmetic — no LLM guessing.
"""

from __future__ import annotations
import uuid
from app.config import THRESHOLDS
from app.models.investment import InvestmentPassport, PriorityIndexResult
from app.models.indicators import DiagnosticResult
from app.models.climate import ClimateFuturesReport
from app.models.community import CommunityIntelligence, PolicyAlignment


def _get_weights() -> dict[str, float]:
    return THRESHOLDS.get("priority_index_weights", {
        "current_degradation_severity": 0.20,
        "future_climate_risk":          0.20,
        "ecosystem_service_value":      0.10,
        "livelihood_exposure":          0.10,
        "community_priority":           0.10,
        "policy_alignment":             0.10,
        "investment_readiness":         0.10,
        "equity_benefit":               0.05,
        "maladaptation_risk":          -0.10,
        "implementation_barriers":     -0.05,
    })


def calculate_priority_index(
    passport: InvestmentPassport,
    diagnostic: DiagnosticResult,
    climate: ClimateFuturesReport | None,
    community: CommunityIntelligence | None,
    policy: PolicyAlignment | None,
) -> PriorityIndexResult:
    weights = _get_weights()

    # Component scores (0–1)
    scores: dict[str, float] = {}

    # 1. Current degradation severity (invert health score: 0=healthy → 1=degraded)
    scores["current_degradation_severity"] = round(1.0 - diagnostic.composite_health_score, 3)

    # 2. Future climate risk
    scores["future_climate_risk"] = round(
        climate.overall_climate_risk_score if climate else 0.5, 3
    )

    # 3. Ecosystem service value — estimated from indicator context
    # Higher erosion + lower NDVI = higher service loss risk
    erosion_sev = diagnostic.indicators.get("soil_loss_rate", None)
    ndvi_res = diagnostic.indicators.get("ndvi", None)
    es_val = 0.5
    if erosion_sev and not erosion_sev.data_gap:
        es_val = erosion_sev.severity_score * 0.5
    if ndvi_res and not ndvi_res.data_gap:
        es_val += ndvi_res.severity_score * 0.5
    scores["ecosystem_service_value"] = round(min(es_val, 1.0), 3)

    # 4. Livelihood exposure — proxy: degradation severity × data completeness
    scores["livelihood_exposure"] = round(
        (1.0 - diagnostic.composite_health_score) * (diagnostic.data_completeness_pct / 100), 3
    )

    # 5. Community priority — from community intelligence form
    scores["community_priority"] = 0.5  # default if no data
    if community and community.restoration_preferences:
        scores["community_priority"] = min(len(community.restoration_preferences) / 5, 1.0)

    # 6. Policy alignment
    scores["policy_alignment"] = round(
        policy.overall_policy_score if policy else 0.5, 3
    )

    # 7. Investment readiness — from passport itself
    scores["investment_readiness"] = round(passport.investment_readiness_score, 3)

    # 8. Equity benefit — simplified: higher if community preferred future specified
    scores["equity_benefit"] = (
        0.7 if community and community.community_preferred_future else 0.3
    )

    # 9. Maladaptation risk (positive value = risk; will be subtracted)
    mal_alerts = len(passport.maladaptation_alerts)
    scores["maladaptation_risk"] = round(min(mal_alerts / 5, 1.0), 3)

    # 10. Implementation barriers
    barriers = len(passport.risk_safeguard_notes)
    scores["implementation_barriers"] = round(min(barriers / 5, 1.0), 3)

    # Weighted priority score
    weighted = sum(
        scores[k] * w
        for k, w in weights.items()
        if k in scores
    )
    weighted = round(max(0.0, min(weighted, 1.0)), 3)

    # Sensitivity: effect of +0.1 weight on each positive component
    sensitivity: dict[str, float] = {
        k: round(scores[k] * 0.1, 4)
        for k in scores
        if weights.get(k, 0) > 0
    }

    data_gaps = diagnostic.data_gaps + (
        ["climate_projection_data"] if not climate else []
    )

    explanation = (
        f"Priority score {weighted:.3f} driven by: "
        f"degradation severity ({scores['current_degradation_severity']:.2f}), "
        f"climate risk ({scores['future_climate_risk']:.2f}), "
        f"policy alignment ({scores['policy_alignment']:.2f}). "
        f"Maladaptation risk discount applied ({scores['maladaptation_risk']:.2f})."
    )

    return PriorityIndexResult(
        project_id=diagnostic.project_id,
        passport_id=passport.passport_id,
        package_name=passport.package_name,
        scores=scores,
        weighted_score=weighted,
        rank=1,  # caller sorts and assigns rank
        explanation=explanation,
        weight_sensitivity=sensitivity,
        data_gaps=data_gaps,
    )


def generate_investment_passport(
    project_id: str,
    package_name: str,
    target_geography: str,
    diagnostic: DiagnosticResult,
    climate: ClimateFuturesReport | None,
    community: CommunityIntelligence | None,
    policy: PolicyAlignment | None,
    pathway_components: list[str],
) -> InvestmentPassport:
    """
    Assemble an Investment Passport from available evidence.
    All fields marked ASSUMPTION are estimates; NEEDS VALIDATION = field check required.
    """
    passport_id = str(uuid.uuid4())

    ecosystem_benefits = [
        "Reduced topsoil loss and improved soil health",
        "Improved watershed function and water supply reliability",
        "Vegetation recovery and carbon sequestration",
        "Reduced downstream reservoir sedimentation",
    ]
    livelihood_benefits = [
        "Improved crop yields and food security",
        "Increased fodder availability for livestock",
        "Reduced labor burden from climate-resilient water access",
        "Diversified income from ecosystem services",
    ]

    # Investment readiness: function of data completeness and pathway evidence quality
    readiness = round(
        diagnostic.data_completeness_pct / 100 * 0.6 +
        (policy.overall_policy_score if policy else 0.5) * 0.4,
        3,
    )
    climate_robustness = round(
        1.0 - (climate.overall_climate_risk_score if climate else 0.5), 3
    )

    return InvestmentPassport(
        passport_id=passport_id,
        project_id=project_id,
        package_name=package_name,
        target_geography=target_geography,
        problem_diagnosis=(
            f"Landscape shows {diagnostic.degradation_severity} degradation "
            f"({int(diagnostic.data_completeness_pct)}% data completeness). "
            f"Key data gaps: {', '.join(diagnostic.data_gaps[:3]) or 'none identified'}."
        ),
        future_climate_rationale=(
            climate.summary_narrative if climate else
            "ASSUMPTION: Climate risk assessment pending — placeholder climate scenario applied."
        ),
        intervention_components=pathway_components,
        expected_ecosystem_benefits=ecosystem_benefits,
        expected_livelihood_benefits=livelihood_benefits,
        beneficiaries=["Smallholder farming households", "Pastoralist communities", "Downstream water users"],
        estimated_cost_category="medium",
        estimated_cost_usd_range="ASSUMPTION: $200–800/ha depending on intervention mix (needs field costing)",
        implementation_partners=[
            "Ethiopia Ministry of Agriculture",
            "Regional Watershed Management Bureau",
            "Local NGO partners",
            "CGIAR Research Programs",
        ],
        community_acceptance_status=(
            "Community preferences documented" if community and community.restoration_preferences
            else "NEEDS VALIDATION: Community consultation required"
        ),
        policy_alignment=(
            policy.aligned_policies if policy else
            ["ASSUMPTION: Policy alignment assessment pending"]
        ),
        investment_readiness_score=readiness,
        climate_robustness_score=climate_robustness,
        risk_safeguard_notes=[
            "Land tenure clarity required before investment",
            "Gender and social inclusion safeguard needed",
            "Community benefit-sharing arrangement required",
        ],
        maladaptation_alerts=(
            climate.maladaptation_climate_alerts if climate else
            ["NEEDS VALIDATION: Climate scenario-specific risks not yet assessed"]
        ),
        monitoring_indicators=[
            "Vegetation cover change (Sentinel-2 NDVI)",
            "Soil erosion rate (field survey + modelling)",
            "Crop yield trends (household survey)",
            "Streamflow and turbidity (gauge station)",
        ],
        evidence_trail=[
            f"Diagnostic completeness: {diagnostic.data_completeness_pct}%",
            f"Syndrome: {diagnostic.degradation_severity} — rule-based classification",
            "Restoration option cards: WOCAT, CGIAR, FAO databases",
        ],
        uncertainty_score=round(1.0 - diagnostic.data_completeness_pct / 100, 3),
        confidence_score=round(diagnostic.data_completeness_pct / 100, 3),
        assumptions=[
            "ASSUMPTION: Cost ranges are indicative; detailed costing requires field visits.",
            "ASSUMPTION: Beneficiary numbers estimated from administrative data.",
            "NEEDS VALIDATION: Carrying capacity, tenure arrangements, and community governance capacity.",
        ],
        is_mock=diagnostic.is_mock,
    )
