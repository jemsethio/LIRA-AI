"""
Causal Futures Graph — links symptoms → drivers → interactions → future risks
→ intervention options → expected benefits → tradeoffs → investment readiness.
Stored as a JSON-serialisable dict; NetworkX used for analysis.
"""

from __future__ import annotations
import networkx as nx
from app.models.syndromes import SyndromeDiagnosis


# Pre-built causal chain templates keyed by syndrome_id
CAUSAL_CHAINS: dict[str, list[tuple[str, str]]] = {
    "erosion_productivity_decline": [
        ("deforestation/bare_slopes", "reduced_vegetation_cover"),
        ("high_intensity_rainfall", "surface_runoff"),
        ("reduced_vegetation_cover", "surface_runoff"),
        ("surface_runoff", "soil_erosion"),
        ("soil_erosion", "topsoil_loss"),
        ("topsoil_loss", "reduced_SOC"),
        ("reduced_SOC", "declining_productivity"),
        ("declining_productivity", "food_insecurity"),
        ("food_insecurity", "further_land_expansion"),
        ("further_land_expansion", "deforestation/bare_slopes"),
        # Interventions
        ("soil_bund_construction", "reduced_surface_runoff"),
        ("reforestation", "reduced_vegetation_cover"),
        ("reduced_surface_runoff", "reduced_soil_erosion"),
        ("reduced_soil_erosion", "improved_productivity"),
    ],
    "moisture_stress": [
        ("declining_rainfall", "soil_moisture_deficit"),
        ("deforestation", "reduced_ET_recycling"),
        ("reduced_ET_recycling", "soil_moisture_deficit"),
        ("soil_moisture_deficit", "crop_failure"),
        ("crop_failure", "food_insecurity"),
        ("crop_failure", "increased_grazing_pressure"),
        # Interventions
        ("water_harvesting", "reduced_soil_moisture_deficit"),
        ("agroforestry", "improved_ET_recycling"),
    ],
    "soil_carbon_depletion": [
        ("continuous_tillage", "SOC_breakdown"),
        ("crop_residue_burning", "SOC_loss"),
        ("SOC_breakdown", "poor_soil_structure"),
        ("poor_soil_structure", "reduced_water_retention"),
        ("reduced_water_retention", "moisture_stress"),
        ("moisture_stress", "declining_productivity"),
        # Interventions
        ("compost_application", "SOC_increase"),
        ("conservation_tillage", "reduced_SOC_breakdown"),
        ("SOC_increase", "improved_water_retention"),
    ],
    "rangeland_overgrazing": [
        ("overstocking", "vegetation_removal"),
        ("vegetation_removal", "bare_soil_patches"),
        ("bare_soil_patches", "soil_compaction"),
        ("soil_compaction", "reduced_infiltration"),
        ("reduced_infiltration", "surface_runoff"),
        ("surface_runoff", "erosion"),
        ("vegetation_removal", "bush_encroachment"),
        ("bush_encroachment", "reduced_grass_cover"),
        # Interventions
        ("rotational_grazing", "vegetation_recovery"),
        ("exclosures", "vegetation_recovery"),
        ("vegetation_recovery", "reduced_bare_soil"),
    ],
    "deforestation_vegetation_loss": [
        ("agricultural_expansion", "forest_clearance"),
        ("charcoal_demand", "forest_clearance"),
        ("forest_clearance", "reduced_canopy_cover"),
        ("reduced_canopy_cover", "increased_surface_runoff"),
        ("increased_surface_runoff", "erosion"),
        ("reduced_canopy_cover", "reduced_rainfall_interception"),
        # Interventions
        ("community_forest_management", "reduced_forest_clearance"),
        ("improved_cookstoves", "reduced_charcoal_demand"),
        ("area_closure", "vegetation_recovery"),
    ],
}


def build_causal_graph(diagnosis: SyndromeDiagnosis) -> dict:
    """
    Build a NetworkX DiGraph from syndrome-matched causal chains,
    return as JSON-serialisable node/edge dict for frontend visualisation.
    """
    G = nx.DiGraph()

    active_syndromes = [diagnosis.primary_syndrome] + diagnosis.secondary_syndromes
    active_ids = [s.syndrome_id for s in active_syndromes]

    for sid in active_ids:
        chains = CAUSAL_CHAINS.get(sid, [])
        for source, target in chains:
            G.add_edge(source, target, syndrome=sid)

    # Assign node types for colouring in the frontend
    def classify_node(n: str) -> str:
        if any(k in n for k in ["intervention", "bund", "reforestation", "water_harvesting",
                                  "agroforestry", "compost", "conservation", "rotational",
                                  "exclosure", "community_forest", "improved_cook", "area_closure"]):
            return "intervention"
        if any(k in n for k in ["food_insecurity", "crop_failure", "declining_productivity",
                                  "erosion", "moisture_stress", "bush_encroachment"]):
            return "impact"
        if any(k in n for k in ["deforestation", "overstocking", "tillage", "burning",
                                  "expansion", "demand", "rainfall"]):
            return "driver"
        return "process"

    nodes = [
        {"id": n, "type": classify_node(n), "label": n.replace("_", " ").title()}
        for n in G.nodes()
    ]
    edges = [
        {"source": u, "target": v, "syndrome": d.get("syndrome", "unknown")}
        for u, v, d in G.edges(data=True)
    ]

    return {
        "project_id": diagnosis.project_id,
        "nodes": nodes,
        "edges": edges,
        "active_syndromes": active_ids,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
