"""
Regeneration Pathway Generator.
Selects and packages restoration option cards into pathway bundles
based on syndrome diagnosis and climate futures context.
All logic is deterministic; LLM can be called for narrative enrichment.
"""

from __future__ import annotations
from app.models.syndromes import SyndromeDiagnosis
from app.models.climate import ClimateFuturesReport
from app.models.pathways import (
    PathwayType, RestorationOptionCard, RegenerationPathway, PathwaySet,
)

# ──────────────────────────────────────────────────────────────────────────────
# Restoration option card library (MVP: embedded; Stage 5 replaces with RAG)
# ──────────────────────────────────────────────────────────────────────────────

OPTION_LIBRARY: dict[str, RestorationOptionCard] = {
    "soil_bunds": RestorationOptionCard(
        option_name="Soil and Stone Bunds",
        target_symptoms=["High soil erosion", "Surface runoff", "Declining productivity"],
        suitable_conditions=["Slope 5–30°", "Annual rainfall > 300 mm", "Available stone/soil"],
        unsuitable_conditions=["Slope > 50°", "Very shallow soils < 20 cm"],
        land_use=["cropland", "degraded_land"],
        slope_range="5–30°",
        rainfall_range="> 300 mm/yr",
        soil_conditions=["Any texture", "Depth > 20 cm"],
        required_inputs=["Community labor", "Local stone or soil"],
        labor_requirements="high — 40–80 person-days/ha",
        community_requirements=["Land user agreement", "Terrace maintenance commitment"],
        benefits=["Reduces runoff by 40–60%", "Increases soil moisture retention", "Reduces erosion"],
        risks=["Breaching in extreme rainfall", "Outlet management needed"],
        maladaptation_risks=["May concentrate flow and cause gully if outlets poorly designed"],
        complementary_options=["grass_strips", "area_closure", "compost_application"],
        monitoring_indicators=["Rill density", "Bund integrity", "Yield trend"],
        evidence_sources=["WOCAT Ethiopia SLM database", "FAO LADA"],
        confidence_level="high",
    ),
    "area_closure": RestorationOptionCard(
        option_name="Area Closure / Exclosure",
        target_symptoms=["Bare soil", "Low vegetation cover", "Overgrazing stress"],
        suitable_conditions=["Any slope", "Community agreement possible", "Viable seed bank present"],
        unsuitable_conditions=["No alternative grazing land available", "Highly invasive species dominant"],
        land_use=["degraded_land", "rangeland", "forest_margin"],
        slope_range="Any",
        rainfall_range="> 200 mm/yr",
        soil_conditions=["Any"],
        required_inputs=["Fencing or community social agreement", "Ranger or guard"],
        labor_requirements="low — patrol only",
        community_requirements=["Strong community governance", "Alternative fodder source"],
        benefits=["Rapid vegetation recovery", "Biodiversity increase", "Erosion reduction"],
        risks=["Conflict over access restriction", "Invasion by undesirable species"],
        maladaptation_risks=["If no alternative fodder: pressure displaced to other areas"],
        complementary_options=["soil_bunds", "rotational_grazing", "improved_cookstoves"],
        monitoring_indicators=["Vegetation cover %", "Species diversity", "Biomass yield"],
        evidence_sources=["Reij & Garrity 2016", "CGIAR Ethiopia MFL reports"],
        confidence_level="high",
    ),
    "reforestation_native": RestorationOptionCard(
        option_name="Native Species Reforestation",
        target_symptoms=["Loss of forest cover", "Declining NDVI", "Soil erosion"],
        suitable_conditions=["Rainfall > 500 mm/yr", "Slope < 45°", "Available seedlings"],
        unsuitable_conditions=["Arid zones < 300 mm/yr without irrigation", "Invasive species pressure"],
        land_use=["degraded_forest", "hillside", "watershed_protection"],
        slope_range="< 45°",
        rainfall_range="> 500 mm/yr",
        soil_conditions=["Minimum 30 cm depth"],
        required_inputs=["Seedlings", "Nursery capacity", "Planting labor"],
        labor_requirements="medium — 20–40 person-days/ha/yr (Years 1–3)",
        community_requirements=["Land tenure clarity", "Protection from grazing"],
        benefits=["Carbon sequestration", "Watershed protection", "Fuelwood and fodder"],
        risks=["Low survival if drought year follows planting", "Fire risk"],
        maladaptation_risks=["Monoculture plantation increases drought vulnerability"],
        complementary_options=["area_closure", "soil_bunds", "agroforestry_parklands"],
        monitoring_indicators=["Survival rate %", "Canopy cover", "Streamflow"],
        evidence_sources=["Ethiopia National Forest Restoration Plan", "TNRC Ethiopia"],
        confidence_level="high",
    ),
    "agroforestry_parklands": RestorationOptionCard(
        option_name="Agroforestry Parklands (FMNR + Planting)",
        target_symptoms=["Low SOC", "Declining productivity", "Moisture stress"],
        suitable_conditions=["Existing root stock present (FMNR)", "Rainfall 400–1200 mm/yr"],
        unsuitable_conditions=["No root stock for FMNR", "Invasive Prosopis dominant"],
        land_use=["cropland", "agropastoral"],
        slope_range="Any",
        rainfall_range="400–1200 mm/yr",
        soil_conditions=["Any — especially benefits degraded soils"],
        required_inputs=["Farmer training", "Pruning tools", "Selected species seedlings"],
        labor_requirements="low (FMNR) to medium (planting)",
        community_requirements=["Farmer acceptance", "Tree tenure security"],
        benefits=["Soil organic matter increase", "Microclimate improvement", "Food and fodder diversification"],
        risks=["Competition with crops if not pruned", "Slow income returns"],
        maladaptation_risks=["Wrong species selection may reduce water availability"],
        complementary_options=["compost_application", "water_harvesting", "soil_bunds"],
        monitoring_indicators=["Tree density/ha", "SOC at 0–20 cm", "Crop yield"],
        evidence_sources=["World Agroforestry (ICRAF)", "FMNR Hub case studies"],
        confidence_level="high",
    ),
    "water_harvesting": RestorationOptionCard(
        option_name="In-Situ Water Harvesting (Half-Moon / Tied Ridges)",
        target_symptoms=["Moisture stress", "Low rainfall capture", "Crop failure"],
        suitable_conditions=["Semi-arid to sub-humid zones", "Flat to gentle slopes < 10°"],
        unsuitable_conditions=["Very steep slopes > 20°", "Soils with very low permeability"],
        land_use=["cropland", "rangeland", "degraded_land"],
        slope_range="< 10°",
        rainfall_range="200–600 mm/yr",
        soil_conditions=["Loamy preferred", "Sandy soils need organic inputs"],
        required_inputs=["Hand tools or mechanization", "Layout training"],
        labor_requirements="medium — 15–30 person-days/ha",
        community_requirements=["Agreement on runoff routing", "Maintenance plan"],
        benefits=["40–80% increase in plant available water", "Improved crop yields in dry years"],
        risks=["Waterlogging in high-rainfall events"],
        maladaptation_risks=["In RCP8.5 scenario: extreme events may cause overflow and gullying"],
        complementary_options=["soil_bunds", "agroforestry_parklands", "compost_application"],
        monitoring_indicators=["Soil moisture at 10 cm", "Crop yield", "Structure integrity"],
        evidence_sources=["Barron et al. 2003", "CGIAR WLE"],
        confidence_level="high",
    ),
    "rotational_grazing": RestorationOptionCard(
        option_name="Rotational Grazing / Herding Calendar Reform",
        target_symptoms=["Overgrazing", "Bare rangeland", "Declining livestock condition"],
        suitable_conditions=["Functional communal grazing governance", "Multiple grazing blocks possible"],
        unsuitable_conditions=["Individual tenure only", "Insufficient land area for rotation"],
        land_use=["rangeland", "communal_pasture"],
        slope_range="Any",
        rainfall_range="Any",
        soil_conditions=["Any"],
        required_inputs=["Community facilitation", "Grazing planning support"],
        labor_requirements="low — behavioral change and monitoring",
        community_requirements=["Bylaws or agreements", "Village council support"],
        benefits=["Vegetation recovery 30–60%", "Improved livestock body condition", "Reduced erosion"],
        risks=["Social conflict over access", "Requires sustained governance"],
        maladaptation_risks=["If no drought contingency plan: entire herd concentrated in one block in crisis"],
        complementary_options=["area_closure", "fodder_banks", "water_harvesting"],
        monitoring_indicators=["Basal grass cover", "Livestock body condition score", "Calving rate"],
        evidence_sources=["ILRI Ethiopia rangeland work", "IGAD DPAS"],
        confidence_level="medium",
    ),
    "compost_application": RestorationOptionCard(
        option_name="Compost and Organic Matter Application",
        target_symptoms=["Low SOC", "Poor soil structure", "Low productivity"],
        suitable_conditions=["Available biomass/manure", "Access to water for composting"],
        unsuitable_conditions=["Severe biomass scarcity", "No manure source"],
        land_use=["cropland", "homestead"],
        slope_range="Any",
        rainfall_range="Any",
        soil_conditions=["Especially low-SOC and sandy soils"],
        required_inputs=["Compost bins/pits", "Biomass feedstock", "Water"],
        labor_requirements="medium — 10–20 person-days/yr",
        community_requirements=["Household level — minimal coordination"],
        benefits=["SOC increase 0.1–0.5 g/kg/yr", "Improved water retention", "Yield increase"],
        risks=["Quality control required", "N-immobilization if C:N too high"],
        maladaptation_risks=["Low — minimal risk"],
        complementary_options=["agroforestry_parklands", "conservation_tillage"],
        monitoring_indicators=["SOC measurements", "Crop yield", "Compost volume produced"],
        evidence_sources=["SoilGrids baseline", "EiABC Ethiopia compost studies"],
        confidence_level="high",
    ),
    "check_dams_gully": RestorationOptionCard(
        option_name="Check Dams for Gully Control",
        target_symptoms=["Active gully erosion", "Reservoir sedimentation", "Stream incision"],
        suitable_conditions=["Active gullies", "Local stone available", "Community maintenance possible"],
        unsuitable_conditions=["Very large drainage areas without engineering design"],
        land_use=["degraded_land", "gully", "catchment"],
        slope_range="5–40°",
        rainfall_range="> 300 mm/yr",
        soil_conditions=["Any"],
        required_inputs=["Stone", "Labor", "Engineering oversight for large structures"],
        labor_requirements="high — 60–120 person-days per structure",
        community_requirements=["Maintenance commitment", "Watershed-level coordination"],
        benefits=["Sediment trapping", "Water table recharge", "Gully healing over time"],
        risks=["Failure in extreme events if undersized"],
        maladaptation_risks=["In high-intensity rainfall scenario: overflow risk if not designed for climate change"],
        complementary_options=["soil_bunds", "reforestation_native", "area_closure"],
        monitoring_indicators=["Sediment accumulation rate", "Gully head retreat", "Downstream turbidity"],
        evidence_sources=["Nyssen et al. Ethiopia gully studies", "MoA Ethiopia SLM"],
        confidence_level="high",
    ),
}


# ──────────────────────────────────────────────────────────────────────────────
# Syndrome → option mapping
# ──────────────────────────────────────────────────────────────────────────────

SYNDROME_OPTIONS: dict[str, list[str]] = {
    "erosion_productivity_decline": [
        "soil_bunds", "area_closure", "reforestation_native", "compost_application",
        "check_dams_gully", "agroforestry_parklands",
    ],
    "moisture_stress": [
        "water_harvesting", "agroforestry_parklands", "compost_application", "soil_bunds",
    ],
    "soil_carbon_depletion": [
        "compost_application", "agroforestry_parklands", "area_closure",
    ],
    "rangeland_overgrazing": [
        "rotational_grazing", "area_closure", "water_harvesting",
    ],
    "deforestation_vegetation_loss": [
        "area_closure", "reforestation_native", "agroforestry_parklands",
    ],
    "reservoir_sedimentation": [
        "check_dams_gully", "soil_bunds", "reforestation_native", "area_closure",
    ],
    "invasive_woody_encroachment": [
        "rotational_grazing", "area_closure", "agroforestry_parklands",
    ],
    "mixed_high_risk": [
        "soil_bunds", "area_closure", "reforestation_native", "water_harvesting",
        "compost_application", "check_dams_gully", "rotational_grazing",
    ],
}


def _get_options_for_diagnosis(diagnosis: SyndromeDiagnosis) -> list[RestorationOptionCard]:
    seen: set[str] = set()
    cards: list[RestorationOptionCard] = []
    for syndrome in [diagnosis.primary_syndrome] + diagnosis.secondary_syndromes:
        for opt_key in SYNDROME_OPTIONS.get(syndrome.syndrome_id, []):
            if opt_key not in seen and opt_key in OPTION_LIBRARY:
                seen.add(opt_key)
                cards.append(OPTION_LIBRARY[opt_key])
    return cards


def _make_pathway(
    pathway_type: PathwayType,
    diagnosis: SyndromeDiagnosis,
    options: list[RestorationOptionCard],
    climate: ClimateFuturesReport | None,
) -> RegenerationPathway:
    """
    Select and package options into a typed pathway.
    Deterministic filtering logic — enriched by LLM narrative later.
    """
    selected = options  # can be filtered per pathway type

    if pathway_type == PathwayType.low_cost:
        selected = [o for o in options if "low" in o.labor_requirements]
        why = "Selected for minimal labor and material cost — suitable for resource-constrained households."

    elif pathway_type == PathwayType.climate_robust:
        # Prefer options with low maladaptation risk
        selected = [o for o in options if len(o.maladaptation_risks) <= 1]
        why = (
            "Selected for resilience under projected climate variability. "
            "Avoids interventions with high maladaptation risk under intensifying rainfall."
        )

    elif pathway_type == PathwayType.food_feed_security:
        selected = [o for o in options if any(
            "yield" in b.lower() or "food" in b.lower() or "fodder" in b.lower()
            for b in o.benefits
        )]
        why = "Prioritises options with direct productivity and feed security benefits."

    elif pathway_type == PathwayType.water_sediment_reduction:
        selected = [o for o in options if any(
            "runoff" in b.lower() or "sediment" in b.lower() or "water" in b.lower()
            for b in o.benefits
        )]
        why = "Prioritises water retention, runoff reduction, and sedimentation control."

    elif pathway_type == PathwayType.biodiversity_carbon:
        selected = [o for o in options if any(
            "carbon" in b.lower() or "biodiversity" in b.lower() or "species" in b.lower()
            for b in o.benefits
        )]
        why = "Maximises biodiversity co-benefits and carbon sequestration potential."

    elif pathway_type == PathwayType.community_preferred:
        selected = [o for o in options if "community" in " ".join(o.community_requirements).lower()]
        why = "Emphasises options with strong community governance alignment and co-management."

    elif pathway_type == PathwayType.investment_ready:
        selected = [o for o in options if o.confidence_level == "high"]
        why = (
            "Focuses on high-evidence, field-validated options with clear monitoring indicators "
            "— suitable for investor and government program packaging."
        )

    if not selected:
        selected = options[:3]
        why = "Insufficient specific options — showing best-available alternatives."

    all_benefits = list({b for o in selected for b in o.benefits})
    all_tradeoffs = list({r for o in selected for r in o.risks})
    all_maladaptation = list({m for o in selected for m in o.maladaptation_risks})
    all_monitoring = list({i for o in selected for i in o.monitoring_indicators})
    all_sources = list({s for o in selected for s in o.evidence_sources})

    climate_alert = []
    if climate and climate.overall_climate_risk_score > 0.6:
        climate_alert = climate.maladaptation_climate_alerts

    return RegenerationPathway(
        pathway_type=pathway_type,
        diagnosis_summary=diagnosis.primary_syndrome.name,
        target_area=f"Priority degraded zones — {diagnosis.project_id}",
        recommended_package=selected,
        why_it_fits=why,
        enabling_conditions=[
            "Community consent and participation",
            "Land tenure clarity or community agreement",
            "Budget and material access",
        ],
        cost_category=(
            "low" if pathway_type == PathwayType.low_cost else
            "medium" if pathway_type in (PathwayType.community_preferred, PathwayType.food_feed_security) else
            "high"
        ),
        labor_burden=(
            "low" if pathway_type == PathwayType.low_cost else "medium"
        ),
        expected_benefits=all_benefits[:6],
        tradeoffs=all_tradeoffs[:4],
        maladaptation_risks=all_maladaptation[:4] + climate_alert[:2],
        policy_alignment=[
            "Ethiopia 10-Year Development Plan",
            "Ethiopia Forest Sector Development Program",
            "CRGE Strategy",
        ],
        monitoring_indicators=all_monitoring[:6],
        confidence_level=(
            "high" if pathway_type == PathwayType.investment_ready else "medium"
        ),
        evidence_sources=all_sources[:5],
        assumptions=[
            "ASSUMPTION: Cost estimates are indicative — field validation required.",
            "ASSUMPTION: Community governance capacity assumed adequate.",
            "NEEDS VALIDATION: Carrying capacity and tenure constraints.",
        ],
    )


def generate_pathways(
    diagnosis: SyndromeDiagnosis,
    climate: ClimateFuturesReport | None = None,
) -> PathwaySet:
    options = _get_options_for_diagnosis(diagnosis)

    pathway_types = [
        PathwayType.low_cost,
        PathwayType.climate_robust,
        PathwayType.food_feed_security,
        PathwayType.water_sediment_reduction,
        PathwayType.biodiversity_carbon,
        PathwayType.community_preferred,
        PathwayType.investment_ready,
    ]

    pathways = [
        _make_pathway(pt, diagnosis, options, climate)
        for pt in pathway_types
    ]

    # Recommend primary based on climate risk and syndrome
    primary = PathwayType.investment_ready.value
    if climate and climate.overall_climate_risk_score > 0.7:
        primary = PathwayType.climate_robust.value
    elif diagnosis.primary_syndrome.risk_level == "very_high":
        primary = PathwayType.investment_ready.value

    climate_score_str = f"{climate.overall_climate_risk_score:.2f}" if climate else "N/A"
    return PathwaySet(
        project_id=diagnosis.project_id,
        pathways=pathways,
        recommended_primary=primary,
        rationale=(
            f"Primary recommendation based on syndrome '{diagnosis.primary_syndrome.name}' "
            f"and climate risk score {climate_score_str}."
        ),
        is_mock=diagnosis.is_mock,
    )
