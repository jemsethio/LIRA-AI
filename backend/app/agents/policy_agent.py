"""
Policy Alignment Agent — LIRA-AI
==================================
Concept note: "Policy Alignment Agent links restoration pathways to NDCs,
NAPs, LDN, biodiversity, agriculture, watershed, and local development plans."

Calculates alignment scores against 10 policy frameworks.
Generates policy-ready outputs: alignment scores, planning briefs,
institutional responsibility maps, policy gap alerts, investment justification.
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.indicators import DiagnosticResult
from app.models.pathways import PathwaySet


class PolicyScore(BaseModel):
    framework:      str
    score:          float   # 0–1
    alignment_note: str
    policy_hook:    str     # specific target/article


class PolicyAlignmentReport(BaseModel):
    project_id:                  str
    overall_policy_score:        float
    ndcs_score:                  float
    naps_score:                  float
    ldn_score:                   float
    biodiversity_score:          float
    agriculture_food_security:   float
    watershed_management:        float
    carbon_pes_score:            float
    local_development_score:     float
    rangeland_livestock_score:   float
    climate_smart_agriculture:   float
    scores_detail:               list[PolicyScore]
    aligned_policies:            list[str]
    misalignment_risks:          list[str]
    policy_gap_alerts:           list[str]
    institutional_responsibility:list[str]
    investment_justification:    str
    climate_contribution_summary:str
    confidence:                  str
    is_mock:                     bool


# Ethiopia-specific policy targets per framework
_ETH_POLICY = {
    "ndcs": {
        "target":  "Ethiopia NDC 2021 — restore 15 Mha of degraded land by 2030; reduce GHG 68.8% by 2030",
        "hook":    "NDC Land Use, Land Use Change and Forestry (LULUCF) mitigation target",
    },
    "naps": {
        "target":  "Ethiopia NAP 2023 — improve climate resilience of smallholder farming and pastoral systems",
        "hook":    "NAP Priority 3: Sustainable Land and Watershed Management",
    },
    "ldn": {
        "target":  "Ethiopia LDN target — no net loss of productive land by 2030 (Bonn Challenge)",
        "hook":    "LDN voluntary target: restore 1.5 Mha by 2030 in Amhara, Oromia, SNNPR",
    },
    "biodiversity": {
        "target":  "NBSAP Ethiopia — 30×30 target; restore 22% of degraded ecosystems",
        "hook":    "CBD Global Biodiversity Framework Target 2 (ecosystem restoration)",
    },
    "agriculture": {
        "target":  "Ethiopia 10-Year Development Plan 2021–2030 — food self-sufficiency and export growth",
        "hook":    "Green Economy Pillar: Sustainable agricultural intensification",
    },
    "watershed": {
        "target":  "Ethiopia Watershed Management Programme — treat 5 Mha of watersheds",
        "hook":    "MoA/MoWIE Integrated Watershed Management Guidelines",
    },
    "carbon_pes": {
        "target":  "CRGE Strategy — forest protection and tree planting for 130 Mt CO2e reduction",
        "hook":    "Ethiopia CRGE Forest Sector Initiative; REDD+ national programme",
    },
    "local": {
        "target":  "Regional/Woreda Development Plans — annual restoration targets",
        "hook":    "SNNPR/Oromia regional land rehabilitation programmes",
    },
    "rangeland": {
        "target":  "Ethiopia Pastoral Policy 2018 — sustainable rangeland management in pastoral areas",
        "hook":    "Pastoral Policy Article 12: rangeland carrying capacity restoration",
    },
    "csa": {
        "target":  "Ethiopia Climate-Smart Agriculture Investment Plan (CSAIP 2020–2030)",
        "hook":    "CSAIP Pillar 2: soil health and water management",
    },
}


def _score_framework(
    framework_key: str,
    syndrome_id:   str,
    pathway_types: list[str],
    degradation_severity: str,
) -> float:
    """
    Rule-based alignment score (0–1) based on syndrome and pathway types.
    Higher score = stronger alignment with this policy framework.
    """
    severity_boost = {
        "very_severe": 0.15, "severe": 0.10,
        "moderate": 0.05, "low": 0.0, "very_low": 0.0
    }.get(degradation_severity, 0.05)

    # Base alignment by syndrome type and framework
    base_scores: dict[str, dict[str, float]] = {
        "erosion_productivity_decline": {
            "ndcs":0.8,"naps":0.8,"ldn":0.9,"biodiversity":0.6,
            "agriculture":0.9,"watershed":0.9,"carbon_pes":0.6,
            "local":0.7,"rangeland":0.4,"csa":0.8,
        },
        "moisture_stress": {
            "ndcs":0.75,"naps":0.9,"ldn":0.7,"biodiversity":0.5,
            "agriculture":0.8,"watershed":0.8,"carbon_pes":0.4,
            "local":0.7,"rangeland":0.6,"csa":0.9,
        },
        "rangeland_overgrazing": {
            "ndcs":0.7,"naps":0.75,"ldn":0.8,"biodiversity":0.7,
            "agriculture":0.6,"watershed":0.7,"carbon_pes":0.5,
            "local":0.6,"rangeland":1.0,"csa":0.65,
        },
        "deforestation_vegetation_loss": {
            "ndcs":0.95,"naps":0.8,"ldn":0.9,"biodiversity":0.95,
            "agriculture":0.5,"watershed":0.8,"carbon_pes":0.95,
            "local":0.7,"rangeland":0.4,"csa":0.55,
        },
        "reservoir_sedimentation": {
            "ndcs":0.7,"naps":0.7,"ldn":0.75,"biodiversity":0.6,
            "agriculture":0.6,"watershed":0.95,"carbon_pes":0.5,
            "local":0.75,"rangeland":0.4,"csa":0.55,
        },
        "soil_carbon_depletion": {
            "ndcs":0.8,"naps":0.7,"ldn":0.85,"biodiversity":0.6,
            "agriculture":0.85,"watershed":0.65,"carbon_pes":0.8,
            "local":0.65,"rangeland":0.5,"csa":0.8,
        },
        "mixed_high_risk": {
            "ndcs":0.85,"naps":0.85,"ldn":0.85,"biodiversity":0.75,
            "agriculture":0.75,"watershed":0.8,"carbon_pes":0.7,
            "local":0.7,"rangeland":0.6,"csa":0.75,
        },
    }
    base = base_scores.get(syndrome_id, {k: 0.6 for k in _ETH_POLICY}).get(framework_key, 0.6)

    # Pathway boost: investment_ready and climate_robust pathways align best
    pathway_boost = 0.0
    if "investment_ready"  in pathway_types: pathway_boost += 0.05
    if "climate_robust"    in pathway_types: pathway_boost += 0.03
    if "biodiversity_carbon" in pathway_types and framework_key in ("carbon_pes","biodiversity","ndcs"):
        pathway_boost += 0.05

    return round(min(1.0, base + severity_boost + pathway_boost), 3)


class PolicyAlignmentAgent(BaseAgent):
    name = "PolicyAlignmentAgent"

    def _execute(
        self,
        project_id:  str,
        diagnostic:  Optional[DiagnosticResult] = None,
        pathway_set: Optional[PathwaySet]        = None,
        **kwargs,
    ) -> PolicyAlignmentReport:

        syndrome_id = kwargs.get("syndrome_id", "mixed_high_risk")
        degradation_severity = diagnostic.degradation_severity if diagnostic else "moderate"
        pathway_types = [p.pathway_type.value for p in pathway_set.pathways] if pathway_set else []

        def s(fk: str) -> float:
            return _score_framework(fk, syndrome_id, pathway_types, degradation_severity)

        # Score all 10 frameworks
        scores = {k: s(k) for k in _ETH_POLICY}

        overall = round(sum(scores.values()) / len(scores), 3)

        # Build detail objects
        detail: list[PolicyScore] = []
        for key, cfg in _ETH_POLICY.items():
            sc = scores[key]
            level = "strong" if sc > 0.75 else "moderate" if sc > 0.5 else "weak"
            detail.append(PolicyScore(
                framework=key.replace("_"," ").title(),
                score=sc,
                alignment_note=f"{level.title()} alignment — {cfg['target'][:80]}",
                policy_hook=cfg["hook"],
            ))

        # Aligned policies
        aligned = [d.policy_hook for d in detail if d.score > 0.70]

        # Misalignment risks
        misaligned: list[str] = []
        for d in detail:
            if d.score < 0.5:
                misaligned.append(f"Weak alignment with {d.framework} — review intervention package against {d.policy_hook}")

        # Policy gap alerts
        gap_alerts: list[str] = []
        if scores.get("ldn", 0) < 0.6:
            gap_alerts.append("LDN alignment gap — add explicit no-net-loss commitment and monitoring baseline")
        if scores.get("carbon_pes", 0) < 0.6:
            gap_alerts.append("Carbon/PES opportunity underexplored — assess REDD+ or carbon market eligibility")
        if scores.get("local", 0) < 0.6:
            gap_alerts.append("Local development plan not aligned — engage woreda planning office before implementation")

        # Institutional responsibility
        institutions = [
            "Ministry of Agriculture (MoA) — land rehabilitation and ISFM programmes",
            "Ministry of Water and Energy (MoWIE) — watershed management coordination",
            "Environment Commission (MoEFCC) — NDC/CRGE implementation oversight",
            "Regional Watershed Development Bureau — field implementation authority",
            "Local Government (Woreda/Kebele) — land tenure and community facilitation",
        ]
        if scores.get("rangeland", 0) > 0.6:
            institutions.append("Pastoral Development Commission — rangeland restoration coordination")
        if scores.get("carbon_pes", 0) > 0.65:
            institutions.append("Ethiopian Carbon Registry / REDD+ National Coordination — carbon accounting")

        # Investment justification
        invest_just = (
            f"This investment package aligns with {len(aligned)} of 10 assessed policy frameworks "
            f"(overall score: {overall:.2f}/1.0), including Ethiopia's NDC land restoration commitment "
            f"(15 Mha by 2030), LDN targets, and the CGIAR MFL Science Program. "
            f"It addresses {degradation_severity} degradation through pathways that are "
            f"climate-smart, community-grounded, and eligible for climate adaptation finance."
        )

        climate_contrib = (
            f"Estimated climate contributions: reduced soil erosion improves carbon sequestration "
            f"(aligned with CRGE LULUCF target), restoration suitability zone improvements "
            f"under {pathway_types[0].replace('_',' ') if pathway_types else 'recommended'} pathway "
            f"support Ethiopia's NDC target of 68.8% GHG reduction by 2030. "
            f"Maladaptation risks have been assessed against SSP2-4.5 and SSP5-8.5 scenarios."
        )

        return PolicyAlignmentReport(
            project_id=project_id,
            overall_policy_score=overall,
            ndcs_score=scores["ndcs"],
            naps_score=scores["naps"],
            ldn_score=scores["ldn"],
            biodiversity_score=scores["biodiversity"],
            agriculture_food_security=scores["agriculture"],
            watershed_management=scores["watershed"],
            carbon_pes_score=scores["carbon_pes"],
            local_development_score=scores["local"],
            rangeland_livestock_score=scores["rangeland"],
            climate_smart_agriculture=scores["csa"],
            scores_detail=detail,
            aligned_policies=aligned,
            misalignment_risks=misaligned,
            policy_gap_alerts=gap_alerts,
            institutional_responsibility=institutions,
            investment_justification=invest_just,
            climate_contribution_summary=climate_contrib,
            confidence="medium",
            is_mock=False,
        )

    def _evidence_trail(self) -> list[str]:
        return [
            "Ethiopia NDC (2021) — UNFCCC submission",
            "Ethiopia National Adaptation Plan (2023)",
            "Ethiopia LDN voluntary target (UNCCD)",
            "CGIAR CRGE Strategy — Forest and Land Use Sector",
            "CBD Global Biodiversity Framework (GBF) 2022",
        ]

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Policy alignment scores are rule-based; review against current national plans.",
            "ASSUMPTION: Local development plan alignment defaulted to 0.7 without woreda plan access.",
            "NEEDS VALIDATION: Carbon/PES eligibility requires formal scoping with Ethiopian Carbon Registry.",
        ]

    def _confidence(self) -> str:
        return "medium"
