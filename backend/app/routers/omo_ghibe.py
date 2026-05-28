"""
Omo-Ghibe Basin — dedicated API router.
Serves the 4 pre-computed landscape zones from disk and
allows live re-fetching from Planetary Computer + SoilGrids.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
import json

from app.models.indicators import LandscapeIndicators
from app.engines.indicator_engine import run_indicator_engine
from app.engines.syndrome_classifier import classify_syndromes
from app.engines.landscape_health_index import compute_lhii

router = APIRouter(prefix="/omo-ghibe", tags=["Omo-Ghibe Living Lab"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ethiopia" / "omo_ghibe"

ZONE_IDS = ["highland", "midland", "lowland_pastoral", "riverine"]


def _load_zone(zone_id: str) -> dict:
    path = DATA_DIR / f"indicators_{zone_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Zone data not found: {zone_id}. Run prepare_omo_ghibe_data.py first.")
    with open(path) as f:
        return json.load(f)


@router.get("/", summary="Basin overview")
def basin_overview() -> dict:
    index_path = DATA_DIR / "index.json"
    if not index_path.exists():
        return {"message": "Run scripts/prepare_omo_ghibe_data.py to generate basin data"}
    with open(index_path) as f:
        return json.load(f)


@router.get("/zones", summary="List all landscape zones")
def list_zones() -> list[dict]:
    zones = []
    for zone_id in ZONE_IDS:
        try:
            d = _load_zone(zone_id)
            zones.append({
                "zone_id": zone_id,
                "zone_name": d["meta"]["zone_name"],
                "area_ha": d["meta"]["area_ha"],
                "dominant_syndrome": d["meta"]["dominant_syndrome"],
                "real_data_layers": d["meta"]["real_data_layers"],
                "data_completeness_pct": d["meta"]["data_completeness_pct"],
                "bbox": d["meta"]["bbox"],
            })
        except HTTPException:
            zones.append({"zone_id": zone_id, "status": "data_not_ready"})
    return zones


@router.get("/zones/{zone_id}", summary="Get full zone dataset")
def get_zone(zone_id: str) -> dict:
    if zone_id not in ZONE_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown zone. Choose from: {ZONE_IDS}")
    return _load_zone(zone_id)


@router.get("/zones/{zone_id}/indicators", summary="Get zone indicators only")
def get_zone_indicators(zone_id: str) -> dict:
    d = _load_zone(zone_id)
    return d["indicators"]


@router.post("/zones/{zone_id}/diagnose", summary="Run full diagnosis on a zone")
def diagnose_zone(zone_id: str) -> dict:
    """Load pre-computed indicators and run the full LIRA-AI diagnosis pipeline."""
    d = _load_zone(zone_id)
    raw = d["indicators"].copy()
    raw["project_id"] = raw.get("project_id", f"OMO-GHIBE-{zone_id.upper()}")

    try:
        inds = LandscapeIndicators(**raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Indicator schema error: {e}")

    diagnostic = run_indicator_engine(inds)
    syndromes  = classify_syndromes(diagnostic)
    lhii       = compute_lhii(diagnostic)

    return {
        "zone_id":   zone_id,
        "zone_name": d["meta"]["zone_name"],
        "dominant_syndrome_configured": d["meta"]["dominant_syndrome"],
        "diagnostic": diagnostic.model_dump(),
        "syndromes":  syndromes.model_dump(),
        "lhii":       lhii.model_dump(),
        "data_quality": d["data_quality"],
        "community_intelligence": d["community_intelligence"],
    }


@router.get("/zones/{zone_id}/community", summary="Get community intelligence")
def get_community_intelligence(zone_id: str) -> dict:
    d = _load_zone(zone_id)
    return {
        "zone_id": zone_id,
        "zone_name": d["meta"]["zone_name"],
        **d["community_intelligence"],
    }


@router.get("/boundary", summary="Get basin GeoJSON boundary")
def get_boundary() -> dict:
    boundary_path = DATA_DIR / "boundary.geojson"
    if not boundary_path.exists():
        raise HTTPException(status_code=404, detail="Boundary file not found")
    with open(boundary_path) as f:
        return json.load(f)


@router.get("/data-registry", summary="Get Ethiopia data source registry")
def get_data_registry() -> dict:
    import yaml
    registry_path = DATA_DIR / "data_registry.yaml"
    if not registry_path.exists():
        raise HTTPException(status_code=404, detail="Data registry not found")
    with open(registry_path) as f:
        return yaml.safe_load(f)


@router.post("/zones/{zone_id}/fetch-live", summary="Re-fetch real data from PC + SoilGrids")
def fetch_live(zone_id: str, background_tasks: BackgroundTasks) -> dict:
    """
    Trigger live re-fetch from Planetary Computer + SoilGrids for a zone.
    Runs in background; results saved to disk and served by GET /zones/{zone_id}.
    """
    if zone_id not in ZONE_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown zone: {zone_id}")

    def _run():
        import subprocess, sys
        subprocess.run(
            [sys.executable, "scripts/prepare_omo_ghibe_data.py"],
            cwd=Path(__file__).resolve().parent.parent.parent,
        )

    background_tasks.add_task(_run)
    return {"status": "fetch_queued", "zone_id": zone_id,
            "message": "Real data fetch from Planetary Computer + SoilGrids started in background. Check GET /omo-ghibe/zones/{zone_id} for results."}


@router.get("/compare", summary="Compare all zones side by side")
def compare_zones() -> dict:
    """Side-by-side comparison of key indicators across all 4 landscape zones."""
    comparison = {}
    key_inds = [
        "ndvi_mean", "land_productivity_index", "soil_loss_rate_t_ha_yr",
        "soil_organic_carbon_g_per_kg", "rainfall_mm_annual",
        "overgrazing_proxy", "forest_cover_pct", "bare_soil_pct",
    ]
    for zone_id in ZONE_IDS:
        try:
            d = _load_zone(zone_id)
            inds = d["indicators"]
            comparison[zone_id] = {
                "zone_name": d["meta"]["zone_name"],
                "dominant_syndrome": d["meta"]["dominant_syndrome"],
                "real_data_layers": d["meta"]["real_data_layers"],
                **{k: inds.get(k) for k in key_inds},
            }
        except HTTPException:
            comparison[zone_id] = {"status": "data_not_ready"}
    return {"basin": "Omo-Ghibe", "zones": comparison}
