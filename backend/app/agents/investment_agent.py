"""
Investment Planning Agent — LIRA-AI
=====================================
Concept note: "Investment Planning Agent costs interventions, estimates benefits,
screens finance readiness, and generates bankable portfolios."

Wraps the existing priority_index engine into a proper BaseAgent with:
  - Green Climate Fund (GCF) screening criteria
  - Blended finance opportunity assessment
  - Co-finance mapping
  - Scalability analysis
  - Monitoring and MRV framework
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.indicators import DiagnosticResult
from app.models.pathways import PathwaySet
from app.models.climate import ClimateFuturesReport
from app.models.community import CommunityIntelligence, PolicyAlignment
from app.engines.priority_index import (
    generate_investment_passport,
    calculate_priority_index,
)


class FinanceWindow(BaseModel):
    name:            str
    type:            str    # grant / concessional_loan / blended / result_based
    eligibility:     str    # likely / possible / unlikely
    eligibility_note:str
    minimum_readiness:float  # 0–1


class MRVFramework(BaseModel):
    monitoring_indicators: list[str]
    reporting_frequency:   str
    verification_approach: str
    data_sources:          list[str]


class InvestmentPlanningReport(BaseModel):
    project_id:            str
    passport_id:           str
    package_name:          str
    priority_score:        float
    rank:                  int
    investment_readiness:  float
    climate_robustness:    float
    finance_windows:       list[FinanceWindow]
    recommended_window:    str
    cost_estimate_usd_ha:  str
    total_cost_estimate:   str
    expected_ecosystem_benefits: list[str]
    expected_livelihood_benefits:list[str]
    co_finance_opportunities:    list[str]
    scalability_score:     float
    scalability_notes:     str
    mrv_framework:         MRVFramework
    priority_explanation:  str
    data_gaps:             list[str]
    is_mock:               bool


# Finance windows relevant to Ethiopia landscape restoration
_FINANCE_WINDOWS: list[FinanceWindow] = [
    FinanceWindow(
        name="Green Climate Fund (GCF)",
        type="grant/concessional_loan",
        eligibility="likely",
        eligibility_note="Eligible if climate rationale is strong and government accredited entity",
        minimum_readiness=0.55,
    ),
    FinanceWindow(
        name="Least Developed Countries Fund (LDCF)",
        type="grant",
        eligibility="likely",
        eligibility_note="Ethiopia is LDC-eligible; adaptation projects prioritised",
        minimum_readiness=0.45,
    ),
    FinanceWindow(
        name="Adaptation Fund (AF)",
        type="grant",
        eligibility="possible",
        eligibility_note="Direct access available through national implementing entities",
        minimum_readiness=0.50,
    ),
    FinanceWindow(
        name="CGIAR MFL / CASP Programme Funding",
        type="grant",
        eligibility="likely",
        eligibility_note="Directly aligned — action-research budget through CGIAR science program",
        minimum_readiness=0.30,
    ),
    FinanceWindow(
        name="World Bank BioCarbon Fund",
        type="result_based",
        eligibility="possible",
        eligibility_note="REDD+/restoration activities eligible; requires carbon MRV system",
        minimum_readiness=0.60,
    ),
    FinanceWindow(
        name="Public Watershed Budget (GoE)",
        type="grant",
        eligibility="likely",
        eligibility_note="Annual MoA/MoWIE watershed management allocation; implementation ready",
        minimum_readiness=0.25,
    ),
    FinanceWindow(
        name="Private Sector / Value Chain Investment",
        type="blended",
        eligibility="possible",
        eligibility_note="Coffee, sesame, livestock supply chains; requires market linkage study",
        minimum_readiness=0.65,
    ),
]


class InvestmentPlanningAgent(BaseAgent):
    name = "InvestmentPlanningAgent"

    def _execute(
        self,
        project_id:        str,
        package_name:      str         = "Integrated Landscape Restoration Package",
        target_geography:  str         = "Omo-Ghibe Basin, Ethiopia",
        pathway_components:list[str]   = None,
        diagnostic:        Optional[DiagnosticResult]       = None,
        climate:           Optional[ClimateFuturesReport]   = None,
        community:         Optional[CommunityIntelligence]  = None,
        policy:            Optional[PolicyAlignment]         = None,
        area_ha:           Optional[float]                   = None,
        **kwargs,
    ) -> InvestmentPlanningReport:

        pathway_components = pathway_components or [
            "Soil and stone bunds", "Native species reforestation",
            "Area closure with fodder access", "Compost application",
        ]

        # ── If no diagnostic provided, create a default one ───────────────────
        if diagnostic is None:
            from app.models.indicators import LandscapeIndicators
            from app.engines.indicator_engine import run_indicator_engine
            default_inds = LandscapeIndicators(project_id=project_id, is_mock=True)
            diagnostic = run_indicator_engine(default_inds)

        # ── Generate passport via engine ──────────────────────────────────────
        passport = generate_investment_passport(
            project_id=project_id,
            package_name=package_name,
            target_geography=target_geography,
            diagnostic=diagnostic,
            climate=climate,
            community=community,
            policy=policy,
            pathway_components=pathway_components,
        )

        # ── Priority index ────────────────────────────────────────────────────
        priority = calculate_priority_index(passport, diagnostic, climate, community, policy)

        # ── Finance window screening ──────────────────────────────────────────
        readiness = passport.investment_readiness_score
        eligible_windows = [w for w in _FINANCE_WINDOWS if readiness >= w.minimum_readiness]
        ineligible_windows = [
            FinanceWindow(
                name=w.name, type=w.type,
                eligibility="unlikely",
                eligibility_note=f"Readiness score {readiness:.2f} below minimum {w.minimum_readiness:.2f}",
                minimum_readiness=w.minimum_readiness,
            )
            for w in _FINANCE_WINDOWS if readiness < w.minimum_readiness
        ]
        all_windows = eligible_windows + ineligible_windows
        recommended_window = (
            eligible_windows[0].name if eligible_windows
            else "Increase investment readiness before approaching funders"
        )

        # ── Cost estimation ───────────────────────────────────────────────────
        # Indicative ranges from CGIAR/FAO SLM cost databases
        cost_per_ha = {
            "low":      "$150–350/ha",
            "medium":   "$350–800/ha",
            "high":     "$800–1,500/ha",
            "very_high":"$1,500+/ha",
        }.get(passport.estimated_cost_category, "$350–800/ha")

        total_cost = "ASSUMPTION: Field costing required"
        if area_ha:
            lo_usd = area_ha * {"low":150,"medium":350,"high":800,"very_high":1500}.get(passport.estimated_cost_category, 350)
            hi_usd = area_ha * {"low":350,"medium":800,"high":1500,"very_high":3000}.get(passport.estimated_cost_category, 800)
            total_cost = f"INDICATIVE: USD {lo_usd/1e6:.1f}M–{hi_usd/1e6:.1f}M for {area_ha:,.0f} ha"

        # ── Scalability ───────────────────────────────────────────────────────
        scale_score = round(min(1.0, readiness * 0.6 + passport.climate_robustness_score * 0.4), 3)
        scale_notes = (
            f"Scalable to {target_geography} at current readiness level. "
            f"CGIAR MFL framework allows replication across similar highland/pastoral landscapes "
            f"in Kenya, Tanzania, and Zimbabwe within 2–3 years."
        )

        # ── Co-finance ────────────────────────────────────────────────────────
        co_finance = [
            "Government of Ethiopia — MoA watershed rehabilitation annual budget",
            "CGIAR One CGIAR programme funding (in-kind science support)",
            "NGO partners — community facilitation and extension (CARE, SNV, WFP)",
        ]
        if climate and climate.overall_climate_risk_score > 0.5:
            co_finance.append("Climate adaptation finance — GCF/LDCF (climate rationale confirmed by CMIP6 risk scores)")
        if passport.climate_robustness_score > 0.6:
            co_finance.append("Carbon/ecosystem service payments — REDD+, biodiversity credits")

        # ── MRV framework ────────────────────────────────────────────────────
        mrv = MRVFramework(
            monitoring_indicators=[
                "Vegetation cover change — Sentinel-2 NDVI (annual composites)",
                "Soil organic carbon — field sampling at baseline, year 3, year 5",
                "Soil erosion rate — RUSLE model updated with annual CHIRPS rainfall",
                "Crop yield — household survey (seasonal)",
                "Livestock body condition score — community monitoring (monthly)",
                "Restoration area treated — GPS-verified GPS plots",
            ],
            reporting_frequency="Quarterly progress / annual scientific report",
            verification_approach=(
                "Independent field verification (years 2, 4); "
                "remote sensing validation (Sentinel-2 + SoilGrids updates); "
                "community-based monitoring with trained local enumerators."
            ),
            data_sources=[
                "Sentinel-2 L2A — Microsoft Planetary Computer",
                "SoilGrids v2.0 — ISRIC REST API",
                "CHIRPS v2.0 — CHC UCSB",
                "Household and community surveys — field teams",
            ],
        )

        # ── Data gaps ────────────────────────────────────────────────────────
        data_gaps = list(passport.assumptions)
        if not area_ha:
            data_gaps.append("Target area (ha) not specified — required for cost estimation")
        if not community:
            data_gaps.append("Community validation not completed")
        if not policy:
            data_gaps.append("Formal policy alignment not computed")

        return InvestmentPlanningReport(
            project_id=project_id,
            passport_id=passport.passport_id,
            package_name=package_name,
            priority_score=priority.weighted_score,
            rank=priority.rank,
            investment_readiness=readiness,
            climate_robustness=passport.climate_robustness_score,
            finance_windows=all_windows,
            recommended_window=recommended_window,
            cost_estimate_usd_ha=cost_per_ha,
            total_cost_estimate=total_cost,
            expected_ecosystem_benefits=passport.expected_ecosystem_benefits,
            expected_livelihood_benefits=passport.expected_livelihood_benefits,
            co_finance_opportunities=co_finance,
            scalability_score=scale_score,
            scalability_notes=scale_notes,
            mrv_framework=mrv,
            priority_explanation=priority.explanation,
            data_gaps=data_gaps[:8],
            is_mock=passport.is_mock,
        )

    def _evidence_trail(self) -> list[str]:
        return [
            "GCF investment criteria — climate rationale, impact potential, country ownership",
            "FAO/World Bank SLM cost database for East Africa",
            "CGIAR MFL CASP programme framework 2025–2030",
            "LIRA-AI Investment Priority Index (configurable weights)",
        ]

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Cost estimates are indicative — field costing with local implementers required.",
            "ASSUMPTION: Finance window eligibility based on readiness score thresholds — formal screening needed.",
            "ASSUMPTION: Co-finance from NGO partners not verified — letters of interest required.",
        ]

    def _confidence(self) -> str:
        return "medium"
