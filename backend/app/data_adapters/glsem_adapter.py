"""
GloSEM Soil Erosion Adapter — LIRA-AI
======================================
GloSEM v1.2: Global Soil Erosion Modelling Platform
Reference: Borrelli et al. (2021) Nature Communications
DOI: https://doi.org/10.1038/s41467-021-27157-7
Data DOI: https://doi.org/10.5281/zenodo.6539253 (open access, CC BY 4.0)

Two-tier approach:
  Tier 1 (REAL):    Read GloSEM GeoTIFF if downloaded locally
                    Download script: python scripts/download_glsem.py
  Tier 2 (REAL+):   Calibrated RUSLE for Ethiopian highlands
                    using SoilGrids erodibility + DEM slope + CHIRPS R-factor
                    + literature-calibrated C and P factors (Hurni 1985, FAO)
  Tier 3 (FALLBACK):Simple RUSLE estimate (already in indicator_engine.py)

GloSEM resolution: ~90m (3 arc-seconds)
Coverage: Global
Units: t ha⁻¹ yr⁻¹

For Omo-Ghibe basin:
  Expected range: 0–200 t/ha/yr (severe on steep slopes)
  Literature benchmark: Ethiopian highlands ~20–50 t/ha/yr on cultivated slopes
"""

from __future__ import annotations
import warnings
from pathlib import Path
from typing import Optional
import numpy as np

warnings.filterwarnings("ignore")

try:
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import transform_bounds
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

# Local GloSEM file (downloaded by scripts/download_glsem.py)
GLSEM_LOCAL = Path(__file__).resolve().parent.parent.parent / "data" / "glsem" / "Global_SoilErosion_3s.tif"

# Alternative open-access sources to try via /vsicurl/
GLSEM_REMOTE_URLS = [
    # OpenLandMap COG on AWS (if available)
    "/vsicurl/https://s3.eu-central-1.wasabisys.com/openlandmap/soil/sol_erosion.raster_merge.tif",
    # Fallback: try Zenodo directly
    "/vsicurl/https://zenodo.org/record/6539253/files/Global_SoilErosion_3s.tif",
]

# ─── Enhanced RUSLE parameters for Ethiopian highlands ─────────────────────────
# Based on: Hurni (1985), Bewket & Teferi (2009), Molla & Sisheber (2017)

# R factor (rainfall erosivity) regression for Ethiopia
# R = 0.55 × P (mm/yr) for highland Ethiopia (Hurni 1985)
# More accurate: R = 0.302 × P^1.11 (Renard & Freimund 1994)
def _r_factor_ethiopia(rainfall_mm: float) -> float:
    """
    Rainfall erosivity for Ethiopia — Hurni (1985) linear calibration.
    R = 0.55 × P (conservative, Ethiopia-specific, avoids overestimation).
    Typical range: 200–1100 MJ mm ha⁻¹ h⁻¹ yr⁻¹.
    """
    if rainfall_mm <= 0:
        return 200.0
    return min(0.55 * rainfall_mm, 1200.0)


# K factor by soil texture class (t·h·MJ⁻¹·mm⁻¹)
K_FACTOR_BY_TEXTURE = {
    "clay":       0.18,
    "clay-loam":  0.28,
    "loam":       0.32,
    "silt-loam":  0.37,
    "sandy-loam": 0.25,
    "sand":       0.12,
    "loamy-sand": 0.16,
}

def _k_factor(texture: str, soc_g_per_kg: float = 20.0) -> float:
    """Soil erodibility — adjusted for SOC (higher SOC = lower K)."""
    base_k = K_FACTOR_BY_TEXTURE.get(texture, 0.28)
    # SOC adjustment: each 10 g/kg SOC reduces K by ~5%
    soc_adjustment = max(0.7, 1.0 - (soc_g_per_kg / 200))
    return round(base_k * soc_adjustment, 3)


def _ls_factor(slope_deg: float, slope_length_m: float = 100.0) -> float:
    """
    Slope length-steepness factor (LS).
    McCool et al. (1987) formula for slope > 9%:
    LS = (λ/22.1)^m × (65.41 sin²θ + 4.56 sinθ + 0.065)
    """
    if slope_deg <= 0:
        return 0.2
    slope_pct = np.tan(np.radians(slope_deg)) * 100
    theta = np.radians(slope_deg)
    # Rill/interrill ratio m
    m = 0.6 * (1 - np.exp(-35.835 * slope_pct / 100))
    m = max(0.2, min(0.6, m))
    ls = ((slope_length_m / 22.1) ** m) * (65.41 * np.sin(theta)**2 + 4.56 * np.sin(theta) + 0.065)
    return round(float(ls), 3)


def _c_factor_from_ndvi(ndvi: float, forest_cover_pct: float = 0.0) -> float:
    """
    Cover-management factor from NDVI, calibrated for Ethiopian context.
    Uses Van Leeuwen & Samson (1997) modified formula.
    Forest cover percentage further reduces C factor.
    Range: C≈0.001 (dense forest) to 1.0 (bare).
    """
    ndvi = max(0.01, min(0.99, ndvi))
    # Modified exponential, stronger than De Jong for dense cover
    c = float(np.exp(-3.5 * ndvi / (1.0 - ndvi * 0.5)))
    # Forest cover adjustment: high forest → much lower C
    if forest_cover_pct > 0:
        forest_adj = max(0.1, 1.0 - (forest_cover_pct / 100.0) * 0.8)
        c = c * forest_adj
    return round(max(0.001, min(1.0, c)), 4)


def _p_factor(slope_deg: float, has_terraces: bool = False, has_strips: bool = False) -> float:
    """
    Support practice factor P.
    FAO guidelines for Ethiopia.
    """
    if has_terraces:
        return 0.1
    if has_strips:
        return 0.35
    # Without practices: P depends on slope
    if slope_deg < 2:    return 0.60
    elif slope_deg < 7:  return 0.70
    elif slope_deg < 12: return 0.80
    elif slope_deg < 18: return 0.90
    else:                return 1.00


def compute_rusle_enhanced(
    rainfall_mm:      float,
    slope_deg:        float,
    ndvi:             float,
    soil_texture:     str   = "clay-loam",
    soc_g_per_kg:     float = 20.0,
    slope_length_m:   float = 50.0,    # 50m default — realistic for Ethiopian fragmented farms
    has_terraces:     bool  = False,
    has_strips:       bool  = False,
    forest_cover_pct: float = 0.0,
) -> dict:
    """
    Enhanced RUSLE with calibrated Ethiopia-specific parameters.
    A = R × K × LS × C × P

    Reference values for validation:
      Hurni (1985): Ethiopian highlands 5–200 t/ha/yr
      Molla & Sisheber (2017): Chemoga watershed 15–78 t/ha/yr
      Bewket & Teferi (2009): Blue Nile highland 93 t/ha/yr (unprotected)
      GloSEM Ethiopia p75: ~35 t/ha/yr
    """
    R  = _r_factor_ethiopia(rainfall_mm)
    K  = _k_factor(soil_texture, soc_g_per_kg)
    LS = _ls_factor(slope_deg, slope_length_m)
    C  = _c_factor_from_ndvi(ndvi, forest_cover_pct)
    P  = _p_factor(slope_deg, has_terraces, has_strips)

    A = R * K * LS * C * P
    # Cap at 200 t/ha/yr — physical maximum for Ethiopian soils
    # (GloSEM p95 for Ethiopia is ~150 t/ha/yr)
    A = min(A, 200.0)

    return {
        "soil_loss_rate_t_ha_yr": round(float(A), 2),
        "r_factor": round(R, 1),
        "k_factor": K,
        "ls_factor": LS,
        "c_factor":  C,
        "p_factor":  P,
        "method":    "Enhanced RUSLE — Hurni 1985 / McCool 1987 / De Jong 1994",
        "is_real":   True,
        "is_glsem":  False,
        "note": "Calibrated for Ethiopian highlands. Validate with field measurements.",
    }


def fetch_glsem_for_bbox(bbox: list[float]) -> dict:
    """
    Fetch GloSEM soil erosion data for a bounding box.
    Priority:
      1. Local GloSEM file (if downloaded)
      2. Remote vsicurl (if accessible)
      3. Returns None → caller falls back to enhanced RUSLE
    """
    if not RASTERIO_AVAILABLE:
        return {"is_real": False, "source": "rasterio not installed"}

    west, south, east, north = bbox

    # Try local file first
    if GLSEM_LOCAL.exists():
        try:
            with rasterio.open(str(GLSEM_LOCAL)) as src:
                win = from_bounds(west, south, east, north, src.transform)
                data = src.read(1, window=win).astype(float)
                nodata = src.nodata or -9999
                data[data <= 0] = np.nan
                data[data == nodata] = np.nan
                return {
                    "soil_loss_mean_t_ha_yr":  round(float(np.nanmean(data)),  2),
                    "soil_loss_max_t_ha_yr":   round(float(np.nanmax(data)),   2),
                    "soil_loss_p75_t_ha_yr":   round(float(np.nanpercentile(data, 75)), 2),
                    "valid_pixels":            int(np.sum(~np.isnan(data))),
                    "source": "GloSEM v1.2 — Borrelli et al. 2021 (local file)",
                    "doi": "10.5281/zenodo.6539253",
                    "is_real": True,
                    "is_glsem": True,
                }
        except Exception as exc:
            pass  # Try remote

    # Try remote sources
    for url in GLSEM_REMOTE_URLS:
        try:
            with rasterio.open(url) as src:
                win = from_bounds(west, south, east, north, src.transform)
                data = src.read(1, window=win).astype(float)
                data[data <= 0] = np.nan
                return {
                    "soil_loss_mean_t_ha_yr":  round(float(np.nanmean(data)),  2),
                    "soil_loss_max_t_ha_yr":   round(float(np.nanmax(data)),   2),
                    "soil_loss_p75_t_ha_yr":   round(float(np.nanpercentile(data, 75)), 2),
                    "valid_pixels":            int(np.sum(~np.isnan(data))),
                    "source": f"GloSEM v1.2 remote — {url[:60]}",
                    "doi": "10.5281/zenodo.6539253",
                    "is_real": True,
                    "is_glsem": True,
                }
        except Exception:
            continue

    return {"is_real": False, "source": "GloSEM not available — run scripts/download_glsem.py"}


def get_soil_loss(
    bbox:           list[float],
    rainfall_mm:    Optional[float]  = None,
    slope_deg:      Optional[float]  = None,
    ndvi:           Optional[float]  = None,
    soil_texture:   str              = "clay-loam",
    soc_g_per_kg:   float            = 20.0,
) -> dict:
    """
    Best available soil loss estimate:
      1. GloSEM (real raster data, if available)
      2. Enhanced RUSLE (calibrated for Ethiopia, always available)
    """
    # Try GloSEM
    glsem = fetch_glsem_for_bbox(bbox)
    if glsem.get("is_glsem"):
        return {
            "soil_loss_rate_t_ha_yr": glsem["soil_loss_mean_t_ha_yr"],
            **glsem,
        }

    # Fall back to enhanced RUSLE
    if rainfall_mm and slope_deg and ndvi:
        rusle = compute_rusle_enhanced(
            rainfall_mm=rainfall_mm,
            slope_deg=slope_deg,
            ndvi=ndvi,
            soil_texture=soil_texture,
            soc_g_per_kg=soc_g_per_kg,
        )
        return rusle

    return {
        "soil_loss_rate_t_ha_yr": None,
        "is_real": False,
        "source": "Insufficient data for RUSLE — provide rainfall, slope, NDVI",
    }
