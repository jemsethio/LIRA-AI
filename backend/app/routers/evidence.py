"""
Evidence Cloud router.
Handles fetching real data from Planetary Computer, SoilGrids, CHIRPS, ERA5,
and orchestrating the Landscape Evidence Agent.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Any, Optional
from app.agents.landscape_evidence_agent import LandscapeEvidenceAgent
from app.agents.soil_agent import SoilAgent
from app.agents.water_agent import WaterHydrologyAgent
from app.agents.vegetation_agent import VegetationBiodiversityAgent
from app.agents.rangeland_agent import RangelandLivestockAgent
from app.data_adapters.planetary_computer import (
    fetch_sentinel2_ndvi, fetch_dem_topography, fetch_land_cover,
    fetch_soilgrids, fetch_chirps_rainfall, fetch_landscape_evidence,
)

router = APIRouter(prefix="/evidence", tags=["Evidence Cloud"])

_evidence_cache: dict[str, dict] = {}
_specialist_reports: dict[str, dict] = {}

_evidence_agent  = LandscapeEvidenceAgent()
_soil_agent      = SoilAgent()
_water_agent     = WaterHydrologyAgent()
_veg_agent       = VegetationBiodiversityAgent()
_range_agent     = RangelandLivestockAgent()


class EvidenceRequest(BaseModel):
    project_id: str
    geojson_boundary: dict[str, Any]
    date_range: str = "2022-01-01/2024-01-01"
    manual_overrides: Optional[dict[str, Any]] = None


@router.post("/fetch", status_code=202)
def fetch_evidence(req: EvidenceRequest) -> dict:
    """
    Fetch all Planetary Computer data layers for a landscape.
    Returns a combined evidence dict with indicators and source provenance.
    """
    output = _evidence_agent.run(
        project_id=req.project_id,
        geojson_boundary=req.geojson_boundary,
        date_range=req.date_range,
        manual_overrides=req.manual_overrides,
    )
    if not output.success:
        raise HTTPException(status_code=500, detail=output.result)

    _evidence_cache[req.project_id] = output.result
    return {
        "project_id": req.project_id,
        "status": "fetched",
        "real_data_layers": output.result.get("real_data_layers", 0),
        "total_layers": output.result.get("total_layers", 7),
        "data_completeness_pct": output.result.get("data_completeness_pct", 0),
        "evidence": output.result,
        "evidence_trail": output.evidence_trail,
        "assumptions": output.assumptions,
    }


@router.get("/layers/{project_id}")
def get_evidence_layers(project_id: str) -> dict:
    """Return cached evidence layers for a project."""
    ev = _evidence_cache.get(project_id)
    if not ev:
        raise HTTPException(status_code=404, detail="No evidence fetched — run /evidence/fetch first")
    return ev


@router.get("/sources/catalog")
def list_data_sources() -> dict:
    """List all integrated data sources with metadata."""
    return {
        "sources": [
            {
                "name": "Sentinel-2 L2A",
                "type": "Multispectral satellite (10m)",
                "variables": ["NDVI", "EVI", "land cover proxies"],
                "temporal": "2017–present, 5-day revisit",
                "provider": "ESA Copernicus via Microsoft Planetary Computer",
                "catalog_url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a",
                "collection": "sentinel-2-l2a",
            },
            {
                "name": "Copernicus DEM GLO-30",
                "type": "Digital Elevation Model (30m)",
                "variables": ["elevation", "slope", "aspect", "terrain roughness"],
                "temporal": "Static (2011–2015 acquisition)",
                "provider": "ESA Copernicus via Microsoft Planetary Computer",
                "catalog_url": "https://planetarycomputer.microsoft.com/dataset/cop-dem-glo-30",
                "collection": "cop-dem-glo-30",
            },
            {
                "name": "ESA WorldCover",
                "type": "Global Land Cover (10m)",
                "variables": ["forest", "cropland", "bare soil", "grassland", "shrubland"],
                "temporal": "2020, 2021 (biennial)",
                "provider": "ESA Copernicus via Microsoft Planetary Computer",
                "catalog_url": "https://planetarycomputer.microsoft.com/dataset/esa-worldcover",
                "collection": "esa-worldcover",
            },
            {
                "name": "Landsat Collection 2 L2",
                "type": "Multispectral satellite (30m)",
                "variables": ["NDVI time series", "land cover change", "surface reflectance"],
                "temporal": "1972–present, 16-day revisit (Landsat 8/9)",
                "provider": "USGS / NASA via Microsoft Planetary Computer",
                "catalog_url": "https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2",
                "collection": "landsat-c2-l2",
            },
            {
                "name": "MODIS MOD13Q1 v061",
                "type": "Vegetation indices (250m)",
                "variables": ["NDVI", "EVI", "land productivity"],
                "temporal": "2000–present, 16-day composites",
                "provider": "NASA LP DAAC via Microsoft Planetary Computer",
                "catalog_url": "https://planetarycomputer.microsoft.com/dataset/modis-13Q1-061",
                "collection": "modis-13Q1-061",
            },
            {
                "name": "CHIRPS v2.0",
                "type": "Rainfall dataset (0.05°)",
                "variables": ["daily rainfall", "annual totals", "drought indices"],
                "temporal": "1981–near present, daily",
                "provider": "CHC/UCSB via Microsoft Planetary Computer",
                "catalog_url": "https://planetarycomputer.microsoft.com/dataset/chirps-2.0",
                "collection": "chirps-2.0",
                "note": "Long record ideal for LIRA-AI trend analysis and drought monitoring",
            },
            {
                "name": "ERA5-Land",
                "type": "Climate reanalysis (0.1°)",
                "variables": ["temperature", "soil moisture", "evapotranspiration", "wind"],
                "temporal": "1950–present, hourly",
                "provider": "ECMWF Copernicus via Planetary Computer",
                "catalog_url": "https://planetarycomputer.microsoft.com/dataset/era5-pds",
                "collection": "era5-pds",
            },
            {
                "name": "SoilGrids v2.0",
                "type": "Global soil property maps (250m)",
                "variables": ["SOC", "clay%", "silt%", "sand%", "pH", "bulk density"],
                "temporal": "Static (trained on ISRIC global soil profile database)",
                "provider": "ISRIC World Soil Information",
                "api_url": "https://rest.isric.org/soilgrids/v2.0/",
                "note": "Used for soil organic carbon and texture classification",
            },
            {
                "name": "Harmonized Landsat Sentinel-2 (HLS)",
                "type": "Gap-filled multispectral (30m)",
                "variables": ["NDVI", "surface reflectance"],
                "temporal": "2013–present",
                "provider": "NASA LPDAAC via Microsoft Planetary Computer",
                "catalog_url": "https://planetarycomputer.microsoft.com/dataset/hls-s30-v002",
                "collection": "hls-s30-v002",
            },
        ],
        "stac_api": "https://planetarycomputer.microsoft.com/api/stac/v1",
        "pc_docs": "https://planetarycomputer.microsoft.com/docs/overview/about",
        "pc_reference": "https://planetarycomputer.microsoft.com/docs/reference/stac/",
    }


@router.post("/specialist-reports/{project_id}")
def run_specialist_agents(project_id: str, from_diagnostic: dict) -> dict:
    """
    Run Soil Doctor, Water Doctor, Vegetation, and Rangeland agents
    against an existing diagnostic result.
    """
    from app.models.indicators import DiagnosticResult
    try:
        diagnostic = DiagnosticResult(**from_diagnostic)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid diagnostic: {e}")

    reports = {}
    for agent, key in [
        (_soil_agent,  "soil_doctor"),
        (_water_agent, "water_doctor"),
        (_veg_agent,   "vegetation_biodiversity"),
        (_range_agent, "rangeland_livestock"),
    ]:
        out = agent.run(project_id=project_id, diagnostic=diagnostic)
        reports[key] = {
            "success": out.success,
            "result": out.result.model_dump() if out.success and hasattr(out.result, "model_dump") else out.result,
            "confidence": out.confidence,
            "assumptions": out.assumptions,
        }

    _specialist_reports[project_id] = reports
    return reports


@router.get("/specialist-reports/{project_id}")
def get_specialist_reports(project_id: str) -> dict:
    reps = _specialist_reports.get(project_id)
    if not reps:
        raise HTTPException(status_code=404, detail="No specialist reports — run POST first")
    return reps
