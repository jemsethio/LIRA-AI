"""
Soil Doctor Agent.
Diagnoses erosion severity, SOC decline, soil moisture constraints,
fertility status, and soil health. Combines rule-based classification
with SoilGrids data and field-calibrated RUSLE-based erosion estimates.
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.indicators import DiagnosticResult


class SoilHealthReport(BaseModel):
    project_id: str
    erosion_risk: str
    erosion_severity_score: float
    soc_status: str
    soc_severity_score: float
    soil_moisture_status: str
    moisture_severity_score: float
    soil_fertility_status: str
    soil_structural_integrity: str
    hotspot_flags: list[str]
    green_spot_flags: list[str]
    transition_zones: list[str]
    restoration_entry_points: list[str]
    data_gaps: list[str]
    confidence: str
    assumptions: list[str]
    is_mock: bool


# RUSLE-based erosion estimation constants for Ethiopian highlands
# R factor range: 600–1200 (MJ·mm·ha⁻¹·h⁻¹·yr⁻¹)
SLOPE_K_FACTOR = {  # K factor by texture (t·h·MJ⁻¹·mm⁻¹)
    "clay":       0.20,
    "clay-loam":  0.30,
    "loam":       0.32,
    "silt-loam":  0.37,
    "sandy-loam": 0.27,
    "sand":       0.15,
}


def _estimate_usle_erosion(
    rainfall_mm: float,
    slope_deg: float,
    ndvi: float,
    soil_texture: str = "clay-loam",
) -> float:
    """
    Simplified RUSLE estimate (t/ha/yr).
    A = R × K × LS × C × P
    """
    # R factor: empirical for Ethiopian highlands (Hurni 1985)
    R = 0.55 * rainfall_mm if rainfall_mm else 400

    # K factor from texture
    K = SLOPE_K_FACTOR.get(soil_texture, 0.30)

    # LS factor (slope length simplified to 100m standard)
    slope_pct = slope_deg * 1.745  # approx degrees to %
    LS = (100 / 22.1) ** 0.4 * (slope_pct / 9) ** 1.3

    # C factor from NDVI (cover factor)
    ndvi = max(ndvi, 0.01)
    C = max(0.05, 1.0 - ndvi * 1.5)  # low NDVI = high C factor

    # P factor (conservation practice) — assume no conservation works
    P = 1.0

    return round(R * K * LS * C * P, 1)


class SoilAgent(BaseAgent):
    name = "SoilDoctorAgent"

    def _execute(
        self,
        project_id: str,
        diagnostic: DiagnosticResult,
        soil_texture: str = "clay-loam",
        rainfall_mm: Optional[float] = None,
        **kwargs,
    ) -> SoilHealthReport:
        inds = diagnostic.indicators
        is_mock = diagnostic.is_mock

        # Erosion
        erosion_ind = inds.get("soil_loss_rate")
        erosion_sev = erosion_ind.severity_score if erosion_ind and not erosion_ind.data_gap else 0.5
        erosion_cat = erosion_ind.category if erosion_ind and not erosion_ind.data_gap else "unknown"

        # If soil_loss_rate is missing, estimate from RUSLE
        if erosion_ind and erosion_ind.data_gap:
            ndvi_val = inds.get("ndvi")
            slope_val = inds.get("slope")
            if ndvi_val and not ndvi_val.data_gap and slope_val and not slope_val.data_gap:
                estimated = _estimate_usle_erosion(
                    rainfall_mm or 600,
                    slope_val.value or 10,
                    ndvi_val.value or 0.3,
                    soil_texture,
                )
                erosion_cat = (
                    "very_severe" if estimated > 50 else
                    "severe"      if estimated > 20 else
                    "moderate"    if estimated > 10 else
                    "low"         if estimated > 2 else "very_low"
                )
                erosion_sev = min(estimated / 60, 1.0)

        # SOC
        soc_ind = inds.get("soil_organic_carbon")
        soc_sev = soc_ind.severity_score if soc_ind and not soc_ind.data_gap else 0.5
        soc_cat = soc_ind.category if soc_ind and not soc_ind.data_gap else "unknown"

        # Moisture
        moist_ind = inds.get("soil_moisture")
        moist_sev = moist_ind.severity_score if moist_ind and not moist_ind.data_gap else 0.5
        moist_cat = moist_ind.category if moist_ind and not moist_ind.data_gap else "unknown"

        # Composite fertility proxy (SOC + productivity)
        prod_ind = inds.get("land_productivity")
        prod_sev = prod_ind.severity_score if prod_ind and not prod_ind.data_gap else 0.5
        fertility_sev = (soc_sev + prod_sev) / 2
        fertility_status = (
            "severely_depleted" if fertility_sev > 0.75 else
            "low"               if fertility_sev > 0.5 else
            "moderate"          if fertility_sev > 0.25 else "adequate"
        )

        # Structural integrity (slope + erosion proxy)
        slope_ind = inds.get("slope")
        slope_sev = slope_ind.severity_score if slope_ind and not slope_ind.data_gap else 0.3
        struct_sev = (erosion_sev + slope_sev) / 2
        struct_status = (
            "severely_compromised" if struct_sev > 0.7 else
            "at_risk"              if struct_sev > 0.4 else "stable"
        )

        # Hotspot flags
        hotspots = []
        if erosion_sev > 0.6:
            hotspots.append("Active erosion hotspot — immediate intervention required")
        if soc_sev > 0.7:
            hotspots.append("Severely SOC-depleted — soil organic matter intervention critical")
        if moist_sev > 0.7:
            hotspots.append("Severe soil moisture deficit — water harvesting priority")

        # Green spot flags (areas of relative health)
        green_spots = []
        if erosion_sev < 0.3 and soc_sev < 0.3:
            green_spots.append("Low-degradation zone — candidate for reduced-intensity intervention")
        if prod_sev < 0.3:
            green_spots.append("Relatively productive zone — protect and build on existing health")

        # Transition zones
        transitions = []
        if 0.3 < erosion_sev < 0.6:
            transitions.append("Moderate erosion — transition zone between stable and degraded")
        if 0.3 < soc_sev < 0.6:
            transitions.append("Intermediate SOC — intervention can prevent further decline")

        # Restoration entry points
        entry_points = []
        if erosion_sev > 0.5:
            entry_points.append("Soil bunds and check dams for runoff control")
        if soc_sev > 0.5:
            entry_points.append("Compost application and agroforestry for SOC rebuild")
        if moist_sev > 0.5:
            entry_points.append("In-situ water harvesting and mulching for moisture retention")
        if slope_sev > 0.5:
            entry_points.append("Slope stabilisation through vegetation cover and terracing")

        data_gaps = [k for k, v in inds.items() if v.data_gap]

        return SoilHealthReport(
            project_id=project_id,
            erosion_risk=erosion_cat.replace("_", " "),
            erosion_severity_score=round(erosion_sev, 3),
            soc_status=soc_cat.replace("_", " "),
            soc_severity_score=round(soc_sev, 3),
            soil_moisture_status=moist_cat.replace("_", " "),
            moisture_severity_score=round(moist_sev, 3),
            soil_fertility_status=fertility_status,
            soil_structural_integrity=struct_status,
            hotspot_flags=hotspots,
            green_spot_flags=green_spots,
            transition_zones=transitions,
            restoration_entry_points=entry_points,
            data_gaps=data_gaps[:5],
            confidence="medium" if data_gaps else "high",
            assumptions=[
                "ASSUMPTION: RUSLE estimation uses simplified slope-length assumption (100m).",
                "ASSUMPTION: Vegetation cover factor derived from NDVI — field calibration improves accuracy.",
            ],
            is_mock=is_mock,
        )

    def _confidence(self) -> str:
        return "medium"

    def _evidence_trail(self) -> list[str]:
        return [
            "Hurni 1985 — RUSLE calibration for Ethiopian highlands",
            "SoilGrids v2.0 — ISRIC",
            "LIRA-AI threshold engine",
        ]
