"""
Water Doctor Agent.
Diagnoses runoff, infiltration, recharge, flood risk, gully formation,
sediment transport, and reservoir sedimentation risk.
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.indicators import DiagnosticResult


class WaterHealthReport(BaseModel):
    project_id: str
    runoff_risk: str
    runoff_risk_score: float
    infiltration_capacity: str
    gully_risk: str
    gully_risk_score: float
    flood_risk: str
    reservoir_sedimentation_risk: str
    sediment_risk_score: float
    water_balance_status: str
    downstream_risk: str
    critical_sub_catchments: list[str]
    intervention_priorities: list[str]
    monitoring_indicators: list[str]
    confidence: str
    data_gaps: list[str]
    is_mock: bool


def _runoff_cn(ndvi: float, soil_texture: str = "clay-loam", slope_deg: float = 10) -> float:
    """
    Estimate SCS Curve Number (CN) as proxy for runoff potential.
    Higher CN = more runoff. Range 0–100.
    """
    # Base CN by soil group (approximated from texture)
    base_cn = {
        "clay": 85, "clay-loam": 78, "loam": 72,
        "silt-loam": 68, "sandy-loam": 63, "sand": 55,
    }.get(soil_texture, 75)

    # Adjust for vegetation cover (NDVI proxy)
    cover_adjustment = (0.5 - ndvi) * 15  # low NDVI increases CN
    slope_adjustment = max(0, (slope_deg - 5) * 0.3)

    cn = min(98, max(35, base_cn + cover_adjustment + slope_adjustment))
    return round(cn, 1)


class WaterHydrologyAgent(BaseAgent):
    name = "WaterDoctorAgent"

    def _execute(
        self,
        project_id: str,
        diagnostic: DiagnosticResult,
        soil_texture: str = "clay-loam",
        **kwargs,
    ) -> WaterHealthReport:
        inds = diagnostic.indicators
        is_mock = diagnostic.is_mock

        # Runoff risk from slope + NDVI + soil
        slope_ind = inds.get("slope")
        ndvi_ind  = inds.get("ndvi")
        slope_val = slope_ind.value if slope_ind and not slope_ind.data_gap else 10.0
        ndvi_val  = ndvi_ind.value  if ndvi_ind  and not ndvi_ind.data_gap  else 0.3

        cn = _runoff_cn(ndvi_val, soil_texture, slope_val)
        runoff_score = round((cn - 35) / 63, 3)  # normalise 35–98 → 0–1
        runoff_label = (
            "very_high" if runoff_score > 0.75 else
            "high"      if runoff_score > 0.55 else
            "moderate"  if runoff_score > 0.35 else "low"
        )

        # Infiltration (inverse of runoff risk, adjusted for SOC)
        soc_ind = inds.get("soil_organic_carbon")
        soc_sev = soc_ind.severity_score if soc_ind and not soc_ind.data_gap else 0.5
        infil_score = 1.0 - runoff_score * 0.7 - soc_sev * 0.3
        infil_label = (
            "poor" if infil_score < 0.3 else
            "low"  if infil_score < 0.5 else
            "moderate" if infil_score < 0.7 else "good"
        )

        # Gully risk
        erosion_ind = inds.get("soil_loss_rate")
        erosion_sev = erosion_ind.severity_score if erosion_ind and not erosion_ind.data_gap else 0.5
        slope_sev   = slope_ind.severity_score if slope_ind and not slope_ind.data_gap else 0.3
        gully_score = round((erosion_sev * 0.6 + slope_sev * 0.4), 3)
        gully_label = (
            "high"     if gully_score > 0.65 else
            "moderate" if gully_score > 0.35 else "low"
        )

        # Flood risk (high runoff + flat lower slopes)
        flood_label = "moderate" if runoff_score > 0.5 and slope_val < 5 else "low"
        if runoff_score > 0.7:
            flood_label = "high"

        # Reservoir sedimentation risk
        res_ind = inds.get("overgrazing")
        res_proxy = inds.get("soil_loss_rate")
        sed_score = round(
            erosion_sev * 0.5 + gully_score * 0.3 + (
                res_ind.severity_score if res_ind and not res_ind.data_gap else 0.3
            ) * 0.2,
            3,
        )
        sed_label = (
            "very_high" if sed_score > 0.7 else
            "high"      if sed_score > 0.5 else
            "moderate"  if sed_score > 0.3 else "low"
        )

        # Water balance
        rain_ind = inds.get("rainfall")
        moist_ind = inds.get("soil_moisture")
        rain_sev  = rain_ind.severity_score  if rain_ind  and not rain_ind.data_gap  else 0.4
        moist_sev = moist_ind.severity_score if moist_ind and not moist_ind.data_gap else 0.5
        wb_score = (rain_sev + moist_sev) / 2
        wb_label = (
            "severe_deficit"     if wb_score > 0.75 else
            "deficit"            if wb_score > 0.5 else
            "marginal"           if wb_score > 0.35 else "adequate"
        )

        # Downstream risk
        downstream = (
            "high — upstream degradation will affect downstream users and reservoirs"
            if sed_score > 0.6 else
            "moderate — upstream management needed to prevent downstream deterioration"
        )

        priorities = []
        if runoff_score > 0.55:
            priorities.append("Construct runoff-diverting structures (soil bunds, half-moons)")
        if gully_score > 0.5:
            priorities.append("Gully rehabilitation with check dams and vegetation establishment")
        if infil_score < 0.4:
            priorities.append("Percolation pits and trenches to increase soil infiltration")
        if sed_score > 0.5:
            priorities.append("Upstream catchment treatment to reduce downstream sedimentation")
        if wb_score > 0.5:
            priorities.append("In-situ water harvesting for crop and livestock water security")

        monitoring = [
            "Streamflow gauge readings (dry vs wet season)",
            "Turbidity/sediment load measurements at outlet",
            "Gully head retreat rate (annual field survey)",
            "Spring and well water level trends",
            "Reservoir bathymetric survey (every 3 years)",
        ]

        data_gaps = [k for k, v in inds.items() if v.data_gap]

        return WaterHealthReport(
            project_id=project_id,
            runoff_risk=runoff_label,
            runoff_risk_score=runoff_score,
            infiltration_capacity=infil_label,
            gully_risk=gully_label,
            gully_risk_score=gully_score,
            flood_risk=flood_label,
            reservoir_sedimentation_risk=sed_label,
            sediment_risk_score=sed_score,
            water_balance_status=wb_label,
            downstream_risk=downstream,
            critical_sub_catchments=["Upper catchment steeplands", "Active gully heads"],
            intervention_priorities=priorities,
            monitoring_indicators=monitoring,
            confidence="medium" if data_gaps else "high",
            data_gaps=data_gaps[:5],
            is_mock=is_mock,
        )

    def _confidence(self) -> str:
        return "medium"

    def _evidence_trail(self) -> list[str]:
        return [
            "SCS Curve Number method (USDA TR-55)",
            "DEM-derived slope from Copernicus GLO-30",
            "NDVI cover factor from Sentinel-2",
        ]
