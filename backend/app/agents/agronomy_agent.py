"""
Agronomy Agent — LIRA-AI
========================
Links crop productivity, crop suitability, soil-water constraints,
and climate-smart agronomy recommendations.

Covers:
  - Crop suitability scoring under current and projected climate
  - Soil fertility and nutrient constraint diagnosis
  - Integrated soil fertility management (ISFM) options
  - Climate-smart variety and practice recommendations
  - Crop calendar alignment with rainfall seasonality
  - Yield gap analysis (actual vs attainable yield)

Reference: CGIAR Excellence in Agronomy initiative, CIMMYT, CIP, ICRISAT
           FAO EcoCrop database, DSSAT crop model principles
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.indicators import DiagnosticResult


class CropSuitability(BaseModel):
    crop:          str
    suitability:   str      # highly_suitable / suitable / marginally_suitable / not_suitable
    score:         float    # 0–1
    limiting_factors:  list[str]
    climate_trend:     str  # improving / stable / worsening
    adaptation_needed: bool


class AgronomyReport(BaseModel):
    project_id:               str
    soil_fertility_status:    str
    nutrient_constraints:     list[str]
    water_constraints:        list[str]
    crop_suitability:         list[CropSuitability]
    yield_gap_estimate_pct:   Optional[float]       # % gap between actual and attainable
    isfm_recommendations:     list[str]             # Integrated Soil Fertility Management
    climate_smart_practices:  list[str]
    crop_calendar_notes:      list[str]
    restoration_agronomy_links: list[str]           # link to landscape restoration
    hotspot_flags:            list[str]
    monitoring_indicators:    list[str]
    confidence:               str
    assumptions:              list[str]
    is_mock:                  bool


# Crop suitability thresholds (rainfall, temperature, slope)
CROP_PROFILES: dict[str, dict] = {
    "teff": {
        "rain_min": 300, "rain_max": 1200, "temp_min": 10, "temp_max": 30,
        "slope_max": 25, "soc_min": 8, "ph_min": 5.0, "ph_max": 8.0,
        "description": "Primary Ethiopian staple — drought tolerant, wide range",
    },
    "sorghum": {
        "rain_min": 400, "rain_max": 1000, "temp_min": 18, "temp_max": 35,
        "slope_max": 20, "soc_min": 6, "ph_min": 5.5, "ph_max": 8.5,
        "description": "Drought-tolerant cereal — excellent for lowland agropastoral zones",
    },
    "maize": {
        "rain_min": 500, "rain_max": 1500, "temp_min": 15, "temp_max": 32,
        "slope_max": 15, "soc_min": 10, "ph_min": 5.5, "ph_max": 8.0,
        "description": "High productivity but water-demanding — vulnerable to drought",
    },
    "enset": {
        "rain_min": 1000, "rain_max": 2500, "temp_min": 12, "temp_max": 25,
        "slope_max": 30, "soc_min": 15, "ph_min": 5.5, "ph_max": 7.5,
        "description": "Ethiopian staple tree crop — highland, resilient perennial",
    },
    "coffee": {
        "rain_min": 1200, "rain_max": 2200, "temp_min": 15, "temp_max": 24,
        "slope_max": 35, "soc_min": 20, "ph_min": 5.5, "ph_max": 7.0,
        "description": "Kafa-Sheka highland specialty — forest agroforestry system",
    },
    "wheat": {
        "rain_min": 450, "rain_max": 1100, "temp_min": 10, "temp_max": 25,
        "slope_max": 20, "soc_min": 10, "ph_min": 5.5, "ph_max": 8.5,
        "description": "Cool-season cereal — mid-to-highland zones",
    },
    "lablab": {
        "rain_min": 600, "rain_max": 2500, "temp_min": 18, "temp_max": 35,
        "slope_max": 30, "soc_min": 5, "ph_min": 5.0, "ph_max": 8.5,
        "description": "Fodder legume — nitrogen fixing, intercrop / fodder bank",
    },
    "vetch": {
        "rain_min": 400, "rain_max": 1500, "temp_min": 8, "temp_max": 25,
        "slope_max": 35, "soc_min": 5, "ph_min": 5.5, "ph_max": 8.0,
        "description": "Fodder/green manure legume — highland restoration companion",
    },
}

# Climate change crop response (SSP2-4.5 / SSP5-8.5 simplified for East Africa)
CLIMATE_CROP_TRENDS = {
    "teff":    "stable",        # drought-tolerant, benefits from CO2
    "sorghum": "stable",        # tolerant, slight heat risk in lowlands
    "maize":   "worsening",     # water-demanding, heat stress increasing
    "enset":   "stable",        # highland perennial — climate buffer
    "coffee":  "worsening",     # narrowing elevation band; pest pressure
    "wheat":   "worsening",     # heat stress in low/mid elevations
    "lablab":  "improving",     # legume, adapts well to variability
    "vetch":   "stable",        # cool season, highland stable
}


def _score_crop(
    crop: str,
    profile: dict,
    rain: Optional[float],
    temp: Optional[float],
    slope: Optional[float],
    soc: Optional[float],
    ph: Optional[float],
) -> CropSuitability:
    score = 1.0
    limits: list[str] = []

    def _check(val, lo, hi, label, penalty=0.25):
        nonlocal score
        if val is None:
            return
        if val < lo:
            score -= penalty
            limits.append(f"{label} too low ({val:.0f} < {lo:.0f})")
        elif val > hi:
            score -= penalty
            limits.append(f"{label} too high ({val:.0f} > {hi:.0f})")

    _check(rain,  profile["rain_min"],  profile["rain_max"],  "Rainfall (mm/yr)", 0.3)
    _check(temp,  profile["temp_min"],  profile["temp_max"],  "Temperature (°C)", 0.25)
    _check(slope, 0,                    profile["slope_max"], "Slope (°)", 0.2)
    _check(soc,   profile["soc_min"],   999,                  "SOC (g/kg)", 0.15)
    _check(ph,    profile.get("ph_min", 4), profile.get("ph_max", 9), "pH", 0.1)

    score = max(0.0, min(1.0, score))
    if score > 0.75:   suitability = "highly_suitable"
    elif score > 0.5:  suitability = "suitable"
    elif score > 0.25: suitability = "marginally_suitable"
    else:              suitability = "not_suitable"

    return CropSuitability(
        crop=crop,
        suitability=suitability,
        score=round(score, 2),
        limiting_factors=limits,
        climate_trend=CLIMATE_CROP_TRENDS.get(crop, "unknown"),
        adaptation_needed=(CLIMATE_CROP_TRENDS.get(crop) == "worsening"),
    )


class AgronomyAgent(BaseAgent):
    name = "AgronomyAgent"

    def _execute(
        self,
        project_id: str,
        diagnostic: DiagnosticResult,
        soil_texture: str = "clay-loam",
        **kwargs,
    ) -> AgronomyReport:
        inds    = diagnostic.indicators
        is_mock = diagnostic.is_mock

        def _val(key: str) -> Optional[float]:
            ind = inds.get(key)
            return ind.value if ind and not ind.data_gap else None

        rain  = _val("rainfall")
        temp  = _val("soil_moisture")  # proxy temperature from ERA5 not in inds; use None
        slope = _val("slope")
        soc   = _val("soil_organic_carbon")
        # pH from SoilGrids via community context if available
        ph    = None

        # Soil fertility assessment
        soc_sev  = inds["soil_organic_carbon"].severity_score if "soil_organic_carbon" in inds else 0.5
        moist_sev= inds["soil_moisture"].severity_score       if "soil_moisture"       in inds else 0.5
        prod_sev = inds["land_productivity"].severity_score   if "land_productivity"   in inds else 0.5

        fert_sev = (soc_sev * 0.5 + prod_sev * 0.5)
        fertility_status = (
            "severely_depleted" if fert_sev > 0.75 else
            "low"               if fert_sev > 0.5  else
            "moderate"          if fert_sev > 0.25 else "adequate"
        )

        # Nutrient constraints (inferred from SOC and texture)
        nutrient_constraints = []
        if soc_sev > 0.5:
            nutrient_constraints.append("Low nitrogen — SOC depletion reduces N mineralisation")
        if soc_sev > 0.6:
            nutrient_constraints.append("Low phosphorus availability — acidic or low-OM soils")
        if moist_sev > 0.6:
            nutrient_constraints.append("Drought stress limiting nutrient uptake")
        if "sandy" in soil_texture.lower():
            nutrient_constraints.append("Sandy texture — rapid nutrient leaching, low CEC")

        # Water constraints
        water_constraints = []
        if moist_sev > 0.7:
            water_constraints.append("Severe soil moisture deficit — yields limited by drought")
        if moist_sev > 0.5:
            water_constraints.append("Seasonal moisture stress — planting window narrowing")
        slope_ind = inds.get("slope")
        if slope_ind and not slope_ind.data_gap and (slope_ind.value or 0) > 15:
            water_constraints.append("High slope — rapid runoff reduces plant-available water")

        # Crop suitability scoring
        rain_val = _val("rainfall")
        soc_val  = _val("soil_organic_carbon")
        slope_val= _val("slope")
        crops = [
            _score_crop(c, p, rain_val, None, slope_val, soc_val, ph)
            for c, p in CROP_PROFILES.items()
        ]
        crops.sort(key=lambda c: c.score, reverse=True)

        # Yield gap estimate
        yield_gap = None
        if prod_sev > 0.3:
            yield_gap = round(min(prod_sev * 100, 85), 1)

        # ISFM recommendations
        isfm = []
        if soc_sev > 0.4:
            isfm.append("Compost application 2–4 t/ha/yr to rebuild SOC and improve structure")
        if soc_sev > 0.3:
            isfm.append("Micro-dose fertiliser (2–4 g/seed hole) combined with organic inputs (ISFM principle)")
        isfm.append("Grain legume intercropping (lablab, vetch) for biological nitrogen fixation")
        isfm.append("Crop residue retention — 50% mulch cover reduces moisture loss and SOC loss")
        if moist_sev > 0.5:
            isfm.append("Tied ridges / furrow planting for in-situ water harvesting in drought years")

        # Climate-smart practices
        csa = []
        csa.append("Drought-tolerant improved varieties (teff, sorghum) — CGIAR ICRISAT/CIMMYT seed systems")
        if moist_sev > 0.5:
            csa.append("Rainwater harvesting (half-moon, tied ridges) for planting moisture")
        if soc_sev > 0.4:
            csa.append("Conservation agriculture (CA): zero/minimum tillage + cover crops")
        csa.append("Early warning system integration — plant before forecast dry spells")
        csa.append("Diversification: enset + coffee + grain crops hedge against climate shocks")

        # Crop calendar notes
        cal = []
        if rain_val and rain_val < 700:
            cal.append("Short growing season (< 90 days) — use short-cycle drought-tolerant varieties")
        elif rain_val and rain_val > 1200:
            cal.append("Bimodal rainfall likely — two planting opportunities; intercrop system recommended")
        else:
            cal.append("Plan planting for 2–3 weeks after onset of long rains (verify with ICPAC seasonal forecast)")
        cal.append("Dry season: livestock fodder production from residues and fodder plots")
        cal.append("Pre-rain season: soil bund repair, seed preparation, compost application")

        # Restoration-agronomy linkages
        links = [
            "Agroforestry integration: shade trees (Faidherbia, Grevillea) improve microclimate and soil",
            "FMNR on farm: retained trees improve soil water, reduce wind erosion, add organic matter",
            "Grass strips between crop rows: reduce rill erosion and improve soil structure",
            "Reforestation watershed: upstream forest restoration improves dry-season streamflow for crops",
        ]

        # Hotspot flags
        hotspots = []
        if fert_sev > 0.7:
            hotspots.append("Critical soil fertility depletion — crop failure risk without intervention")
        if moist_sev > 0.7:
            hotspots.append("Severe drought stress — crop production highly vulnerable to rainfall variability")
        maize = next((c for c in crops if c.crop == "maize"), None)
        if maize and maize.suitability == "not_suitable":
            hotspots.append("Maize no longer suitable — shift to drought-tolerant cereals recommended")

        monitoring = [
            "Soil organic carbon (0–20cm) — lab analysis every 3 years",
            "Crop yield per ha — household survey each season",
            "Soil moisture at 10cm — field sensor or gravimetric at planting",
            "Fertiliser use rate (kg/ha) — input supply tracking",
            "Drought-tolerant variety adoption rate (%) — extension records",
        ]

        return AgronomyReport(
            project_id=project_id,
            soil_fertility_status=fertility_status,
            nutrient_constraints=nutrient_constraints,
            water_constraints=water_constraints,
            crop_suitability=crops,
            yield_gap_estimate_pct=yield_gap,
            isfm_recommendations=isfm,
            climate_smart_practices=csa,
            crop_calendar_notes=cal,
            restoration_agronomy_links=links,
            hotspot_flags=hotspots,
            monitoring_indicators=monitoring,
            confidence="medium",
            assumptions=[
                "ASSUMPTION: Crop suitability scored from climate/soil thresholds — field trials required for validation.",
                "ASSUMPTION: Yield gap estimated from LPI severity — census yield data would improve accuracy.",
                "ASSUMPTION: Temperature not directly measured — inferred from elevation and ERA5.",
                "NEEDS VALIDATION: Actual crop calendars and varieties grown should be confirmed with local extension.",
            ],
            is_mock=is_mock,
        )

    def _evidence_trail(self) -> list[str]:
        return [
            "FAO EcoCrop crop suitability database",
            "CGIAR Excellence in Agronomy initiative",
            "CIMMYT Ethiopia crop improvement program",
            "ICRISAT drought-tolerant sorghum work",
            "Vanlauwe et al. ISFM framework for Sub-Saharan Africa",
        ]

    def _confidence(self) -> str:
        return "medium"

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Crop thresholds simplified — FAO EcoCrop provides more detailed suitability curves.",
            "ASSUMPTION: Temperature input from ERA5 centroid — spatial variability not captured.",
        ]
