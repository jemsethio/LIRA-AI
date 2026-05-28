"""
Causal Diagnosis Agent — LIRA-AI
====================================
Concept note: "Causal Diagnosis Agent identifies hotspots, green-spots,
transition zones, syndromes, and driver interactions."

Wraps the causal_graph engine + syndrome classifier into a proper BaseAgent.
Provides:
  - Full causal chain graph (NetworkX → JSON)
  - Driver interaction matrix
  - Feedback loop identification
  - Hotspot / green-spot / transition zone map
  - Uncertainty and data-gap report
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.models.indicators import DiagnosticResult
from app.models.syndromes import SyndromeDiagnosis
from app.engines.causal_graph import build_causal_graph
from app.engines.syndrome_classifier import classify_syndromes
from app.engines.landscape_health_index import compute_lhii


class DriverInteraction(BaseModel):
    driver_a:      str
    driver_b:      str
    interaction:   str    # reinforcing / dampening / threshold
    strength:      str    # strong / moderate / weak
    evidence:      str


class LandscapeZoneFlag(BaseModel):
    zone_type:       str   # hotspot / green_spot / transition / unknown
    description:     str
    key_indicators:  list[str]
    recommended_action: str


class CausalDiagnosisReport(BaseModel):
    project_id:           str
    primary_syndrome:     str
    secondary_syndromes:  list[str]
    causal_narrative:     str
    causal_graph:         dict          # nodes + edges JSON
    driver_interactions:  list[DriverInteraction]
    feedback_loops:       list[str]
    hotspots:             list[LandscapeZoneFlag]
    green_spots:          list[LandscapeZoneFlag]
    transition_zones:     list[LandscapeZoneFlag]
    lhii_score:           float
    lhii_class:           str
    dominant_constraint:  str
    recovery_potential:   str
    assumptions:          list[str]
    needs_validation:     list[str]
    confidence:           str
    is_mock:              bool


# Pre-built driver interaction rules by syndrome
_DRIVER_INTERACTIONS: dict[str, list[dict]] = {
    "erosion_productivity_decline": [
        {"a":"deforestation","b":"surface_runoff","i":"reinforcing","s":"strong",
         "e":"Vegetation removal directly increases runoff coefficient (Hurni 1985)"},
        {"a":"soil_erosion","b":"soc_loss","i":"reinforcing","s":"strong",
         "e":"Topsoil removal depletes organic matter — SOC and erosion co-degrade"},
        {"a":"declining_productivity","b":"further_land_expansion","i":"reinforcing","s":"moderate",
         "e":"Vicious cycle: low yields drive expansion onto steeper, more erodible land"},
        {"a":"seasonal_rainfall","b":"rill_formation","i":"threshold","s":"strong",
         "e":"Erosion risk non-linear above ~30 mm/day intensity (IPCC AR6 Africa chapter)"},
    ],
    "rangeland_overgrazing": [
        {"a":"overstocking","b":"vegetation_removal","i":"reinforcing","s":"strong",
         "e":"Grazing pressure above carrying capacity prevents vegetation recovery"},
        {"a":"bare_soil","b":"surface_runoff","i":"reinforcing","s":"moderate",
         "e":"Compacted bare patches reduce infiltration, accelerating runoff"},
        {"a":"feed_gap","b":"grazing_pressure","i":"reinforcing","s":"strong",
         "e":"Drought-induced feed gap pushes herds onto recovering areas, preventing rest"},
    ],
    "deforestation_vegetation_loss": [
        {"a":"fuelwood_demand","b":"forest_clearance","i":"reinforcing","s":"strong",
         "e":"Household energy demand drives incremental forest margin clearing"},
        {"a":"agricultural_expansion","b":"forest_clearance","i":"reinforcing","s":"strong",
         "e":"Population pressure and market access incentivise crop area expansion"},
        {"a":"reduced_canopy","b":"soil_moisture_loss","i":"reinforcing","s":"moderate",
         "e":"Canopy removal reduces ET recycling, drying the local climate"},
    ],
}

_FEEDBACK_LOOPS: dict[str, list[str]] = {
    "erosion_productivity_decline": [
        "Erosion → SOC loss → lower water retention → moisture stress → lower vegetation cover → more erosion",
        "Low productivity → expanded cultivation on steep slopes → deforestation → more erosion",
    ],
    "rangeland_overgrazing": [
        "Overgrazing → bare soil → compaction → reduced infiltration → surface runoff → erosion → less grass → more overgrazing",
        "Feed gap → early offtake failure → herd concentration in few areas → localised overgrazing hotspot",
    ],
    "deforestation_vegetation_loss": [
        "Deforestation → reduced rainfall interception → drier soils → less forest regeneration potential",
        "Fuelwood demand → incremental clearance → fire risk increases → faster forest loss",
    ],
}


class CausalDiagnosisAgent(BaseAgent):
    name = "CausalDiagnosisAgent"

    def _execute(
        self,
        project_id: str,
        diagnostic: DiagnosticResult,
        **kwargs,
    ) -> CausalDiagnosisReport:

        is_mock = diagnostic.is_mock

        # ── Syndrome classification ───────────────────────────────────────────
        syndrome_diag: SyndromeDiagnosis = classify_syndromes(diagnostic)

        # ── Causal graph ─────────────────────────────────────────────────────
        graph = build_causal_graph(syndrome_diag)

        # ── LHII ─────────────────────────────────────────────────────────────
        lhii = compute_lhii(diagnostic)

        # ── Driver interactions ───────────────────────────────────────────────
        primary_sid = syndrome_diag.primary_syndrome.syndrome_id
        raw_interactions = _DRIVER_INTERACTIONS.get(primary_sid, [])
        interactions = [
            DriverInteraction(
                driver_a=d["a"], driver_b=d["b"],
                interaction=d["i"], strength=d["s"], evidence=d["e"],
            )
            for d in raw_interactions
        ]

        # ── Feedback loops ────────────────────────────────────────────────────
        loops = _FEEDBACK_LOOPS.get(primary_sid, [
            "No pre-built feedback loops for this syndrome — expert review recommended."
        ])

        # ── Zone flags from LHII ──────────────────────────────────────────────
        hotspots = [
            LandscapeZoneFlag(
                zone_type="hotspot",
                description=h.description,
                key_indicators=["LHII < 0.3", "severity > severe"],
                recommended_action=h.priority_action,
            )
            for h in lhii.hotspots
        ]
        green_spots = [
            LandscapeZoneFlag(
                zone_type="green_spot",
                description=g.description,
                key_indicators=["LHII > 0.6", "positive NDVI trend"],
                recommended_action=g.priority_action,
            )
            for g in lhii.green_spots
        ]
        transitions = [
            LandscapeZoneFlag(
                zone_type="transition",
                description=t.description,
                key_indicators=["LHII 0.3–0.6", "moderate degradation"],
                recommended_action=t.priority_action,
            )
            for t in lhii.transition_zones
        ]

        return CausalDiagnosisReport(
            project_id=project_id,
            primary_syndrome=syndrome_diag.primary_syndrome.name,
            secondary_syndromes=[s.name for s in syndrome_diag.secondary_syndromes],
            causal_narrative=syndrome_diag.causal_narrative,
            causal_graph=graph,
            driver_interactions=interactions,
            feedback_loops=loops,
            hotspots=hotspots,
            green_spots=green_spots,
            transition_zones=transitions,
            lhii_score=lhii.overall_lhii,
            lhii_class=lhii.lhii_class,
            dominant_constraint=lhii.dominant_constraint,
            recovery_potential=lhii.recovery_potential,
            assumptions=syndrome_diag.assumptions,
            needs_validation=syndrome_diag.needs_validation,
            confidence=syndrome_diag.primary_syndrome.confidence,
            is_mock=is_mock,
        )

    def _evidence_trail(self) -> list[str]:
        return [
            "Hurni (1985) — Ethiopian highlands causal erosion chains",
            "ILRI rangeland feedback loop modelling — East Africa",
            "LIRA-AI causal chain templates (8 syndrome types)",
            "CGIAR LHII composite index — 6 weighted components",
        ]

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Causal chains use pre-built templates — participatory causal mapping recommended.",
            "ASSUMPTION: Feedback loop strengths are qualitative — quantitative modelling needs field data.",
            "NEEDS VALIDATION: Hotspot/green-spot boundaries are conceptual — GIS overlay required.",
        ]

    def _confidence(self) -> str:
        return "medium"
