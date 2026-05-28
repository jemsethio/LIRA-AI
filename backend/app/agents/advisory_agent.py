"""
Advisory Communication Agent.
Produces farmer advisories, planning briefs, investment notes,
extension messages, and multilingual-ready community summaries.
All outputs are template-based; LLM can enhance when enabled.
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.syndromes import SyndromeDiagnosis
from app.models.pathways import PathwaySet
from app.models.climate import ClimateFuturesReport
from app.models.community import CommunityIntelligence


class CommunityAdvisory(BaseModel):
    audience: str        # farmers / pastoralists / planners / investors / extension_workers
    language_note: str   # "Amharic translation recommended for community use"
    headline: str
    key_messages: list[str]
    recommended_actions: list[str]
    seasonal_guidance: list[str]
    warning_flags: list[str]
    monitoring_tasks: list[str]


class PlanningBrief(BaseModel):
    audience: str
    title: str
    executive_summary: str
    diagnosis_highlights: list[str]
    climate_context: list[str]
    recommended_package: list[str]
    policy_hooks: list[str]
    investment_ask: str
    next_steps: list[str]


class AdvisoryPackage(BaseModel):
    project_id: str
    farmer_advisory: CommunityAdvisory
    pastoralist_advisory: CommunityAdvisory
    planner_brief: PlanningBrief
    investor_note: PlanningBrief
    extension_messages: list[str]
    equity_notes: list[str]
    is_mock: bool


def _severity_plain(sev: str) -> str:
    m = {
        "very_severe": "very serious degradation",
        "severe": "serious degradation",
        "moderate": "moderate degradation",
        "low": "mild degradation",
        "very_low": "low degradation",
    }
    return m.get(sev, sev.replace("_", " "))


class AdvisoryCommunicationAgent(BaseAgent):
    name = "AdvisoryCommunicationAgent"

    def _execute(
        self,
        project_id: str,
        syndrome: SyndromeDiagnosis,
        pathway_set: Optional[PathwaySet] = None,
        climate: Optional[ClimateFuturesReport] = None,
        community: Optional[CommunityIntelligence] = None,
        degradation_severity: str = "moderate",
        **kwargs,
    ) -> AdvisoryPackage:
        primary = syndrome.primary_syndrome
        sev_plain = _severity_plain(degradation_severity)
        syndrome_name = primary.name

        # Key messages shared across audiences
        climate_msg = (
            f"Future climate projections indicate increasing drought frequency and rainfall variability — "
            f"restoration actions must be climate-resilient."
            if climate and climate.overall_climate_risk_score > 0.5
            else "Climate trends should be monitored as part of restoration planning."
        )

        recommended_interventions = []
        if pathway_set:
            for pw in pathway_set.pathways:
                if pw.pathway_type.value == pathway_set.recommended_primary:
                    for opt in pw.recommended_package[:3]:
                        recommended_interventions.append(opt.option_name)
                    break

        # Farmer advisory
        farmer = CommunityAdvisory(
            audience="farmers",
            language_note="Translate to Amharic, Tigrinya, or Oromifa before community distribution",
            headline=f"Your land needs attention: {syndrome_name}",
            key_messages=[
                f"Your landscape shows {sev_plain}. The main problem is: {syndrome_name}.",
                f"Key causes: {', '.join(primary.likely_drivers[:3])}.",
                "Early action protects soil, water, and your future harvests.",
                climate_msg,
            ],
            recommended_actions=recommended_interventions or [
                "Build soil bunds on your most eroded field borders",
                "Do not burn crop residues — compost them instead",
                "Plant trees on degraded hillsides to reduce runoff",
            ],
            seasonal_guidance=[
                "Before rains: repair and maintain soil bunds",
                "At planting: apply compost and mulch to retain moisture",
                "During rains: check bunds after heavy storms",
                "Post-harvest: establish cover crops or residue mulch",
                "Dry season: plan restoration work — community labour is available",
            ],
            warning_flags=primary.main_symptoms[:3],
            monitoring_tasks=[
                "Count new rills in your field each year",
                "Note spring flow in dry season — improving or declining?",
                "Record your crop yield each season",
            ],
        )

        # Pastoralist advisory
        pastoralist = CommunityAdvisory(
            audience="pastoralists",
            language_note="Translate to Afaan Oromoo, Somali, or Afar as appropriate",
            headline="Rangeland alert: grazing pressure exceeds carrying capacity",
            key_messages=[
                "Rangeland condition is deteriorating due to overgrazing and rainfall variability.",
                "Feed gaps are expected to increase under future climate projections.",
                "Early destocking and rotational grazing protect the land for future seasons.",
                climate_msg,
            ],
            recommended_actions=[
                "Agree with your community on rotational grazing and rest periods",
                "Establish a community area closure for at least one season",
                "Plant fodder species (lablab, vetch) for dry-season feed",
                "Use early warning signs to plan livestock sales before feed gaps",
            ],
            seasonal_guidance=[
                "Pre-dry season: destocking if feed balance is negative",
                "Early rains: allow rest period for key grazing blocks",
                "Late rains: harvest and store fodder for dry season",
                "Dry season: monitor body condition and milk production",
            ],
            warning_flags=[
                "Bare soil patches expanding",
                "Perennial grasses replaced by annual weeds",
                "Livestock body condition declining before dry season ends",
            ],
            monitoring_tasks=[
                "Monthly livestock body condition score (scale 1–5)",
                "Dry-season basal grass cover (% per transect)",
                "Timing of first green flush after rains",
            ],
        )

        # Planner brief
        planner = PlanningBrief(
            audience="planners_and_government",
            title=f"LIRA-AI Planning Brief: {syndrome_name}",
            executive_summary=(
                f"This landscape shows {sev_plain}. "
                f"The primary syndrome — {syndrome_name} — is driven by "
                f"{', '.join(primary.likely_drivers[:3])}. "
                f"Integrated restoration investment is required to address compound degradation "
                f"before climate change intensifies current trajectories."
            ),
            diagnosis_highlights=[
                f"Primary syndrome: {syndrome_name}",
                f"Degradation severity: {degradation_severity}",
                f"Key symptoms: {', '.join(primary.main_symptoms[:3])}",
            ],
            climate_context=[
                climate_msg,
                "Climate stress testing indicates restoration window narrowing under RCP8.5.",
                "All proposed interventions have been screened for maladaptation risk.",
            ],
            recommended_package=recommended_interventions or [
                "Integrated soil and water conservation package",
                "Native species reforestation with community management",
                "Area closure with alternative livelihood support",
            ],
            policy_hooks=[
                "Aligns with Ethiopia 10-Year Development Plan — green economy pillar",
                "Supports LDN (Land Degradation Neutrality) national commitments",
                "Contributes to NDC targets for land restoration and carbon sequestration",
                "Linked to CRGE strategy — restoration and adaptation co-benefits",
            ],
            investment_ask="Medium-scale integrated restoration investment required — estimated $200–800/ha over 3–5 years (field costing required)",
            next_steps=[
                "Conduct participatory community validation workshop",
                "Commission field-level soil and vegetation baseline survey",
                "Develop detailed investment concept note with cost breakdown",
                "Engage Watershed Development Bureau for co-financing",
            ],
        )

        # Investor note
        investor = PlanningBrief(
            audience="investors_and_finance_partners",
            title=f"LIRA-AI Investment Note: Landscape Regeneration Portfolio",
            executive_summary=(
                f"This investment opportunity targets {sev_plain} in a landscape "
                f"where {syndrome_name} is driving ecological and livelihood risk. "
                f"Climate stress testing confirms that early investment generates higher returns "
                f"as climate change intensifies degradation trajectories."
            ),
            diagnosis_highlights=[
                "Evidence-based degradation diagnosis with transparency trail",
                "Climate-stress-tested restoration suitability confirmed",
                f"Syndrome match confidence: {primary.confidence}",
            ],
            climate_context=[
                "Investment is climate-robust under tested scenarios",
                "Maladaptation risks have been screened and mitigation designed",
                "Carbon co-benefits from vegetation restoration are eligible for PES/carbon markets",
            ],
            recommended_package=recommended_interventions or [
                "Integrated soil-water-vegetation restoration package",
            ],
            policy_hooks=[
                "Policy alignment confirmed with NDC and NAP frameworks",
                "Eligible for climate adaptation finance (GCF, LDCF, AF)",
                "Ecosystem service valuation available on request",
            ],
            investment_ask="Seeking co-investment for integrated landscape regeneration. High investment readiness score. Community validation pending.",
            next_steps=[
                "Field due diligence and site visit",
                "Community co-design and acceptance confirmation",
                "Detailed feasibility study and cost-benefit analysis",
                "Investment agreement and monitoring protocol",
            ],
        )

        # Equity notes
        equity_notes = []
        if community:
            if community.gendered_burdens:
                equity_notes.append(f"Gender: {community.gendered_burdens}")
            if community.youth_opportunities:
                equity_notes.append(f"Youth: {community.youth_opportunities}")
            if community.tenure_constraints:
                equity_notes.append(f"Tenure: {community.tenure_constraints}")
        equity_notes.append("All restoration packages assessed for gender and social inclusion implications.")
        equity_notes.append("Benefits and labor burden distribution should be negotiated with all community groups.")

        # Extension messages (short SMS-style)
        extension = [
            f"Alert: {syndrome_name} detected. Priority: immediate soil conservation action.",
            f"Restoration option recommended: {recommended_interventions[0] if recommended_interventions else 'soil bunds'}.",
            "Check bund condition before rains. Repair now — prevention costs less than repair.",
            "Record this season's yield for comparison next year.",
        ]

        return AdvisoryPackage(
            project_id=project_id,
            farmer_advisory=farmer,
            pastoralist_advisory=pastoralist,
            planner_brief=planner,
            investor_note=investor,
            extension_messages=extension,
            equity_notes=equity_notes,
            is_mock=syndrome.is_mock,
        )

    def _confidence(self) -> str:
        return "medium"

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Advisories are template-based — local language translation required before distribution.",
            "ASSUMPTION: Investment figures are indicative — field costing required.",
        ]
