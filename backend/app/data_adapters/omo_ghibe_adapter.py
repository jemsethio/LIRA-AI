"""
Omo-Ghibe Basin Data Adapter — LIRA-AI (all fixes applied)
===========================================================
Uses the fixed planetary_computer.py adapter with:
  - EPSG:32637 (UTM Zone 37N) for all raster operations
  - rescale=False + manual unit conversion
  - CHIRPS via rasterio /vsicurl/ (CHC public server)
  - ERA5 via Open-Meteo free API
  - SoilGrids confirmed working (no depth= in URL)
"""

from __future__ import annotations
import warnings
import numpy as np

warnings.filterwarnings("ignore")

from app.data_adapters.planetary_computer import (
    fetch_sentinel2_ndvi,
    fetch_ndvi_trend,
    fetch_dem_topography,
    fetch_land_cover,
    fetch_modis_productivity,
    fetch_soilgrids,
    fetch_chirps_rainfall,
    fetch_era5_climate,
)


def fetch_zone_evidence(
    zone_id: str,
    bbox: list[float],
    sample_bbox: list[float],
    centroid: tuple[float, float],
    date_range: str = "2022-06-01/2023-10-31",
) -> dict:
    """
    Fetch all evidence layers for one Omo-Ghibe landscape zone.
    Uses fixed adapters — all real data where available.
    """
    lon, lat = centroid

    print(f"    SoilGrids…",  end=" ", flush=True)
    soil   = fetch_soilgrids(lon, lat)
    print(f"{'✓' if soil['is_real'] else '✗'}  ", end="", flush=True)

    print(f"Sentinel-2 NDVI…", end=" ", flush=True)
    ndvi   = fetch_sentinel2_ndvi(sample_bbox, date_range=date_range)
    print(f"{'✓' if ndvi['is_real'] else '✗'}  ", end="", flush=True)

    print(f"DEM…", end=" ", flush=True)
    dem    = fetch_dem_topography(sample_bbox)
    print(f"{'✓' if dem['is_real'] else '✗'}  ", end="", flush=True)

    print(f"WorldCover…", end=" ", flush=True)
    lc     = fetch_land_cover(sample_bbox)
    print(f"{'✓' if lc['is_real'] else '✗'}  ", end="", flush=True)

    print(f"MODIS LPI…", end=" ", flush=True)
    lpi    = fetch_modis_productivity(sample_bbox, date_range=date_range)
    print(f"{'✓' if lpi['is_real'] else '✗'}  ", end="", flush=True)

    print(f"CHIRPS…", end=" ", flush=True)
    chirps = fetch_chirps_rainfall(bbox, start_year=2014, end_year=2023)
    print(f"{'✓' if chirps['is_real'] else '✗'}  ", end="", flush=True)

    print(f"ERA5…", end=" ", flush=True)
    era5   = fetch_era5_climate(bbox, year=2023)
    print(f"{'✓' if era5['is_real'] else '✗'}")

    real_count = sum(
        d.get("is_real", False)
        for d in [soil, ndvi, dem, lc, lpi, chirps, era5]
    )

    return {
        "zone_id":    zone_id,
        "bbox":       bbox,
        "sample_bbox":sample_bbox,
        "centroid":   {"lon": lon, "lat": lat},
        "layers": {
            "soil":            soil,
            "sentinel2_ndvi":  ndvi,
            "dem":             dem,
            "worldcover":      lc,
            "modis_lpi":       lpi,
            "chirps":          chirps,
            "era5":            era5,
        },
        "flat_indicators": {
            # Vegetation
            "ndvi_mean":               ndvi.get("ndvi_mean"),
            "evi_mean":                ndvi.get("evi_mean"),
            "ndvi_std":                ndvi.get("ndvi_std"),
            "land_productivity_index": lpi.get("land_productivity_index"),
            # Topography
            "slope_mean_degrees":  dem.get("slope_mean_degrees"),
            "elevation_mean_m":    dem.get("elevation_mean_m"),
            "relief_m":            dem.get("relief_m"),
            # Land cover
            "forest_cover_pct":    lc.get("forest_cover_pct"),
            "bare_soil_pct":       lc.get("bare_soil_pct"),
            "cropland_pct":        lc.get("cropland_pct"),
            # Soil (SoilGrids real)
            "soil_organic_carbon_g_per_kg": soil.get("soil_organic_carbon_g_per_kg"),
            "clay_pct":            soil.get("clay_pct"),
            "silt_pct":            soil.get("silt_pct"),
            "sand_pct":            soil.get("sand_pct"),
            "ph":                  soil.get("ph"),
            "bulk_density_g_cm3":  soil.get("bulk_density_g_cm3"),
            "soil_texture":        soil.get("soil_texture"),
            "nitrogen_g_per_kg":   soil.get("nitrogen_g_per_kg"),
            # Climate
            "rainfall_mm_annual":      chirps.get("rainfall_mm_annual"),
            "rainfall_trend_mm_per_yr":chirps.get("rainfall_trend_mm_per_yr"),
            "temperature_mean_c":      era5.get("temperature_mean_c"),
            "temperature_max_mean_c":  era5.get("temperature_max_mean_c"),
        },
        "real_data_layers":      real_count,
        "total_layers":          7,
        "data_completeness_pct": round(real_count / 7 * 100, 1),
    }
