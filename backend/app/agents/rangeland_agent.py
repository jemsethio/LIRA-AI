"""
Rangeland and Livestock Agent.
Assesses grazing pressure, feed availability, carrying capacity estimates,
livestock climate stress, and rangeland restoration options.
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.indicators import DiagnosticResult
from app.models.community import CommunityIntelligence


class RangelandReport(BaseModel):
    project_id: str
    grazing_pressure: str
    grazing_pressure_score: float
    estimated_carrying_capacity_tlu_ha: Optional[float]
    feed_balance: str
    feed_gap_risk: str
    livestock_climate_stress: str
    rangeland_condition: str
    rangeland_score: float
    bare_ground_risk: str
    encroachment_risk: str
    restoration_options: list[str]
    governance_entry_points: list[str]
    monitoring_indicators: list[str]
    assumptions: list[str]
    confidence: str
    data_gaps: list[str]
    is_mock: bool


# Tropical Livestock Unit (TLU) equivalents
# Carrying capacity for Ethiopian highlands: 0.5–2.0 TLU/ha depending on condition
CC_BY_CONDITION = {
    "good":     2.0,   # TLU/ha/year
    "moderate": 1.2,
    "poor":     0.6,
    "degraded": 0.3,
}


class RangelandLivestockAgent(BaseAgent):
    name = "RangelandLivestockAgent"

    def _execute(
        self,
        project_id: str,
        diagnostic: DiagnosticResult,
        community: Optional[CommunityIntelligence] = None,
        **kwargs,
    ) -> RangelandReport:
        inds = diagnostic.indicators
        is_mock = diagnostic.is_mock

        ndvi_ind  = inds.get("ndvi")
        og_ind    = inds.get("overgrazing")
        prod_ind  = inds.get("land_productivity")
        rain_ind  = inds.get("rainfall")
        temp_ind  = inds.get("soil_moisture")  # proxy for feed availability

        ndvi_sev  = ndvi_ind.severity_score if ndvi_ind  and not ndvi_ind.data_gap  else 0.5
        ndvi_val  = ndvi_ind.value          if ndvi_ind  and not ndvi_ind.data_gap  else 0.3
        og_sev    = og_ind.severity_score   if og_ind    and not og_ind.data_gap    else 0.5
        prod_sev  = prod_ind.severity_score if prod_ind  and not prod_ind.data_gap  else 0.5
        rain_sev  = rain_ind.severity_score if rain_ind  and not rain_ind.data_gap  else 0.4

        # Grazing pressure composite
        grazing_score = round(og_sev * 0.6 + ndvi_sev * 0.4, 3)
        grazing_label = (
            "very_high" if grazing_score > 0.7 else
            "high"      if grazing_score > 0.5 else
            "moderate"  if grazing_score > 0.3 else "low"
        )

        # Rangeland condition
        range_score = round(1.0 - (ndvi_sev * 0.5 + prod_sev * 0.3 + og_sev * 0.2), 3)
        range_label = (
            "severely_degraded" if range_score < 0.2 else
            "degraded"          if range_score < 0.4 else
            "fair"              if range_score < 0.6 else "good"
        )

        # Estimated carrying capacity (TLU/ha)
        cc = CC_BY_CONDITION.get(range_label, 0.6)

        # Feed balance
        feed_label = (
            "severe_deficit" if grazing_score > 0.7 and rain_sev > 0.5 else
            "deficit"        if grazing_score > 0.5 else
            "marginal"       if grazing_score > 0.3 else "balanced"
        )
        feed_gap = (
            "high"     if feed_label in ("severe_deficit", "deficit") else
            "moderate" if feed_label == "marginal" else "low"
        )

        # Livestock climate stress (heat + moisture)
        climate_stress = (
            "high"     if rain_sev > 0.6 else
            "moderate" if rain_sev > 0.35 else "low"
        )

        bare_ground_risk = (
            "high" if ndvi_val < 0.15 else
            "moderate" if ndvi_val < 0.25 else "low"
        )

        encroachment_risk = (
            "high" if og_sev > 0.5 and 0.2 < ndvi_val < 0.4 else
            "moderate" if og_sev > 0.3 else "low"
        )

        # Restoration options
        options = []
        if grazing_score > 0.5:
            options.append("Establish rotational grazing with 3–4 paddock system")
        if grazing_score > 0.6:
            options.append("Community-managed area closure with alternative fodder supply")
        if feed_label in ("severe_deficit", "deficit"):
            options.append("Fodder bank establishment (lablab, vetch, rhodes grass)")
        if bare_ground_risk in ("high", "moderate"):
            options.append("Reseeding of bare patches with local grass species")
        if encroachment_risk == "high":
            options.append("Mechanical Prosopis control followed by native grass reseeding")
        options.append("Destocking / livestock early offtake during drought alerts")
        options.append("Improved water points to reduce pressure on riparian vegetation")

        # Governance entry points
        governance = []
        if community and community.grazing_rules:
            governance.append(f"Build on existing grazing rules: {community.grazing_rules[:80]}")
        governance.extend([
            "Village bylaws or kebele grazing agreements",
            "Seasonal mobility corridors between highland and lowland",
            "Community livestock early warning and drought response plan",
        ])

        monitoring = [
            "Basal cover % (dry-season Braun-Blanquet transects)",
            "Grass species composition (perennial vs annual ratio)",
            "Livestock body condition score (monthly market assessment)",
            "Calving and milk production rates (community data)",
            "NDVI time series (growing season peak vs dry season floor)",
        ]

        data_gaps = [k for k, v in inds.items() if v.data_gap]
        data_gaps.append("livestock_census_data")
        data_gaps.append("carrying_capacity_field_assessment")

        return RangelandReport(
            project_id=project_id,
            grazing_pressure=grazing_label,
            grazing_pressure_score=grazing_score,
            estimated_carrying_capacity_tlu_ha=cc,
            feed_balance=feed_label,
            feed_gap_risk=feed_gap,
            livestock_climate_stress=climate_stress,
            rangeland_condition=range_label,
            rangeland_score=range_score,
            bare_ground_risk=bare_ground_risk,
            encroachment_risk=encroachment_risk,
            restoration_options=options,
            governance_entry_points=governance,
            monitoring_indicators=monitoring,
            assumptions=[
                "ASSUMPTION: Carrying capacity estimated from rangeland condition class — field livestock census required.",
                "ASSUMPTION: Overgrazing proxy derived from NDVI and indicator composites, not actual livestock count.",
                "NEEDS VALIDATION: Actual stocking rate from community livestock census.",
            ],
            confidence="low" if "livestock_census_data" in data_gaps else "medium",
            data_gaps=data_gaps[:6],
            is_mock=is_mock,
        )

    def _confidence(self) -> str:
        return "low"

    def _evidence_trail(self) -> list[str]:
        return [
            "ILRI rangeland assessment methods",
            "IGAD/ICPALD livestock climate stress assessment",
            "Sentiel-2 NDVI vegetation condition proxy",
        ]
