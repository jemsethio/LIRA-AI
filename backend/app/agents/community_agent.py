"""
Community Intelligence Agent — LIRA-AI
========================================
Synthesises community knowledge into a structured decision layer.
Concept note: "Community Intelligence Agent captures local priorities,
tenure issues, labor, gender, grazing rules, and adoption feasibility."

Input: CommunityIntelligence form data + DiagnosticResult
Output: CommunityIntelligenceReport with scores, flags, and advisories

Equity and inclusion is treated as a core decision criterion, not an add-on.
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.community import CommunityIntelligence
from app.models.indicators import DiagnosticResult


class EquityScore(BaseModel):
    gender_inclusion_score:    float   # 0–1
    youth_opportunity_score:   float
    tenure_security_score:     float
    conflict_risk_score:       float   # 0=low risk, 1=high
    adoption_feasibility_score:float
    overall_equity_score:      float
    equity_flags:              list[str]
    recommended_safeguards:    list[str]


class CommunityIntelligenceReport(BaseModel):
    project_id:              str
    data_source:             str          # form / csv / estimated
    community_priority_score:float        # 0–1 — how aligned with community preferences
    labor_constraint_level:  str          # low / medium / high / critical
    tenure_risk_level:       str
    conflict_risk_level:     str
    equity:                  EquityScore
    preferred_interventions: list[str]
    adoption_barriers:       list[str]
    local_success_indicators:list[str]
    gender_advisory:         str
    youth_advisory:          str
    negotiation_requirements:list[str]
    validation_questions:    list[str]
    confidence:              str
    data_gaps:               list[str]
    is_mock:                 bool


class CommunityIntelligenceAgent(BaseAgent):
    name = "CommunityIntelligenceAgent"

    def _execute(
        self,
        project_id:  str,
        community:   Optional[CommunityIntelligence] = None,
        diagnostic:  Optional[DiagnosticResult]      = None,
        **kwargs,
    ) -> CommunityIntelligenceReport:

        # ── Data availability ────────────────────────────────────────────────
        has_data  = community is not None
        data_src  = "form" if has_data else "estimated"
        is_mock   = not has_data

        def _list(attr: str) -> list[str]:
            if not community: return []
            val = getattr(community, attr, None)
            if isinstance(val, list): return [str(v) for v in val]
            if val: return [str(val)]
            return []

        def _str(attr: str) -> str:
            if not community: return ""
            return str(getattr(community, attr, "") or "")

        # ── Community priority score ─────────────────────────────────────────
        # Higher when: community data rich, restoration preferences stated,
        #              success indicators defined, preferred future articulated
        indicators_present = sum([
            bool(_str("community_preferred_future")),
            bool(_str("local_degradation_memory")),
            len(_list("restoration_preferences")) > 0,
            len(_list("local_success_indicators")) > 0,
            bool(_str("grazing_rules")),
        ])
        priority_score = round(min(1.0, indicators_present / 5), 3) if has_data else 0.3

        # ── Labor constraint ─────────────────────────────────────────────────
        labor_txt = _str("labor_constraints").lower()
        labor_level = (
            "critical" if any(w in labor_txt for w in ["severe", "no labor", "elderly only", "shortage"]) else
            "high"     if any(w in labor_txt for w in ["out-migrat", "limited", "scarce", "only women"]) else
            "medium"   if labor_txt else "low"
        )

        # ── Tenure risk ──────────────────────────────────────────────────────
        tenure_txt = _str("tenure_constraints").lower()
        tenure_level = (
            "high"   if any(w in tenure_txt for w in ["unclear", "ambiguous", "disputed", "no certificate"]) else
            "medium" if tenure_txt else "low"
        )

        # ── Conflict risk ────────────────────────────────────────────────────
        conflict_txt = _str("local_conflict_risks").lower()
        conflict_level = (
            "very_high" if any(w in conflict_txt for w in ["violent", "extreme", "armed", "very high"]) else
            "high"      if any(w in conflict_txt for w in ["high", "serious", "inter-ethnic", "boundary"]) else
            "moderate"  if conflict_txt else "low"
        )

        # ── Equity scoring ───────────────────────────────────────────────────
        gendered_txt = _str("gendered_burdens").lower()
        youth_txt    = _str("youth_opportunities").lower()

        gender_score = (
            0.3 if any(w in gendered_txt for w in ["heavy", "3-4h", "4-6h", "excessive"]) else
            0.6 if gendered_txt else 0.7
        )
        youth_score = (
            0.8 if any(w in youth_txt for w in ["enterprise", "training", "nursery", "monitoring"]) else
            0.5 if youth_txt else 0.3
        )
        tenure_score = {"low": 0.8, "medium": 0.5, "high": 0.2}.get(tenure_level, 0.5)
        conflict_score = {"low": 0.1, "moderate": 0.4, "high": 0.7, "very_high": 0.95}.get(conflict_level, 0.3)
        adoption_barriers = _list("adoption_barriers")
        adoption_score = max(0.1, 1.0 - len(adoption_barriers) * 0.15)
        overall_equity = round((gender_score + youth_score + tenure_score + (1-conflict_score) + adoption_score) / 5, 3)

        equity_flags: list[str] = []
        if gender_score < 0.5:
            equity_flags.append("High gendered burden — restoration must reduce women's workload, not increase it")
        if youth_score < 0.5:
            equity_flags.append("Limited youth engagement — identify income and skill opportunities in restoration package")
        if conflict_score > 0.6:
            equity_flags.append("High conflict risk — community dialogue and conflict-sensitive facilitation required before any intervention")
        if tenure_score < 0.4:
            equity_flags.append("Tenure insecurity — land rights clarification is a prerequisite for investment")

        safeguards: list[str] = []
        if gender_score < 0.5:
            safeguards.append("Gender action plan: map women's workload and ensure interventions create time savings")
        if conflict_score > 0.5:
            safeguards.append("Conflict-sensitive facilitation protocol before community meetings")
        if tenure_score < 0.5:
            safeguards.append("Engage local government to clarify/formalise tenure before land-based investments")

        # ── Advisories ───────────────────────────────────────────────────────
        gender_adv = (
            f"Women currently bear significant burdens ({_str('gendered_burdens')[:80]}). "
            "Restoration interventions must explicitly reduce — not add to — these burdens. "
            "Fuelwood, water, and fodder availability should improve as direct outcomes."
            if gendered_txt else
            "Gender assessment not yet collected. Conduct gender disaggregated focus groups before finalising pathway selection."
        )

        youth_adv = (
            f"Youth opportunities identified: {_str('youth_opportunities')[:100]}. "
            "Formalise these as enterprise or employment pathways within the restoration package."
            if youth_txt else
            "Youth engagement pathway not defined. Identify nursery, monitoring, or value-chain roles to prevent out-migration."
        )

        # ── Validation questions ─────────────────────────────────────────────
        validation_qs = [
            "Do restoration preferences reflect the views of women and youth, not only male household heads?",
            "Have adoption barriers been verified through direct community consultation?",
            "Is the stated community preferred future aligned with formal land use plans?",
            "Have grazing rules been tested under drought conditions?",
        ]
        if conflict_level in ("high", "very_high"):
            validation_qs.insert(0, "Has a conflict stakeholder mapping been completed with all affected ethnic/social groups?")

        # ── Negotiation requirements ─────────────────────────────────────────
        negotiation = []
        if tenure_level != "low":
            negotiation.append("Land tenure negotiation with local government and customary authorities")
        if conflict_level != "low":
            negotiation.append("Conflict mediation and inter-community dialogue protocol")
        if labor_level in ("high", "critical"):
            negotiation.append("Labour calendar alignment — restoration work outside peak agricultural/livestock seasons")
        negotiation.append("Community benefit-sharing agreement before investment mobilisation")

        # ── Data gaps ────────────────────────────────────────────────────────
        data_gaps: list[str] = []
        if not has_data:
            data_gaps.append("Full community intelligence form not yet completed")
        for field in ["grazing_rules", "tenure_constraints", "local_conflict_risks", "gendered_burdens"]:
            if not _str(field):
                data_gaps.append(f"{field.replace('_',' ')} not captured")

        return CommunityIntelligenceReport(
            project_id=project_id,
            data_source=data_src,
            community_priority_score=priority_score,
            labor_constraint_level=labor_level,
            tenure_risk_level=tenure_level,
            conflict_risk_level=conflict_level,
            equity=EquityScore(
                gender_inclusion_score=round(gender_score, 3),
                youth_opportunity_score=round(youth_score, 3),
                tenure_security_score=round(tenure_score, 3),
                conflict_risk_score=round(conflict_score, 3),
                adoption_feasibility_score=round(adoption_score, 3),
                overall_equity_score=overall_equity,
                equity_flags=equity_flags,
                recommended_safeguards=safeguards,
            ),
            preferred_interventions=_list("restoration_preferences"),
            adoption_barriers=adoption_barriers,
            local_success_indicators=_list("local_success_indicators"),
            gender_advisory=gender_adv,
            youth_advisory=youth_adv,
            negotiation_requirements=negotiation,
            validation_questions=validation_qs,
            confidence="high" if has_data else "low",
            data_gaps=data_gaps,
            is_mock=is_mock,
        )

    def _evidence_trail(self) -> list[str]:
        return [
            "Community form data — direct stakeholder input",
            "CGIAR gender and social inclusion assessment framework",
            "ILRI conflict-sensitive pastoral development guidelines",
        ]

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Labor constraint level inferred from text — field census required for accuracy.",
            "ASSUMPTION: Conflict risk derived from qualitative description — formal stakeholder mapping recommended.",
            "NEEDS VALIDATION: All equity scores require participatory validation with women and youth groups.",
        ]

    def _confidence(self) -> str:
        return "medium"
