"""
Vegetation and Biodiversity Agent.
Detects deforestation, invasive species risk, woody encroachment,
habitat fragmentation, and recovery potential from RS indicators.
"""

from __future__ import annotations
from pydantic import BaseModel
from app.agents.base_agent import BaseAgent
from app.models.indicators import DiagnosticResult


class VegetationReport(BaseModel):
    project_id: str
    vegetation_condition: str
    vegetation_score: float           # 0=worst, 1=best
    deforestation_risk: str
    deforestation_risk_score: float
    invasive_species_risk: str
    woody_encroachment_risk: str
    habitat_fragmentation: str
    recovery_potential: str
    recovery_potential_score: float
    green_spots: list[str]            # areas with vegetation health
    degradation_hotspots: list[str]
    recommended_vegetation_actions: list[str]
    monitoring_indicators: list[str]
    confidence: str
    data_gaps: list[str]
    is_mock: bool


class VegetationBiodiversityAgent(BaseAgent):
    name = "VegetationBiodiversityAgent"

    def _execute(
        self,
        project_id: str,
        diagnostic: DiagnosticResult,
        **kwargs,
    ) -> VegetationReport:
        inds = diagnostic.indicators
        is_mock = diagnostic.is_mock

        # Core vegetation indicators
        ndvi_ind   = inds.get("ndvi")
        prod_ind   = inds.get("land_productivity")
        lcc_ind    = inds.get("land_cover_change")
        og_ind     = inds.get("overgrazing")

        ndvi_val   = ndvi_ind.value  if ndvi_ind  and not ndvi_ind.data_gap  else 0.3
        ndvi_sev   = ndvi_ind.severity_score  if ndvi_ind  and not ndvi_ind.data_gap  else 0.5
        prod_sev   = prod_ind.severity_score  if prod_ind  and not prod_ind.data_gap  else 0.5
        lcc_sev    = lcc_ind.severity_score   if lcc_ind   and not lcc_ind.data_gap   else 0.4
        og_sev     = og_ind.severity_score    if og_ind    and not og_ind.data_gap    else 0.3

        # Vegetation condition (composite NDVI + productivity)
        veg_score = round(1.0 - (ndvi_sev * 0.6 + prod_sev * 0.4), 3)
        veg_label = (
            "severely_degraded" if veg_score < 0.2 else
            "degraded"          if veg_score < 0.4 else
            "moderate"          if veg_score < 0.6 else
            "good"              if veg_score < 0.8 else "excellent"
        )

        # Deforestation risk
        defor_score = round(lcc_sev * 0.6 + ndvi_sev * 0.4, 3)
        defor_label = (
            "very_high" if defor_score > 0.7 else
            "high"      if defor_score > 0.5 else
            "moderate"  if defor_score > 0.3 else "low"
        )

        # Invasive species risk
        # Prosopis/Lantana risk when: overgrazing high, moderate NDVI (not bare, not healthy)
        invasive_risk = (
            "high"     if og_sev > 0.6 and 0.2 < ndvi_val < 0.4 else
            "moderate" if og_sev > 0.4 else "low"
        )

        # Woody encroachment (inverse — healthy but low productivity = possible encroachment)
        encroachment_risk = (
            "high"     if ndvi_sev < 0.4 and prod_sev > 0.5 else
            "moderate" if ndvi_sev < 0.5 else "low"
        )

        # Habitat fragmentation (land cover change proxy)
        frag = "high" if lcc_sev > 0.6 else "moderate" if lcc_sev > 0.3 else "low"

        # Recovery potential
        # High recovery: NDVI not yet zero, rainfall adequate, low slope, low deforestation
        slope_ind = inds.get("slope")
        rain_ind  = inds.get("rainfall")
        slope_sev = slope_ind.severity_score if slope_ind and not slope_ind.data_gap else 0.4
        rain_sev  = rain_ind.severity_score  if rain_ind  and not rain_ind.data_gap  else 0.4

        recovery_score = round(
            veg_score * 0.4 + (1 - slope_sev) * 0.3 + (1 - rain_sev) * 0.3, 3
        )
        recovery_label = (
            "high"        if recovery_score > 0.65 else
            "moderate"    if recovery_score > 0.4 else
            "low"         if recovery_score > 0.2 else "very_low"
        )

        green_spots = []
        if veg_score > 0.5:
            green_spots.append("Remnant vegetation patches — protect and use as seed sources")
        if recovery_score > 0.6:
            green_spots.append("Good recovery potential — area closure may suffice")

        hotspots = []
        if defor_score > 0.5:
            hotspots.append("Deforestation hotspot — active tree cover loss detected")
        if ndvi_sev > 0.6:
            hotspots.append("Severely degraded vegetation — bare soil expansion")

        actions = []
        if defor_score > 0.5:
            actions.append("Area closure and community forest management")
        if defor_score > 0.6:
            actions.append("Native species reforestation with local provenance seed")
        if invasive_risk == "high":
            actions.append("Invasive species mapping and control (Prosopis removal)")
        if encroachment_risk == "high":
            actions.append("Rotational grazing to prevent woody encroachment of grasslands")
        if recovery_score > 0.5:
            actions.append("Assisted natural regeneration (FMNR) where root stock exists")
        if og_sev > 0.5:
            actions.append("Managed livestock exclusion with cut-and-carry fodder systems")

        monitoring = [
            "NDVI trend (Sentinel-2 annual composites)",
            "Forest cover change (ESA WorldCover biennial)",
            "Invasive species cover (annual field transects)",
            "Basal grass cover % (dry season survey)",
            "Tree density/ha (random plot sampling)",
            "Species richness index (ecological survey every 3 years)",
        ]

        data_gaps = [k for k, v in inds.items() if v.data_gap]

        return VegetationReport(
            project_id=project_id,
            vegetation_condition=veg_label,
            vegetation_score=veg_score,
            deforestation_risk=defor_label,
            deforestation_risk_score=defor_score,
            invasive_species_risk=invasive_risk,
            woody_encroachment_risk=encroachment_risk,
            habitat_fragmentation=frag,
            recovery_potential=recovery_label,
            recovery_potential_score=recovery_score,
            green_spots=green_spots,
            degradation_hotspots=hotspots,
            recommended_vegetation_actions=actions,
            monitoring_indicators=monitoring,
            confidence="medium" if data_gaps else "high",
            data_gaps=data_gaps[:5],
            is_mock=is_mock,
        )

    def _evidence_trail(self) -> list[str]:
        return [
            "Sentinel-2 NDVI — Microsoft Planetary Computer",
            "ESA WorldCover land cover",
            "MODIS MOD13Q1 land productivity",
        ]
