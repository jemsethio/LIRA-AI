"""
Spatial Analysis Router — LIRA-AI
====================================
Provides GeoJSON endpoints for map visualisation:
  - Zone boundaries with embedded indicator values
  - Hotspot / green-spot / transition zone features
  - Indicator raster statistics per zone
  - Soil erosion (GloSEM/RUSLE) per zone
  - Narrative generation via LLM service
  - NDVI time-series history (simulated)
  - Multi-zone aggregate statistics
  - GeoTIFF export for selected zones and layers
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from pathlib import Path
import json, copy, collections, io, re
import numpy as np

from app.data_adapters.glsem_adapter import get_soil_loss, compute_rusle_enhanced
from app.engines.landscape_health_index import compute_lhii
from app.engines.indicator_engine import run_indicator_engine
from app.engines.syndrome_classifier import classify_syndromes
from app.models.indicators import LandscapeIndicators

router = APIRouter(prefix="/spatial", tags=["Spatial Analysis"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ethiopia" / "omo_ghibe"

# Security: allowlist of valid zone IDs (T-13-01, T-13-03)
VALID_ZONE_IDS = {"highland", "midland", "lowland_pastoral", "riverine"}
_ZONE_ID_RE = re.compile(r"^[a-z_]+$")

# Maximum zones allowed in aggregate/export requests (T-13-02)
MAX_ZONE_IDS = 10

# LHII class → colour for map visualisation
LHII_COLORS = {
    "severely_degraded": "#c1121f",
    "degraded":          "#e07a2f",
    "fair":              "#e9c46a",
    "good":              "#52796f",
    "excellent":         "#2d6a4f",
}

SYNDROME_COLORS = {
    "deforestation_vegetation_loss":  "#264653",
    "erosion_productivity_decline":   "#e07a2f",
    "rangeland_overgrazing":          "#c1121f",
    "reservoir_sedimentation":        "#1a759f",
    "moisture_stress":                "#e9c46a",
    "mixed_high_risk":                "#9b2226",
}


def _load_zone(zone_id: str) -> dict:
    f = DATA_DIR / f"indicators_{zone_id}.json"
    if not f.exists():
        raise HTTPException(404, f"Zone data not found: {zone_id}")
    with open(f) as fp:
        return json.load(fp)


@router.get("/basin/geojson", summary="Full basin GeoJSON with LHII scores")
def basin_geojson() -> dict:
    """
    Returns GeoJSON FeatureCollection of all Omo-Ghibe zones,
    each feature enriched with LHII score, syndrome, and key indicators.
    Use directly in Leaflet/MapLibre.
    """
    boundary_path = DATA_DIR / "boundary.geojson"
    if not boundary_path.exists():
        raise HTTPException(404, "Boundary GeoJSON not found")

    with open(boundary_path) as f:
        base = json.load(f)

    zone_ids = ["highland", "midland", "lowland_pastoral", "riverine"]
    enriched_features = []

    for feature in base.get("features", []):
        props = feature.get("properties", {})
        zone_id = props.get("zone", "")

        if zone_id in zone_ids:
            try:
                d = _load_zone(zone_id)
                inds = d["indicators"]

                # Run LHII
                li = LandscapeIndicators(**inds)
                diagnostic = run_indicator_engine(li)
                lhii = compute_lhii(diagnostic)
                syndrome = classify_syndromes(diagnostic)

                # Enhanced soil loss via RUSLE (with forest cover for C-factor)
                rusle = compute_rusle_enhanced(
                    rainfall_mm      = inds.get("rainfall_mm_annual") or 800,
                    slope_deg        = inds.get("slope_mean_degrees")  or 10,
                    ndvi             = inds.get("ndvi_mean")           or 0.3,
                    soil_texture     = inds.get("soil_texture", "clay-loam"),
                    soc_g_per_kg     = inds.get("soil_organic_carbon_g_per_kg") or 20,
                    forest_cover_pct = inds.get("forest_cover_pct") or 0.0,
                )

                new_props = {
                    **props,
                    # Zone identity — explicitly set for frontend click handler
                    "zone_id":   zone_id,
                    "zone_name": d["meta"]["zone_name"],
                    "primary_land_use": d["meta"]["primary_land_use"],
                    # LHII
                    "lhii_score":    lhii.overall_lhii,
                    "lhii_class":    lhii.lhii_class,
                    "fill_color":    LHII_COLORS.get(lhii.lhii_class, "#7a9ab0"),
                    # Degradation
                    "degradation_severity": diagnostic.degradation_severity,
                    "health_score":         diagnostic.composite_health_score,
                    # Syndrome
                    "syndrome_id":    syndrome.primary_syndrome.syndrome_id,
                    "syndrome_name":  syndrome.primary_syndrome.name,
                    "syndrome_risk":  syndrome.primary_syndrome.risk_level,
                    "syndrome_color": SYNDROME_COLORS.get(
                        syndrome.primary_syndrome.syndrome_id, "#7a9ab0"
                    ),
                    # Key indicators (real data)
                    "ndvi":         inds.get("ndvi_mean"),
                    "soc_g_per_kg": inds.get("soil_organic_carbon_g_per_kg"),
                    "rainfall_mm":  inds.get("rainfall_mm_annual"),
                    "temp_c":       inds.get("temperature_mean_c"),
                    "slope_deg":    inds.get("slope_mean_degrees"),
                    "forest_pct":   inds.get("forest_cover_pct"),
                    # Soil erosion
                    "soil_loss_t_ha_yr":  rusle["soil_loss_rate_t_ha_yr"],
                    "rusle_method":       rusle["method"],
                    # Data quality
                    "real_data_layers": d["meta"]["real_data_layers"],
                    "data_completeness": d["meta"]["data_completeness_pct"],
                    # Zones
                    "hotspots":     [h.description for h in lhii.hotspots],
                    "green_spots":  [g.description for g in lhii.green_spots],
                }
                enriched_features.append({**feature, "properties": new_props})
            except Exception as exc:
                import traceback
                print(f"[spatial] Zone {zone_id} enrichment failed: {exc}")
                traceback.print_exc()
                enriched_features.append(feature)
        else:
            enriched_features.append(feature)

    return {
        "type": "FeatureCollection",
        "name": "Omo-Ghibe Basin — LIRA-AI Spatial Analysis",
        "features": enriched_features,
        "metadata": {
            "projection": "WGS84 (EPSG:4326)",
            "lhii_color_scale": LHII_COLORS,
            "syndrome_color_scale": SYNDROME_COLORS,
            "data_source": "LIRA-AI real data — SoilGrids, Sentinel-2, CHIRPS, ERA5",
        },
    }


@router.get("/zone/{zone_id}/indicators-geojson",
            summary="Zone indicators as GeoJSON point features")
def zone_indicators_geojson(zone_id: str) -> dict:
    """
    Returns a GeoJSON point at the zone centroid with all indicator values,
    suitable for popup display on the map.
    """
    d = _load_zone(zone_id)
    meta = d["meta"]
    inds = d["indicators"]
    centroid = meta.get("centroid", {})
    lon = centroid.get("lon", 37.0)
    lat = centroid.get("lat", 6.0)

    # Run full analysis
    li        = LandscapeIndicators(**inds)
    diag      = run_indicator_engine(li)
    lhii      = compute_lhii(diag)
    synd      = classify_syndromes(diag)

    rusle = compute_rusle_enhanced(
        rainfall_mm  = inds.get("rainfall_mm_annual") or 800,
        slope_deg    = inds.get("slope_mean_degrees")  or 10,
        ndvi         = inds.get("ndvi_mean")           or 0.3,
        soil_texture = inds.get("soil_texture", "clay-loam"),
        soc_g_per_kg = inds.get("soil_organic_carbon_g_per_kg") or 20,
    )

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "zone_id":    zone_id,
            "zone_name":  meta["zone_name"],
            "area_ha":    meta["area_ha"],
            "lhii_score": lhii.overall_lhii,
            "lhii_class": lhii.lhii_class,
            "degradation_severity": diag.degradation_severity,
            "syndrome_name": synd.primary_syndrome.name,
            "syndrome_risk": synd.primary_syndrome.risk_level,
            "causal_narrative": synd.causal_narrative,
            "soil_loss_t_ha_yr": rusle["soil_loss_rate_t_ha_yr"],
            "soil_loss_method": rusle["method"],
            "dominant_constraint": lhii.dominant_constraint,
            "recovery_potential": lhii.recovery_potential,
            "hotspots":    [h.description for h in lhii.hotspots],
            "green_spots": [g.description for g in lhii.green_spots],
            "indicators": {k: v for k, v in inds.items()
                           if v is not None and k != "project_id" and k != "is_mock"},
            "data_sources": meta.get("data_sources", {}),
            "real_data_layers": meta["real_data_layers"],
        },
    }


@router.get("/zone/{zone_id}/soil-erosion",
            summary="Soil erosion analysis (GloSEM/RUSLE)")
def zone_soil_erosion(zone_id: str) -> dict:
    """Soil loss estimate using GloSEM (if downloaded) or enhanced RUSLE."""
    d = _load_zone(zone_id)
    inds = d["indicators"]
    bbox = d["meta"]["bbox"]

    result = get_soil_loss(
        bbox         = bbox,
        rainfall_mm  = inds.get("rainfall_mm_annual"),
        slope_deg    = inds.get("slope_mean_degrees"),
        ndvi         = inds.get("ndvi_mean"),
        soil_texture = inds.get("soil_texture", "clay-loam"),
        soc_g_per_kg = inds.get("soil_organic_carbon_g_per_kg") or 20.0,
    )

    # Also run enhanced RUSLE for comparison
    if all([inds.get("rainfall_mm_annual"), inds.get("slope_mean_degrees"), inds.get("ndvi_mean")]):
        rusle = compute_rusle_enhanced(
            rainfall_mm  = inds["rainfall_mm_annual"],
            slope_deg    = inds["slope_mean_degrees"],
            ndvi         = inds["ndvi_mean"],
            soil_texture = inds.get("soil_texture", "clay-loam"),
            soc_g_per_kg = inds.get("soil_organic_carbon_g_per_kg") or 20.0,
        )
    else:
        rusle = {"soil_loss_rate_t_ha_yr": None}

    return {
        "zone_id":   zone_id,
        "zone_name": d["meta"]["zone_name"],
        "primary":   result,
        "rusle_enhanced": rusle,
        "glsem_available": result.get("is_glsem", False),
        "glsem_download_cmd": "cd backend && python scripts/download_glsem.py",
        "glsem_doi": "https://doi.org/10.5281/zenodo.6539253",
        "reference": "Borrelli et al. (2021) Nature Communications — GloSEM v1.2",
    }


@router.post("/zone/{zone_id}/narrative",
             summary="Generate LLM narrative for a zone")
def generate_zone_narrative(
    zone_id:    str,
    hf_token:   str = Query(default="", description="HuggingFace API token (free at hf.co/settings/tokens)"),
    groq_key:   str = Query(default="", description="Groq API key (free at console.groq.com)"),
    narrative_type: str = Query(default="syndrome", description="syndrome|climate|investment|pathway"),
) -> dict:
    """
    Generate LLM-enhanced narrative for a zone using open-source models.
    Provider order: Ollama (local) → Groq (free) → HuggingFace (free) → Template
    """
    from app.services.llm_service import (
        narrate_syndrome, narrate_climate_risk,
        narrate_investment_passport, narrate_pathway,
    )
    d = _load_zone(zone_id)
    inds = d["indicators"]

    li   = LandscapeIndicators(**inds)
    diag = run_indicator_engine(li)
    lhii = compute_lhii(diag)
    synd = classify_syndromes(diag)

    llm_kwargs = {"hf_token": hf_token, "groq_key": groq_key}

    if narrative_type == "syndrome":
        result = narrate_syndrome(
            syndrome_name        = synd.primary_syndrome.name,
            drivers              = synd.primary_syndrome.likely_drivers,
            symptoms             = synd.primary_syndrome.main_symptoms,
            degradation_severity = diag.degradation_severity,
            lhii_score           = lhii.overall_lhii,
            zone_name            = d["meta"]["zone_name"],
            **llm_kwargs,
        )
    elif narrative_type == "climate":
        result = narrate_climate_risk(
            zone_name  = d["meta"]["zone_name"],
            scenario   = "SSP2-4.5",
            horizon    = "2050",
            risk_scores = {"rainfall_intensity_risk": 0.55, "drought_dry_spell_risk": 0.60,
                           "heat_stress_risk": 0.50, "erosion_runoff_risk": 0.65,
                           "restoration_suitability_stress": 0.52},
            indicators  = {k: inds.get(k) for k in
                           ["rainfall_mm_annual", "temperature_mean_c", "ndvi_mean"]},
            **llm_kwargs,
        )
    else:
        result = narrate_syndrome(
            syndrome_name        = synd.primary_syndrome.name,
            drivers              = synd.primary_syndrome.likely_drivers,
            symptoms             = synd.primary_syndrome.main_symptoms,
            degradation_severity = diag.degradation_severity,
            lhii_score           = lhii.overall_lhii,
            zone_name            = d["meta"]["zone_name"],
            **llm_kwargs,
        )

    # If LLM returned None, use template
    if not result.get("text"):
        result["text"] = synd.causal_narrative
        result["provider"] = "template"

    return {
        "zone_id":       zone_id,
        "zone_name":     d["meta"]["zone_name"],
        "narrative_type": narrative_type,
        **result,
    }


def _validate_zone_id(zone_id: str) -> str:
    """Validate a single zone_id against regex and allowlist (T-13-01, T-13-03)."""
    if not _ZONE_ID_RE.match(zone_id):
        raise HTTPException(400, f"Invalid zone_id format: {zone_id!r}")
    if zone_id not in VALID_ZONE_IDS:
        raise HTTPException(400, f"Unknown zone_id: {zone_id!r}. Valid IDs: {sorted(VALID_ZONE_IDS)}")
    return zone_id


def _parse_zone_ids(zone_ids_str: str, max_zones: int = MAX_ZONE_IDS) -> list[str]:
    """Parse, deduplicate, and validate a comma-separated zone_ids string."""
    raw = [z.strip() for z in zone_ids_str.split(",") if z.strip()]
    # Cap on raw length before deduplication to prevent enumeration DoS (T-13-02)
    if len(raw) > max_zones:
        raise HTTPException(400, f"Too many zone IDs requested (max {max_zones})")
    seen: set[str] = set()
    unique: list[str] = []
    for z in raw:
        if z not in seen:
            seen.add(z)
            unique.append(z)
    for z in unique:
        _validate_zone_id(z)
    return unique


@router.get("/zone/{zone_id}/ndvi-history",
            summary="Simulated NDVI time series for a zone (2020–2025)")
def zone_ndvi_history(
    zone_id: str,
    start_year: int = Query(default=2020, ge=2010, le=2030),
    end_year:   int = Query(default=2025, ge=2010, le=2030),
) -> dict:
    """
    Returns a simulated NDVI time series for the requested zone.

    Simulation anchors on the real Sentinel-2 ndvi_mean (year 2023) and applies
    a linear degradation rate derived from land_cover_change_pct_10yr.

    Formula:
        annual_delta = -(land_cover_change_pct_10yr / 100) * ndvi_mean / 10
        ndvi(year)   = ndvi_mean + (year - 2023) * annual_delta
        clamped to [0.05, 0.90]
    """
    _validate_zone_id(zone_id)

    if start_year > end_year:
        raise HTTPException(400, "start_year must be <= end_year")

    d = _load_zone(zone_id)
    inds = d["indicators"]
    meta = d["meta"]

    anchor_ndvi = inds.get("ndvi_mean") or 0.3
    degr_pct    = inds.get("land_cover_change_pct_10yr") or 0.0

    # Spread the 10-year land-cover change linearly across individual years
    annual_delta = -(degr_pct / 100.0) * anchor_ndvi / 10.0

    series = []
    for year in range(start_year, end_year + 1):
        ndvi = anchor_ndvi + (year - 2023) * annual_delta
        ndvi = round(max(0.05, min(0.90, ndvi)), 4)
        series.append({"year": year, "ndvi": ndvi})

    return {
        "zone_id":     zone_id,
        "zone_name":   meta["zone_name"],
        "simulated":   True,
        "anchor_year": 2023,
        "anchor_ndvi": round(anchor_ndvi, 4),
        "source":      "Sentinel-2 L2A — Planetary Computer",
        "series":      series,
    }


@router.get("/zones/aggregate",
            summary="Aggregate statistics across multiple zones")
def zones_aggregate(
    zone_ids: str = Query(..., description="Comma-separated zone IDs, e.g. 'highland,midland'"),
) -> dict:
    """
    Returns arithmetic-mean indicator statistics across the requested zones.

    Fields aggregated: lhii_score, ndvi_mean, soil_loss_t_ha_yr, rainfall_mm, syndrome_id.
    Unknown or load-failing zone IDs are skipped and reported in 'failed_zones'.
    """
    ids = _parse_zone_ids(zone_ids)

    lhii_scores: list[float] = []
    ndvi_values: list[float] = []
    soil_values: list[float] = []
    rain_values: list[float] = []
    syndrome_ids: list[str] = []
    zone_summaries: list[dict] = []
    failed_zones: list[str] = []

    for zone_id in ids:
        try:
            d    = _load_zone(zone_id)
            inds = d["indicators"]
            meta = d["meta"]

            li       = LandscapeIndicators(**inds)
            diag     = run_indicator_engine(li)
            lhii     = compute_lhii(diag)
            syndrome = classify_syndromes(diag)
            rusle    = compute_rusle_enhanced(
                rainfall_mm      = inds.get("rainfall_mm_annual") or 800,
                slope_deg        = inds.get("slope_mean_degrees")  or 10,
                ndvi             = inds.get("ndvi_mean")           or 0.3,
                soil_texture     = inds.get("soil_texture", "clay-loam"),
                soc_g_per_kg     = inds.get("soil_organic_carbon_g_per_kg") or 20,
                forest_cover_pct = inds.get("forest_cover_pct") or 0.0,
            )

            lhii_scores.append(lhii.overall_lhii)
            if inds.get("ndvi_mean") is not None:
                ndvi_values.append(inds["ndvi_mean"])
            soil_values.append(rusle["soil_loss_rate_t_ha_yr"])
            if inds.get("rainfall_mm_annual") is not None:
                rain_values.append(inds["rainfall_mm_annual"])
            syndrome_ids.append(syndrome.primary_syndrome.syndrome_id)

            zone_summaries.append({
                "zone_id":    zone_id,
                "zone_name":  meta["zone_name"],
                "lhii_score": round(lhii.overall_lhii, 4),
            })

        except HTTPException:
            failed_zones.append(zone_id)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            failed_zones.append(zone_id)

    if not zone_summaries:
        raise HTTPException(404, "No zones could be loaded")

    def _mean(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    dominant_syndrome = (
        collections.Counter(syndrome_ids).most_common(1)[0][0]
        if syndrome_ids else "unknown"
    )

    return {
        "zone_ids":              ids,
        "zone_count":            len(zone_summaries),
        "mean_lhii":             _mean(lhii_scores),
        "mean_ndvi":             _mean(ndvi_values),
        "mean_soil_loss_t_ha_yr": _mean(soil_values),
        "mean_rainfall_mm":      _mean(rain_values),
        "dominant_syndrome":     dominant_syndrome,
        "zones":                 zone_summaries,
        "failed_zones":          failed_zones,
        "method":                "arithmetic_mean",
    }


@router.get("/export/geotiff",
            summary="Export zone layer as GeoTIFF (EPSG:32637)")
def export_geotiff(
    layer:    str = Query(default="ndvi",     description="Layer: ndvi | lhii | soil_loss | rainfall"),
    zone_ids: str = Query(default="highland", description="Comma-separated zone IDs"),
) -> StreamingResponse:
    """
    Rasterizes indicator values for the requested zones onto a 256x256 UTM Zone 37N
    (EPSG:32637) raster grid and returns a GeoTIFF binary stream.

    Layer mapping:
        ndvi       → ndvi_mean (Sentinel-2)
        lhii       → compute_lhii overall_lhii (computed)
        soil_loss  → rusle soil_loss_rate_t_ha_yr (computed)
        rainfall   → rainfall_mm_annual
    """
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.features import rasterize as rasterio_rasterize
    from pyproj import Transformer
    import shapely.geometry
    import shapely.ops

    valid_layers = {"ndvi", "lhii", "soil_loss", "rainfall"}
    if layer not in valid_layers:
        raise HTTPException(400, f"Unknown layer: {layer!r}. Valid: {sorted(valid_layers)}")

    ids = _parse_zone_ids(zone_ids)

    # Load boundary GeoJSON once
    boundary_path = DATA_DIR / "boundary.geojson"
    if not boundary_path.exists():
        raise HTTPException(404, "Boundary GeoJSON not found")

    with open(boundary_path) as f:
        fc = json.load(f)

    # Collect (geometry, value) pairs for matching zones
    shapes_values: list[tuple[dict, float]] = []

    for feat in fc.get("features", []):
        zid = feat.get("properties", {}).get("zone", "")
        if zid not in ids:
            continue

        try:
            d    = _load_zone(zid)
            inds = d["indicators"]

            if layer == "ndvi":
                value = float(inds.get("ndvi_mean") or 0.3)
            elif layer == "lhii":
                li   = LandscapeIndicators(**inds)
                diag = run_indicator_engine(li)
                lhii = compute_lhii(diag)
                value = float(lhii.overall_lhii)
            elif layer == "soil_loss":
                rusle = compute_rusle_enhanced(
                    rainfall_mm      = inds.get("rainfall_mm_annual") or 800,
                    slope_deg        = inds.get("slope_mean_degrees")  or 10,
                    ndvi             = inds.get("ndvi_mean")           or 0.3,
                    soil_texture     = inds.get("soil_texture", "clay-loam"),
                    soc_g_per_kg     = inds.get("soil_organic_carbon_g_per_kg") or 20,
                    forest_cover_pct = inds.get("forest_cover_pct") or 0.0,
                )
                value = float(rusle["soil_loss_rate_t_ha_yr"])
            else:  # rainfall
                value = float(inds.get("rainfall_mm_annual") or 800)

            shapes_values.append((feat["geometry"], value))

        except HTTPException:
            pass
        except Exception:
            import traceback
            traceback.print_exc()

    if not shapes_values:
        raise HTTPException(404, "No matching zone features found")

    # Compute bounding box in EPSG:4326 from all matched feature coordinates
    all_lons: list[float] = []
    all_lats: list[float] = []
    for geom, _ in shapes_values:
        coords_iter = geom.get("coordinates", [])
        # Support Polygon (one ring list) and MultiPolygon
        if geom.get("type") == "Polygon":
            for ring in coords_iter:
                for pt in ring:
                    all_lons.append(pt[0])
                    all_lats.append(pt[1])
        elif geom.get("type") == "MultiPolygon":
            for poly in coords_iter:
                for ring in poly:
                    for pt in ring:
                        all_lons.append(pt[0])
                        all_lats.append(pt[1])

    if not all_lons:
        raise HTTPException(500, "Could not extract coordinates from zone geometries")

    west  = min(all_lons)
    east  = max(all_lons)
    south = min(all_lats)
    north = max(all_lats)

    # Reproject bounding box from EPSG:4326 to EPSG:32637 (UTM Zone 37N)
    transformer_fwd = Transformer.from_crs("EPSG:4326", "EPSG:32637", always_xy=True)
    west_m,  south_m = transformer_fwd.transform(west,  south)
    east_m,  north_m = transformer_fwd.transform(east,  north)

    WIDTH  = 256
    HEIGHT = 256
    transform = from_bounds(west_m, south_m, east_m, north_m, width=WIDTH, height=HEIGHT)

    # Reproject geometry dicts to EPSG:32637 for rasterize
    def _reproject_geom(geom_dict: dict) -> dict:
        shp = shapely.geometry.shape(geom_dict)
        reprojected = shapely.ops.transform(
            lambda x, y: transformer_fwd.transform(x, y),
            shp,
        )
        return reprojected.__geo_interface__

    reprojected_shapes = [
        (_reproject_geom(geom), val)
        for geom, val in shapes_values
    ]

    # Rasterize onto fixed 256x256 grid
    data = rasterio_rasterize(
        reprojected_shapes,
        out_shape=(HEIGHT, WIDTH),
        transform=transform,
        fill=0.0,
        dtype="float32",
    )

    # Write to in-memory GeoTIFF buffer
    buf = io.BytesIO()
    with rasterio.open(
        buf, "w",
        driver="GTiff",
        dtype="float32",
        crs="EPSG:32637",
        count=1,
        width=WIDTH,
        height=HEIGHT,
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    buf.seek(0)

    safe_zone_ids = zone_ids.replace(",", "_").replace(" ", "")
    filename = f"{layer}_{safe_zone_ids}.tif"
    return StreamingResponse(
        buf,
        media_type="image/tiff",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
