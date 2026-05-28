"""
Landscape Health Intelligence Index (LHII).
Multidimensional composite index combining soil, vegetation, water,
climate, and social indicators into a transparent, configurable score.

Tracks hotspots, green-spots, and transition zones as required by the concept note.
All component weights are configurable from thresholds.yaml.
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.models.indicators import DiagnosticResult
from app.models.climate import ClimateFuturesReport
from app.models.community import CommunityIntelligence


class LHIIComponent(BaseModel):
    name: str
    score: float        # 0=worst, 1=best
    weight: float
    weighted_score: float
    data_source: str
    is_estimated: bool


class LandscapeZone(BaseModel):
    zone_type: str      # hotspot / green_spot / transition
    description: str
    priority_action: str
    spatial_note: str   # for future GIS layer integration


class LandscapeHealthIndex(BaseModel):
    project_id: str
    overall_lhii: float              # 0=severely degraded, 1=fully healthy
    lhii_class: str                  # severely_degraded / degraded / fair / good / excellent
    components: list[LHIIComponent]
    hotspots: list[LandscapeZone]
    green_spots: list[LandscapeZone]
    transition_zones: list[LandscapeZone]
    data_completeness_pct: float
    dominant_constraint: str
    recovery_potential: str
    trend_direction: str             # improving / stable / declining / unknown
    interpretation: str
    assumptions: list[str]
    is_mock: bool


# Default weights (must sum to 1.0; sourced from thresholds.yaml if available)
DEFAULT_WEIGHTS = {
    "soil_health":      0.25,
    "vegetation":       0.20,
    "water_hydrology":  0.15,
    "land_productivity":0.15,
    "climate_risk":     0.15,
    "community_social": 0.10,
}


def compute_lhii(
    diagnostic: DiagnosticResult,
    climate: Optional[ClimateFuturesReport] = None,
    community: Optional[CommunityIntelligence] = None,
    weights: Optional[dict[str, float]] = None,
) -> LandscapeHealthIndex:
    """
    Compute the Landscape Health Intelligence Index (LHII).
    """
    w = weights or DEFAULT_WEIGHTS
    inds = diagnostic.indicators

    def _sev(key: str) -> float:
        ind = inds.get(key)
        return ind.severity_score if ind and not ind.data_gap else 0.5

    # Soil health (composite of SOC, erosion, moisture)
    soil_score = round(1.0 - (
        _sev("soil_loss_rate")     * 0.40 +
        _sev("soil_organic_carbon")* 0.35 +
        _sev("soil_moisture")      * 0.25
    ), 3)

    # Vegetation score (NDVI, productivity)
    veg_score = round(1.0 - (
        _sev("ndvi")             * 0.55 +
        _sev("land_productivity") * 0.45
    ), 3)

    # Water/hydrology (slope proxy for runoff, land cover change)
    water_score = round(1.0 - (
        _sev("slope")            * 0.40 +
        _sev("land_cover_change")* 0.35 +
        _sev("soil_moisture")    * 0.25
    ), 3)

    # Land productivity
    prod_score = round(1.0 - _sev("land_productivity"), 3)

    # Climate risk (0=high risk, 1=low risk)
    climate_score = round(
        1.0 - (climate.overall_climate_risk_score if climate else 0.5), 3
    )

    # Community/social score
    social_score = 0.5  # default
    if community:
        positives = sum([
            bool(community.community_preferred_future),
            bool(community.restoration_preferences),
            bool(community.local_success_indicators),
            bool(community.grazing_rules),
        ])
        negatives = sum([
            bool(community.local_conflict_risks),
            bool(community.tenure_constraints),
            len(community.adoption_barriers) > 2,
        ])
        social_score = round(max(0, min(1, 0.5 + positives * 0.1 - negatives * 0.1)), 3)

    # Weighted LHII
    components_data = {
        "soil_health":       (soil_score,    "Soil erosion, SOC, moisture — LIRA-AI indicator engine"),
        "vegetation":        (veg_score,     "NDVI + land productivity — Sentinel-2/MODIS"),
        "water_hydrology":   (water_score,   "Slope, land cover change, soil moisture"),
        "land_productivity": (prod_score,    "MODIS MOD13Q1 — Microsoft Planetary Computer"),
        "climate_risk":      (climate_score, "Climate Futures Agent — Tier 1 scenario"),
        "community_social":  (social_score,  "Community Intelligence form input"),
    }

    components = []
    total_weight = sum(w.values())
    overall = 0.0

    for name, (score, source) in components_data.items():
        weight = w.get(name, 1 / len(components_data))
        ws = round(score * weight, 4)
        overall += ws
        components.append(LHIIComponent(
            name=name,
            score=score,
            weight=weight,
            weighted_score=ws,
            data_source=source,
            is_estimated=(name == "community_social" and not community),
        ))

    overall_lhii = round(max(0.0, min(1.0, overall)), 3)

    lhii_class = (
        "severely_degraded" if overall_lhii < 0.2 else
        "degraded"          if overall_lhii < 0.4 else
        "fair"              if overall_lhii < 0.6 else
        "good"              if overall_lhii < 0.8 else "excellent"
    )

    # Dominant constraint (lowest component score)
    lowest = min(components, key=lambda c: c.score)

    # Hotspots, green-spots, transition zones
    hotspots, green_spots, transitions = [], [], []

    if soil_score < 0.3:
        hotspots.append(LandscapeZone(
            zone_type="hotspot",
            description="Severe soil degradation — erosion and SOC loss driving landscape decline",
            priority_action="Immediate soil and water conservation works (bunds, compost, reforestation)",
            spatial_note="Target steeplands and bare-soil patches identified from DEM + WorldCover",
        ))

    if veg_score < 0.3:
        hotspots.append(LandscapeZone(
            zone_type="hotspot",
            description="Severely degraded vegetation — NDVI below 0.2 in large areas",
            priority_action="Area closure and native species reforestation",
            spatial_note="Target areas with NDVI < 0.2 from Sentinel-2 analysis",
        ))

    if soil_score > 0.6 and veg_score > 0.6:
        green_spots.append(LandscapeZone(
            zone_type="green_spot",
            description="Relatively healthy zone — good soil and vegetation condition",
            priority_action="Protect and use as reference/seed source for restoration",
            spatial_note="High-NDVI patches in less-disturbed areas — identify from Sentinel-2",
        ))

    if 0.3 <= soil_score <= 0.6 or 0.3 <= veg_score <= 0.6:
        transitions.append(LandscapeZone(
            zone_type="transition",
            description="Transition zone — moderate degradation with recovery potential",
            priority_action="Early intervention to prevent further decline",
            spatial_note="Areas with NDVI 0.25–0.4 and moderate slope — high restoration return on investment",
        ))

    # Recovery potential
    ndvi_trend = inds.get("ndvi", None)
    recovery = (
        "high"     if overall_lhii > 0.5 and climate_score > 0.4 else
        "moderate" if overall_lhii > 0.35 else
        "low"      if overall_lhii > 0.2 else "very_low"
    )

    trend_dir = "declining" if diagnostic.degradation_severity in ("severe", "very_severe") else "stable"

    interpretation = (
        f"The landscape scores {overall_lhii:.2f} on the LHII (0–1 scale), classified as '{lhii_class}'. "
        f"The dominant constraint is '{lowest.name.replace('_', ' ')}' (score: {lowest.score:.2f}). "
        f"Recovery potential is '{recovery}'. "
        f"{'Immediate intervention is critical.' if overall_lhii < 0.3 else 'Targeted restoration can prevent further decline.'}"
    )

    return LandscapeHealthIndex(
        project_id=diagnostic.project_id,
        overall_lhii=overall_lhii,
        lhii_class=lhii_class,
        components=components,
        hotspots=hotspots,
        green_spots=green_spots,
        transition_zones=transitions,
        data_completeness_pct=diagnostic.data_completeness_pct,
        dominant_constraint=lowest.name.replace("_", " "),
        recovery_potential=recovery,
        trend_direction=trend_dir,
        interpretation=interpretation,
        assumptions=[
            "ASSUMPTION: LHII weights are defaults — calibrate with local expert panel for site-specific use.",
            "ASSUMPTION: Hotspot/green-spot zones are conceptual — spatial delineation requires GIS overlay of all layers.",
            "ASSUMPTION: Social score defaults to 0.5 when community data is absent.",
        ],
        is_mock=diagnostic.is_mock,
    )
