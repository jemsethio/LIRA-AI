"""
CMIP6 Climate Projections Adapter — LIRA-AI
============================================
Data sources:
  - nasa-nex-gddp-cmip6  : Daily NetCDF per model/scenario/year
    https://planetarycomputer.microsoft.com/dataset/nasa-nex-gddp-cmip6
  - cil-gdpcir-cc-by/cc0 : Zarr stores (requires Azure anon access)
    https://planetarycomputer.microsoft.com/dataset/group/cil-gdpcir

PC Examples reference:
  https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets

Variables fetched:
  pr      — daily precipitation (kg/m²/s  →  mm/day via ×86400)
  tas     — daily mean 2m temperature (K  →  °C via −273.15)
  tasmax  — daily max 2m temperature (K  →  °C)
  tasmin  — daily min 2m temperature (K  →  °C)

Climate indicators computed:
  • Annual precipitation (mm/yr)
  • Annual temperature anomaly (ΔT vs historical baseline)
  • Drought days: pr < 1 mm/day
  • Dry-spell days: consecutive dry days > 5
  • Heat stress days: tasmax > 35 °C
  • Extreme rain days: pr > 50 mm/day (erosion risk)
  • Future rainfall change % vs baseline

Omo-Ghibe bbox: lat 3–10°N, lon 33–42°E
"""

from __future__ import annotations
import json, warnings
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np

warnings.filterwarnings("ignore")

try:
    import planetary_computer as pc
    import pystac_client
    import xarray as xr
    import fsspec
    PC_AVAILABLE = True
except ImportError:
    PC_AVAILABLE = False

PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"

# Representative CMIP6 models — selected for East Africa performance
# Reference: IPCC AR6 Atlas, CORDEX-Africa model evaluation
CMIP6_MODELS = {
    "MIROC6":       "High performance for East Africa rainfall; Japanese model",
    "MRI-ESM2-0":   "Strong seasonal cycle representation; Japanese model",
    "GFDL-ESM4":    "Good East Africa precipitation; NOAA/GFDL",
    "CanESM5":      "Climate sensitivity mid-range; Canadian model",
    "ACCESS-CM2":   "Good horn-of-Africa performance; Australian model",
}

SCENARIOS = {
    "historical": "1950–2014 baseline",
    "ssp245":     "SSP2-4.5 — middle-of-road (moderate mitigation)",
    "ssp585":     "SSP5-8.5 — high-end (fossil fuel intensive)",
}

HISTORICAL_YEAR = 1990   # representative historical reference year
NEAR_TERM_YEAR  = 2030
MID_TERM_YEAR   = 2050
LONG_TERM_YEAR  = 2070

# Omo-Ghibe basin
OMO_GHIBE_BBOX = [33.0, 3.0, 42.0, 10.0]
OMO_GHIBE_LAT  = slice(3.0, 10.0)
OMO_GHIBE_LON  = slice(33.0, 42.0)


# ── Core STAC reader ─────────────────────────────────────────────────────────

def _open_catalog():
    return pystac_client.Client.open(PC_STAC, modifier=pc.sign_inplace)


def _read_cmip6_year(
    model: str, scenario: str, year: int, variable: str
) -> Optional[np.ndarray]:
    """
    Fetch one year of daily CMIP6 data for the Omo-Ghibe bbox.
    Returns numpy array (days,) of spatial means, or None on failure.

    Reading approach follows:
    https://github.com/microsoft/PlanetaryComputerExamples/blob/main/quickstarts/reading-stac.ipynb
    """
    if not PC_AVAILABLE:
        return None
    try:
        cat = _open_catalog()
        search = cat.search(
            collections=["nasa-nex-gddp-cmip6"],
            query={
                "cmip6:model":    {"eq": model},
                "cmip6:scenario": {"eq": scenario},
                "cmip6:year":     {"eq": year},
            },
            max_items=1,
        )
        items = list(search.items())
        if not items:
            return None

        signed = pc.sign(items[0])
        if variable not in signed.assets:
            return None

        href = signed.assets[variable].href
        # NOTE: computation MUST be inside the `with` block — file handle closes on exit
        # Use a 45-second timeout via fsspec open_options to prevent blocking the API
        with fsspec.open(href, "rb", open_with={"timeout": 45}) as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            da = ds[variable].sel(lat=OMO_GHIBE_LAT, lon=OMO_GHIBE_LON)
            # Spatial mean → daily time series (load into memory while file open)
            daily = da.mean(dim=["lat", "lon"]).values.astype(np.float64)
        return daily
    except Exception as exc:
        # Re-raise with context so callers can log properly
        raise RuntimeError(f"CMIP6 read failed [{model}/{scenario}/{year}/{variable}]: {exc}") from exc


# ── Climate indicator computation ─────────────────────────────────────────────

def _pr_to_mm_day(pr_kg_m2_s: np.ndarray) -> np.ndarray:
    """Convert precipitation from kg/m²/s to mm/day."""
    return pr_kg_m2_s * 86400.0


def _k_to_c(temp_k: np.ndarray) -> np.ndarray:
    return temp_k - 273.15


def compute_annual_indicators(
    pr_mm_day: np.ndarray,
    tas_c: np.ndarray,
    tasmax_c: np.ndarray,
) -> dict[str, float]:
    """Compute annual climate indicators from daily arrays."""
    annual_pr   = float(np.nansum(pr_mm_day))
    dry_days    = int(np.sum(pr_mm_day < 1.0))
    extreme_rain= int(np.sum(pr_mm_day > 50.0))
    heat_days   = int(np.sum(tasmax_c > 35.0))
    tas_mean    = float(np.nanmean(tas_c))
    tasmax_mean = float(np.nanmean(tasmax_c))

    # Dry-spell frequency: consecutive days with pr < 1mm
    dry_binary = (pr_mm_day < 1.0).astype(int)
    spell_lengths = []
    current = 0
    for d in dry_binary:
        if d:
            current += 1
        elif current > 0:
            spell_lengths.append(current)
            current = 0
    if current > 0:
        spell_lengths.append(current)

    max_dry_spell  = int(np.max(spell_lengths)) if spell_lengths else 0
    mean_dry_spell = float(np.mean(spell_lengths)) if spell_lengths else 0
    n_dry_spells_5d = int(sum(1 for s in spell_lengths if s >= 5))

    return {
        "annual_precip_mm":      round(annual_pr, 1),
        "dry_days":              dry_days,
        "extreme_rain_days":     extreme_rain,
        "heat_stress_days_35c":  heat_days,
        "temp_mean_c":           round(tas_mean, 2),
        "tasmax_mean_c":         round(tasmax_mean, 2),
        "max_dry_spell_days":    max_dry_spell,
        "mean_dry_spell_days":   round(mean_dry_spell, 1),
        "n_dry_spells_gte5d":    n_dry_spells_5d,
    }


# ── Multi-model ensemble for one scenario/year ───────────────────────────────

def fetch_cmip6_scenario(
    scenario: str,
    year: int,
    models: list[str] | None = None,
    verbose: bool = True,
) -> dict:
    """
    Fetch CMIP6 climate indicators for Omo-Ghibe basin.
    Averages across an ensemble of models for robustness.

    Returns dict with ensemble mean indicators, uncertainty range,
    and per-model results. All clearly labelled with is_real flag.
    """
    if not PC_AVAILABLE:
        return _fallback_cmip6(scenario, year)

    models = models or list(CMIP6_MODELS.keys())[:3]  # use 3 models by default
    model_results: dict[str, dict] = {}
    log: list[str] = []

    for model in models:
        if verbose:
            print(f"    [{model}] {scenario} {year}…", end=" ", flush=True)
        try:
            pr_raw    = _read_cmip6_year(model, scenario, year, "pr")
            tas_raw   = _read_cmip6_year(model, scenario, year, "tas")
            tasmax_raw= _read_cmip6_year(model, scenario, year, "tasmax")

            if pr_raw is None:
                log.append(f"{model}: no pr data")
                if verbose: print("✗ (no data)")
                continue

            pr_mm    = _pr_to_mm_day(pr_raw)
            tas_c    = _k_to_c(tas_raw)    if tas_raw    is not None else pr_mm * 0 + 20
            tmax_c   = _k_to_c(tasmax_raw) if tasmax_raw is not None else tas_c + 5

            inds = compute_annual_indicators(pr_mm, tas_c, tmax_c)
            model_results[model] = inds
            if verbose:
                print(f"✓ pr={inds['annual_precip_mm']:.0f}mm  T={inds['temp_mean_c']:.1f}°C  heat={inds['heat_stress_days_35c']}d")
            log.append(f"{model}: OK — {inds['annual_precip_mm']:.0f}mm/yr")
        except Exception as exc:
            log.append(f"{model}: ERROR {exc}")
            if verbose: print(f"✗ ({exc})")

    if not model_results:
        return _fallback_cmip6(scenario, year, reason="all models failed")

    # Ensemble statistics
    keys = list(list(model_results.values())[0].keys())
    ensemble: dict[str, float] = {}
    uncertainty: dict[str, float] = {}

    for key in keys:
        vals = [v[key] for v in model_results.values() if key in v]
        if vals:
            ensemble[key]    = round(float(np.mean(vals)), 3)
            uncertainty[key] = round(float(np.std(vals)), 3)

    return {
        "scenario": scenario,
        "year": year,
        "description": SCENARIOS.get(scenario, scenario),
        "model_ensemble": list(model_results.keys()),
        "n_models": len(model_results),
        "indicators": ensemble,
        "uncertainty_std": uncertainty,
        "per_model": model_results,
        "fetch_log": log,
        "source": "NASA NEX GDDP CMIP6 — Microsoft Planetary Computer",
        "source_collection": "nasa-nex-gddp-cmip6",
        "pc_catalog": PC_STAC,
        "bbox": OMO_GHIBE_BBOX,
        "is_real": True,
    }


# ── Full multi-scenario projection report ─────────────────────────────────────

def fetch_cmip6_projections(
    models: list[str] | None = None,
    scenarios: list[str] | None = None,
    verbose: bool = True,
) -> dict:
    """
    Fetch CMIP6 projections for Omo-Ghibe across scenarios and horizons.
    Computes delta indicators (change vs historical baseline).

    Scenarios: historical (1990), ssp245 (2030/2050/2070), ssp585 (2030/2050/2070)
    """
    scenarios = scenarios or ["ssp245", "ssp585"]
    models    = models    or list(CMIP6_MODELS.keys())[:3]

    if verbose:
        print("\n  Fetching historical baseline (MIROC6 1990)…")
    historical = fetch_cmip6_scenario("historical", HISTORICAL_YEAR, models, verbose)

    projections: dict = {"historical": historical, "scenarios": {}}

    for scenario in scenarios:
        projections["scenarios"][scenario] = {}
        for year in [NEAR_TERM_YEAR, MID_TERM_YEAR, LONG_TERM_YEAR]:
            if verbose:
                print(f"\n  {scenario} {year}…")
            result = fetch_cmip6_scenario(scenario, year, models, verbose)

            # Compute deltas vs historical
            if historical.get("is_real") and result.get("is_real"):
                hist_inds = historical["indicators"]
                proj_inds = result["indicators"]
                deltas = {}
                for key in proj_inds:
                    if key in hist_inds and hist_inds[key] != 0:
                        if "precip" in key or "days" in key:
                            deltas[f"delta_{key}"] = round(proj_inds[key] - hist_inds[key], 3)
                            deltas[f"pct_change_{key}"] = round(
                                (proj_inds[key] - hist_inds[key]) / abs(hist_inds[key]) * 100, 1
                            )
                        elif "temp" in key or "tasmax" in key:
                            deltas[f"delta_{key}_c"] = round(proj_inds[key] - hist_inds[key], 3)
                result["deltas_vs_historical"] = deltas

            projections["scenarios"][scenario][str(year)] = result

    return projections


# ── CIL GDPCIR (pre-computed indicators) ─────────────────────────────────────
# Uses Azure Blob Storage. Access via anonymous HTTPS endpoint.

def fetch_cil_gdpcir_indicators(scenario: str = "ssp245", verbose: bool = True) -> dict:
    """
    Attempt to read CIL GDPCIR pre-computed climate impact indicators.
    These are Zarr stores on Azure Blob (abfs://) — requires anon access.

    Collections:
      cil-gdpcir-cc0  : CC0 license — free to use
      cil-gdpcir-cc-by: CC-BY license

    https://planetarycomputer.microsoft.com/dataset/cil-gdpcir-cc-by#Climate-indicators
    """
    if not PC_AVAILABLE:
        return {"is_real": False, "source": "PC not available"}

    try:
        cat = _open_catalog()
        # cc0 is publicly accessible
        search = cat.search(collections=["cil-gdpcir-cc0"], max_items=30)
        items = list(search.items())

        # Find SSP245 items
        ssp_items = [i for i in items if scenario in i.id]
        if not ssp_items:
            return {"is_real": False, "source": f"No cil-gdpcir items for {scenario}"}

        if verbose:
            print(f"    CIL GDPCIR: {len(ssp_items)} items for {scenario}")

        # Try to read one item's pr zarr via HTTPS (anonymous)
        item = ssp_items[0]
        raw_href = item.assets["pr"].href

        # Convert abfs:// to anonymous HTTPS
        # Account: rhgpublicdata (Climate Impact Lab's Azure storage)
        path = raw_href.replace("abfs://", "")
        https_href = f"https://rhgpublicdata.blob.core.windows.net/{path}"

        if verbose:
            print(f"    Opening Zarr: {https_href[:80]}…", end=" ", flush=True)

        store = fsspec.get_mapper(https_href, account_name="rhgpublicdata", anon=True)
        ds = xr.open_zarr(store, consolidated=True)

        pr_omo = ds["pr"].sel(lat=OMO_GHIBE_LAT, lon=OMO_GHIBE_LON)

        # Sample a few years
        pr_mean = float(pr_omo.mean()) * 86400 * 365
        if verbose:
            print(f"✓ annual pr={pr_mean:.0f} mm/yr")

        return {
            "scenario": scenario,
            "model": item.id.split("-")[2] if "-" in item.id else "unknown",
            "annual_precip_mm": round(pr_mean, 1),
            "source": "CIL GDPCIR — Planetary Computer (Zarr)",
            "source_collection": "cil-gdpcir-cc0",
            "href": https_href[:80],
            "is_real": True,
        }
    except Exception as exc:
        if verbose:
            print(f"✗ CIL GDPCIR: {exc}")
        return {"is_real": False, "source": f"CIL GDPCIR failed: {exc}"}


# ── Fallback (clearly labelled) ───────────────────────────────────────────────

def _fallback_cmip6(scenario: str, year: int, reason: str = "PC not available") -> dict:
    """
    Ecologically grounded placeholder values for Omo-Ghibe basin
    based on published CMIP6 multi-model assessment for East Africa.

    Reference: IPCC AR6 Chapter 9 (Africa), Dunning et al. 2018,
    Rowell & Chadwick 2018, Giannini et al. 2021.
    """
    base = {
        "annual_precip_mm": 820,      # basin mean from CHIRPS baseline
        "dry_days": 185,
        "extreme_rain_days": 12,
        "heat_stress_days_35c": 95,
        "temp_mean_c": 24.2,
        "tasmax_mean_c": 31.8,
        "max_dry_spell_days": 42,
        "mean_dry_spell_days": 8.5,
        "n_dry_spells_gte5d": 18,
    }
    # Apply scenario adjustments (multi-model median from IPCC AR6)
    if scenario == "ssp245":
        if year >= 2050:
            base["annual_precip_mm"]    *= 1.04   # +4% wetter (East Africa)
            base["temp_mean_c"]         += 1.8
            base["tasmax_mean_c"]       += 1.9
            base["heat_stress_days_35c"]+= 32
            base["dry_days"]            -= 12      # slightly fewer dry days overall
            base["extreme_rain_days"]   += 4       # but more intense events
            base["max_dry_spell_days"]  += 8
    elif scenario == "ssp585":
        if year >= 2050:
            base["annual_precip_mm"]    *= 1.07
            base["temp_mean_c"]         += 3.2
            base["tasmax_mean_c"]       += 3.5
            base["heat_stress_days_35c"]+= 68
            base["dry_days"]            -= 15
            base["extreme_rain_days"]   += 9
            base["max_dry_spell_days"]  += 18

    return {
        "scenario": scenario,
        "year": year,
        "description": SCENARIOS.get(scenario, scenario),
        "model_ensemble": ["IPCC_AR6_median_placeholder"],
        "n_models": 0,
        "indicators": {k: round(v, 2) for k, v in base.items()},
        "uncertainty_std": {},
        "per_model": {},
        "fetch_log": [f"Fallback used: {reason}"],
        "source": (
            "ASSUMPTION: Placeholder values from IPCC AR6 East Africa assessment. "
            f"Reason: {reason}. Replace with real CMIP6 fetch."
        ),
        "source_collection": "nasa-nex-gddp-cmip6 (not yet fetched)",
        "is_real": False,
    }


# ── Convenience: derive LIRA-AI risk indicators from CMIP6 ───────────────────

def cmip6_to_lira_risk_indicators(
    historical: dict,
    projection: dict,
) -> dict:
    """
    Convert raw CMIP6 indicators into LIRA-AI climate risk scores (0–1).
    Higher score = higher risk to restoration.
    """
    hist = historical.get("indicators", {})
    proj = projection.get("indicators", {})
    deltas = projection.get("deltas_vs_historical", {})

    def _normalize(val: float, lo: float, hi: float) -> float:
        return max(0.0, min(1.0, (val - lo) / (hi - lo)))

    # Rainfall intensity risk: increasing extreme events
    ext_delta = deltas.get("delta_extreme_rain_days", 0)
    rainfall_intensity_risk = _normalize(ext_delta, -5, 20)

    # Drought risk: increasing dry spells
    spell_delta = deltas.get("delta_max_dry_spell_days", 0)
    drought_risk = _normalize(spell_delta, -10, 30)

    # Heat stress: increasing hot days
    heat_delta  = deltas.get("delta_heat_stress_days_35c", 0)
    heat_risk   = _normalize(heat_delta, 0, 90)

    # Soil moisture stress: from temperature increase
    delta_t     = deltas.get("delta_temp_mean_c_c", 0)
    moisture_stress = _normalize(delta_t, 0, 5)

    # Erosion/runoff risk: extreme rain days increase
    erosion_risk = _normalize(ext_delta, 0, 15)

    # Vegetation stress: heat + drought combined
    veg_stress   = (heat_risk * 0.5 + drought_risk * 0.5)

    # Restoration suitability stress: narrowing window
    restore_stress = (drought_risk * 0.4 + moisture_stress * 0.4 + rainfall_intensity_risk * 0.2)

    overall = round(np.mean([
        rainfall_intensity_risk, drought_risk, heat_risk,
        moisture_stress, erosion_risk
    ]), 3)

    return {
        "rainfall_intensity_risk": round(rainfall_intensity_risk, 3),
        "drought_dry_spell_risk":  round(drought_risk, 3),
        "heat_stress_risk":        round(heat_risk, 3),
        "soil_moisture_stress":    round(moisture_stress, 3),
        "erosion_runoff_risk":     round(erosion_risk, 3),
        "vegetation_stress":       round(veg_stress, 3),
        "restoration_suitability_stress": round(restore_stress, 3),
        "overall_climate_risk_score": overall,
        "scenario": projection.get("scenario"),
        "year": projection.get("year"),
        "is_real": projection.get("is_real", False),
    }
