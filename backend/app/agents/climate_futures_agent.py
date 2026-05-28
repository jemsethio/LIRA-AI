"""
Climate Futures Agent — LIRA-AI
================================
Tier 1 (MVP): placeholder scenario logic
Tier 2 (current): real NASA NEX GDDP CMIP6 data via Planetary Computer

Data source: nasa-nex-gddp-cmip6
  https://planetarycomputer.microsoft.com/dataset/nasa-nex-gddp-cmip6

CMIP6 models used:
  - MIROC6       — high performance for East Africa rainfall seasonality
  - MRI-ESM2-0   — strong seasonal cycle; robust African rainfall signal
  - GFDL-ESM4    — good East Africa precipitation; NOAA model

Reference: IPCC AR6 Chapter 9 (Africa), Dunning et al. 2018,
           Rowell & Chadwick 2018, Giannini et al. 2021

Architecture: all quantitative calculations are deterministic Python.
LLM provides only narrative explanation (optional, when API key configured).
"""

from __future__ import annotations
from app.agents.base_agent import BaseAgent
from app.models.climate import (
    ClimateScenario, ClimateRiskIndicator, ClimateFuturesReport,
)
from app.models.indicators import LandscapeIndicators

try:
    from app.data_adapters.cmip6_adapter import (
        fetch_cmip6_scenario, cmip6_to_lira_risk_indicators,
        HISTORICAL_YEAR, CMIP6_MODELS,
    )
    CMIP6_AVAILABLE = True
except ImportError:
    CMIP6_AVAILABLE = False


def _risk_indicator(
    name: str,
    current: str,
    projected: str,
    direction: str,
    score: float,
    scenario: ClimateScenario,
    horizon: str,
    source: str,
    is_real: bool = False,
) -> ClimateRiskIndicator:
    return ClimateRiskIndicator(
        name=name,
        current_level=current,
        projected_level=projected,
        change_direction=direction,
        risk_score=round(max(0.0, min(1.0, score)), 2),
        scenario=scenario,
        horizon=horizon,
        confidence="medium" if is_real else "low",
        data_source=source,
        is_mock=not is_real,
    )


class ClimateFuturesAgent(BaseAgent):
    name = "ClimateFuturesAgent"

    def _execute(
        self,
        project_id: str,
        indicators: LandscapeIndicators,
        scenario: ClimateScenario = ClimateScenario.ssp245,
        horizon: str = "2050",
        models: list[str] | None = None,
        bbox: list[float] | None = None,
        **kwargs,
    ) -> ClimateFuturesReport:

        # Map scenario enum to CMIP6 string
        scenario_map = {
            ClimateScenario.ssp245: "ssp245",
            ClimateScenario.ssp585: "ssp585",
            ClimateScenario.rcp45:  "ssp245",
            ClimateScenario.rcp85:  "ssp585",
            ClimateScenario.mock:   "ssp245",
        }
        cmip6_scenario = scenario_map.get(scenario, "ssp245")
        year = int(horizon) if horizon.isdigit() else 2050

        # ── Attempt real CMIP6 fetch ──────────────────────────────────────────
        cmip6_data  = None
        cmip6_hist  = None
        risk_scores = None
        is_real     = False

        if CMIP6_AVAILABLE and models != []:   # empty list [] = skip CMIP6 (fast fallback)
            try:
                use_models = models or list(CMIP6_MODELS.keys())[:1]  # 1 model for interactive speed
                print(f"    [ClimateFuturesAgent] Fetching CMIP6 {cmip6_scenario} {year}…")
                cmip6_data = fetch_cmip6_scenario(cmip6_scenario, year, use_models)
                cmip6_hist = fetch_cmip6_scenario("historical", HISTORICAL_YEAR, use_models)

                if cmip6_data.get("is_real") and cmip6_hist.get("is_real"):
                    # Add deltas
                    hist_i  = cmip6_hist["indicators"]
                    proj_i  = cmip6_data["indicators"]
                    deltas  = {}
                    for k in proj_i:
                        if k in hist_i and hist_i[k] != 0:
                            deltas[f"delta_{k}"] = round(proj_i[k] - hist_i[k], 3)
                            if abs(hist_i[k]) > 0:
                                deltas[f"pct_change_{k}"] = round(
                                    (proj_i[k] - hist_i[k]) / abs(hist_i[k]) * 100, 1
                                )
                    cmip6_data["deltas_vs_historical"] = deltas
                    risk_scores = cmip6_to_lira_risk_indicators(cmip6_hist, cmip6_data)
                    is_real = True
                    print(f"    ✓ CMIP6 real data: {cmip6_data['n_models']} models, "
                          f"pr={cmip6_data['indicators'].get('annual_precip_mm'):.0f}mm/yr")
            except Exception as exc:
                print(f"    ✗ CMIP6 fetch failed: {exc} — using eco-profile fallback")

        # ── Fallback: eco-profile based on indicators ─────────────────────────
        if not is_real:
            rainfall  = indicators.rainfall_mm_annual or 700
            slope     = indicators.slope_mean_degrees or 10
            rainfall_risk   = 0.60 if rainfall < 500 else 0.40
            erosion_risk    = min(0.35 + slope / 50, 0.90)
            drought_risk    = 0.70 if rainfall < 500 else 0.45
            heat_risk       = 0.65 if (indicators.temperature_mean_c or 20) > 25 else 0.45
            moisture_stress = drought_risk + 0.1
            vegetation_stress = moisture_stress * 0.8
            restore_stress  = (rainfall_risk + drought_risk) / 2
            risk_scores = {
                "rainfall_intensity_risk":    rainfall_risk,
                "drought_dry_spell_risk":     drought_risk,
                "heat_stress_risk":           heat_risk,
                "soil_moisture_stress":       moisture_stress,
                "erosion_runoff_risk":        erosion_risk,
                "vegetation_stress":          vegetation_stress,
                "restoration_suitability_stress": restore_stress,
                "overall_climate_risk_score": round(
                    (rainfall_risk + drought_risk + heat_risk + erosion_risk) / 4, 3
                ),
                "is_real": False,
            }

        rs  = risk_scores
        src = (
            f"NASA NEX GDDP CMIP6 — {cmip6_data.get('n_models', 0)} model ensemble "
            f"({', '.join(cmip6_data.get('model_ensemble',[])[:2])})"
            if is_real else
            "ASSUMPTION: eco-profile placeholder (CMIP6 fetch failed)"
        )

        # Build indicator objects
        ri_kwargs = {"scenario": scenario, "horizon": horizon, "source": src, "is_real": is_real}

        rainfall_ind = _risk_indicator(
            "Rainfall Intensity Risk",
            "Moderate", "High" if rs["rainfall_intensity_risk"] > 0.5 else "Moderate",
            "increasing", rs["rainfall_intensity_risk"], **ri_kwargs
        )
        drought_ind  = _risk_indicator(
            "Drought/Dry-Spell Risk",
            "Moderate", "High" if rs["drought_dry_spell_risk"] > 0.5 else "Moderate",
            "increasing", rs["drought_dry_spell_risk"], **ri_kwargs
        )
        heat_ind     = _risk_indicator(
            "Heat Stress Risk",
            "Low-Moderate", "Moderate-High",
            "increasing", rs["heat_stress_risk"], **ri_kwargs
        )
        moisture_ind = _risk_indicator(
            "Soil Moisture Stress",
            "Limiting", "Deficit",
            "increasing", rs["soil_moisture_stress"], **ri_kwargs
        )
        erosion_ind  = _risk_indicator(
            "Erosion/Runoff Risk",
            "Moderate", "Severe" if rs["erosion_runoff_risk"] > 0.6 else "High",
            "increasing", rs["erosion_runoff_risk"], **ri_kwargs
        )
        veg_ind      = _risk_indicator(
            "Vegetation Stress",
            "Moderate", "High",
            "increasing", rs["vegetation_stress"], **ri_kwargs
        )
        restore_ind  = _risk_indicator(
            "Restoration Suitability Stress",
            "Moderate", "High",
            "increasing", rs["restoration_suitability_stress"], **ri_kwargs
        )

        overall = rs.get("overall_climate_risk_score",
                         (rs["rainfall_intensity_risk"] + rs["drought_dry_spell_risk"] +
                          rs["heat_stress_risk"] + rs["erosion_runoff_risk"]) / 4)

        # Maladaptation alerts — informed by real indicators where available
        alerts: list[str] = []
        if rs["erosion_runoff_risk"] > 0.55:
            alerts.append(
                "High future erosion risk: water harvesting structures must be dimensioned "
                "for intensifying rainfall — standard designs may underperform."
            )
        if rs["drought_dry_spell_risk"] > 0.55:
            alerts.append(
                "Increasing drought frequency: tree species must prioritise drought tolerance. "
                "Avoid moisture-demanding species without supplemental water."
            )
        if rs["heat_stress_risk"] > 0.55:
            alerts.append(
                "Heat stress risk increasing: livestock breeds and crop varieties must be "
                "adapted to higher temperatures — maladaptation risk if not addressed."
            )
        if rs.get("restoration_suitability_stress", 0) > 0.5:
            alerts.append(
                "Restoration suitability window narrowing under this scenario — "
                "planting seasons may need to shift earlier in the wet season."
            )

        # Build CMIP6-specific narrative
        if is_real and cmip6_data:
            inds     = cmip6_data["indicators"]
            deltas   = cmip6_data.get("deltas_vs_historical", {})
            n_models = cmip6_data.get("n_models", 0)
            models_  = ", ".join(cmip6_data.get("model_ensemble", [])[:3])
            pr_proj  = inds.get("annual_precip_mm", 0)
            t_proj   = inds.get("temp_mean_c", 0)
            heat_d   = inds.get("heat_stress_days_35c", 0)
            dry_d    = inds.get("dry_days", 0)
            ext_r    = inds.get("extreme_rain_days", 0)
            dpr      = deltas.get("pct_change_annual_precip_mm", 0)
            dt       = deltas.get("delta_temp_mean_c_c", 0)
            narrative = (
                f"REAL CMIP6 DATA ({n_models}-model ensemble: {models_}). "
                f"Under {scenario.value} to {horizon}, Omo-Ghibe projects: "
                f"annual precipitation {pr_proj:.0f} mm/yr ({'+' if dpr>=0 else ''}{dpr:.1f}% vs baseline), "
                f"mean temperature {t_proj:.1f}°C ({'+' if dt>=0 else ''}{dt:.1f}°C), "
                f"heat stress days >35°C: {heat_d:.0f}, "
                f"dry days: {dry_d:.0f}, "
                f"extreme rain events (>50mm): {ext_r:.0f}. "
                f"Overall climate risk score: {overall:.2f}/1.0. "
                f"Source: nasa-nex-gddp-cmip6 — Microsoft Planetary Computer."
            )
        else:
            narrative = (
                f"[FALLBACK — CMIP6 not fetched] Under {scenario.value} scenario to {horizon}, "
                f"Omo-Ghibe faces moderately high climate risk (score: {overall:.2f}). "
                f"Key stressors: intensified rainfall seasonality, increased dry-spell frequency, "
                f"and heat stress. "
                f"IMPORTANT: Replace with real CMIP6 fetch — nasa-nex-gddp-cmip6 on Planetary Computer."
            )

        return ClimateFuturesReport(
            project_id=project_id,
            scenario=scenario,
            horizon=horizon,
            rainfall_intensity_risk=rainfall_ind,
            drought_dry_spell_risk=drought_ind,
            heat_stress_risk=heat_ind,
            soil_moisture_stress=moisture_ind,
            erosion_runoff_risk=erosion_ind,
            vegetation_stress=veg_ind,
            restoration_suitability_stress=restore_ind,
            overall_climate_risk_score=round(overall, 3),
            restoration_window_narrowing=(rs.get("restoration_suitability_stress", 0) > 0.5),
            maladaptation_climate_alerts=alerts,
            summary_narrative=narrative,
            is_mock=not is_real,
        )

    def _evidence_trail(self) -> list[str]:
        return [
            "nasa-nex-gddp-cmip6 — NASA / Microsoft Planetary Computer",
            "CMIP6 models: MIROC6, MRI-ESM2-0, GFDL-ESM4",
            "cil-gdpcir-cc-by — Climate Impact Lab / Planetary Computer",
            "IPCC AR6 Chapter 9 (Africa) — East Africa regional assessment",
            "Dunning et al. 2018 — East Africa future rainfall projections",
        ]

    def _assumptions(self) -> list[str]:
        return [
            "ASSUMPTION: Representative year used (not full 30-year climatology).",
            "ASSUMPTION: Ensemble mean of 2-3 models — expand to 5+ for investment-grade analysis.",
            "ASSUMPTION: CIL GDPCIR indicators pending Azure Blob credential setup.",
        ]

    def _needs_validation(self) -> list[str]:
        return [
            "Cross-validate against CORDEX-Africa regional projections for Omo-Ghibe",
            "Compare with ICPAC seasonal climate outlooks",
            "Validate against Ethiopian national met service station data",
        ]

    def _confidence(self) -> str:
        return "medium"  # upgrades to "high" when full ensemble is used

    def _uncertainty(self) -> float:
        return 0.35  # CMIP6 multi-model spread for East Africa
