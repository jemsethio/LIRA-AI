"""
Landscape Evidence Agent.
Orchestrates fetching of all geospatial data layers from Planetary Computer,
SoilGrids, CHIRPS, ERA5, and other sources.
Produces a harmonised LandscapeIndicators object ready for the indicator engine.
"""

from __future__ import annotations
from app.agents.base_agent import BaseAgent
from app.models.indicators import LandscapeIndicators
from app.data_adapters.planetary_computer import fetch_landscape_evidence


class LandscapeEvidenceAgent(BaseAgent):
    name = "LandscapeEvidenceAgent"

    def _execute(
        self,
        project_id: str,
        geojson_boundary: dict,
        date_range: str = "2022-01-01/2024-01-01",
        manual_overrides: dict | None = None,
        **kwargs,
    ) -> dict:
        """
        Fetch all evidence layers and return harmonised indicator dict.
        manual_overrides can supply field measurements that take priority
        over remotely sensed values.
        """
        evidence = fetch_landscape_evidence(geojson_boundary, project_id, date_range)
        indicators = evidence["indicators"]

        # Apply manual field measurement overrides (field truth > RS)
        if manual_overrides:
            for k, v in manual_overrides.items():
                if v is not None:
                    indicators[k] = v

        # Build LandscapeIndicators from combined sources
        li = LandscapeIndicators(
            project_id=project_id,
            ndvi_mean=indicators.get("ndvi_mean"),
            evi_mean=indicators.get("evi_mean"),
            ndvi_trend_5yr=indicators.get("ndvi_trend_5yr"),
            slope_mean_degrees=indicators.get("slope_mean_degrees"),
            forest_cover_pct=indicators.get("forest_cover_pct"),
            bare_soil_pct=indicators.get("bare_soil_pct"),
            land_cover_change_pct_10yr=indicators.get("land_cover_change_pct_10yr"),
            soil_organic_carbon_g_per_kg=indicators.get("soil_organic_carbon_g_per_kg"),
            soil_texture=indicators.get("soil_texture"),
            rainfall_mm_annual=indicators.get("rainfall_mm_annual"),
            temperature_mean_c=indicators.get("temperature_mean_c"),
            land_productivity_index=indicators.get("land_productivity_index"),
            is_mock=(evidence.get("real_data_layers", 0) == 0),
        )

        return {
            "landscape_indicators": li.model_dump(),
            "evidence_layers": evidence["evidence_layers"],
            "data_sources": evidence["data_sources"],
            "real_data_layers": evidence.get("real_data_layers", 0),
            "total_layers": evidence.get("total_layers", 7),
            "data_completeness_pct": round(
                evidence.get("real_data_layers", 0) / max(evidence.get("total_layers", 7), 1) * 100, 1
            ),
        }

    def _evidence_trail(self) -> list[str]:
        return [
            "Sentinel-2 L2A (10m) — Microsoft Planetary Computer",
            "Copernicus DEM GLO-30 (30m) — Microsoft Planetary Computer",
            "ESA WorldCover (10m) — Microsoft Planetary Computer",
            "SoilGrids v2.0 (250m) — ISRIC",
            "CHIRPS v2.0 (0.05°) — CHC/UCSB via Planetary Computer",
            "ERA5-Land (0.1°) — Copernicus/ECMWF via Planetary Computer",
            "MODIS MOD13Q1 v061 (250m) — Planetary Computer",
        ]

    def _confidence(self) -> str:
        return "high"

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Cloud cover threshold may exclude valid dry-season observations.",
            "ASSUMPTION: MODIS land productivity normalised to 0–1 using 90th percentile NDVI.",
            "ASSUMPTION: SoilGrids values are 250m prediction means — field verification improves accuracy.",
        ]
