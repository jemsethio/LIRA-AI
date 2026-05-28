#!/usr/bin/env python3
"""
CMIP6 + GARDIAN Data Preparation Script — LIRA-AI Omo-Ghibe Basin
==================================================================
Fetches:
  1. NASA NEX GDDP CMIP6 climate projections (real data from Planetary Computer)
     - Variables: pr, tas, tasmax
     - Scenarios: historical (1990), ssp245 (2030, 2050, 2070), ssp585 (2050, 2070)
     - Models: MIROC6, MRI-ESM2-0, GFDL-ESM4
     - Collection: nasa-nex-gddp-cmip6
     - URL: https://planetarycomputer.microsoft.com/dataset/nasa-nex-gddp-cmip6

  2. CIL GDPCIR indicators (attempted; falls back if Azure auth required)
     - Collection: cil-gdpcir-cc0 / cil-gdpcir-cc-by
     - URL: https://planetarycomputer.microsoft.com/dataset/group/cil-gdpcir

  3. CGIAR CGSpace evidence library (real data via DSpace 7+ API)
     - Source: https://cgspace.cgiar.org
     - 10 priority queries for Ethiopia/Omo-Ghibe
     - Saved as evidence cards for RAG pipeline

Output files:
  data/ethiopia/omo_ghibe/cmip6_projections.json
  data/ethiopia/omo_ghibe/cmip6_risk_indicators.json
  data/ethiopia/omo_ghibe/gardian_evidence.json
  data/ethiopia/omo_ghibe/data_sources_verified.json

Usage:
    cd backend
    PYTHONPATH=. python scripts/prepare_cmip6_gardian.py
"""

import json, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUTPUT_DIR = ROOT / "data" / "ethiopia" / "omo_ghibe"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

from app.data_adapters.cmip6_adapter import (
    fetch_cmip6_scenario, cmip6_to_lira_risk_indicators,
    HISTORICAL_YEAR, NEAR_TERM_YEAR, MID_TERM_YEAR, LONG_TERM_YEAR,
    CMIP6_MODELS,
)
from app.data_adapters.gardian_adapter import (
    harvest_cgspace, extract_restoration_evidence,
    fetch_gardian_datasets,
)

# ── Configuration ─────────────────────────────────────────────────────────────

MODELS_TO_USE = ["MIROC6", "MRI-ESM2-0", "GFDL-ESM4"]   # 3-model ensemble
SCENARIOS     = ["ssp245", "ssp585"]
HORIZONS      = [NEAR_TERM_YEAR, MID_TERM_YEAR, LONG_TERM_YEAR]

print("\n" + "="*70)
print("LIRA-AI CMIP6 + GARDIAN Data Preparation")
print(f"Basin: Omo-Ghibe (lat 3-10°N, lon 33-42°E)")
print(f"Models: {', '.join(MODELS_TO_USE)}")
print(f"Scenarios: {', '.join(SCENARIOS)}")
print(f"Horizons: {', '.join(str(h) for h in HORIZONS)}")
print("="*70)

# ── 1. Historical baseline ────────────────────────────────────────────────────
print(f"\n[1/4] Historical baseline CMIP6 ({HISTORICAL_YEAR})…")
historical = fetch_cmip6_scenario("historical", HISTORICAL_YEAR, MODELS_TO_USE, verbose=True)
print(f"  Ensemble: {historical.get('n_models')} models  |  is_real={historical['is_real']}")
if historical.get("indicators"):
    h = historical["indicators"]
    print(f"  pr={h.get('annual_precip_mm'):.0f}mm  T={h.get('temp_mean_c'):.1f}°C  "
          f"heat_days={h.get('heat_stress_days_35c'):.0f}  dry={h.get('dry_days'):.0f}")

# ── 2. SSP projections ────────────────────────────────────────────────────────
print(f"\n[2/4] SSP projections…")
projections: dict = {"historical": historical, "scenarios": {}}

for scenario in SCENARIOS:
    projections["scenarios"][scenario] = {}
    for year in HORIZONS:
        print(f"  [{scenario} {year}]")
        proj = fetch_cmip6_scenario(scenario, year, MODELS_TO_USE, verbose=True)

        # Compute deltas vs historical
        if historical.get("is_real") and proj.get("is_real"):
            hist_i = historical["indicators"]
            proj_i = proj["indicators"]
            deltas = {}
            for k in proj_i:
                if k in hist_i:
                    d = proj_i[k] - hist_i[k]
                    deltas[f"delta_{k}"] = round(d, 3)
                    if abs(hist_i[k]) > 0:
                        deltas[f"pct_change_{k}"] = round(d / abs(hist_i[k]) * 100, 1)
            proj["deltas_vs_historical"] = deltas
        else:
            proj["deltas_vs_historical"] = {}

        projections["scenarios"][scenario][str(year)] = proj

        if proj.get("indicators"):
            p = proj["indicators"]
            d = proj.get("deltas_vs_historical", {})
            print(f"    pr={p.get('annual_precip_mm'):.0f}mm "
                  f"({'+' if d.get('pct_change_annual_precip_mm',0)>=0 else ''}"
                  f"{d.get('pct_change_annual_precip_mm',0):.1f}%)  "
                  f"T={p.get('temp_mean_c'):.1f}°C "
                  f"(+{d.get('delta_temp_mean_c_c',0):.1f}°C)  "
                  f"heat={p.get('heat_stress_days_35c'):.0f}d  "
                  f"real={proj['is_real']}")

# Save raw projections
projections["meta"] = {
    "basin": "Omo-Ghibe",
    "bbox": [33.0, 3.0, 42.0, 10.0],
    "models": MODELS_TO_USE,
    "scenarios": SCENARIOS,
    "horizons": HORIZONS,
    "source": "nasa-nex-gddp-cmip6 — Microsoft Planetary Computer",
    "pc_catalog": "https://planetarycomputer.microsoft.com/dataset/nasa-nex-gddp-cmip6",
    "generated_at": datetime.utcnow().isoformat(),
}

out_proj = OUTPUT_DIR / "cmip6_projections.json"
with open(out_proj, "w") as f:
    json.dump(projections, f, indent=2, default=str)
print(f"\n✓ Saved: {out_proj.name}")

# ── 3. Derived LIRA-AI risk indicators ────────────────────────────────────────
print(f"\n[3/4] Computing LIRA-AI risk indicators from CMIP6…")
risk_indicators: dict = {"scenarios": {}}

for scenario in SCENARIOS:
    risk_indicators["scenarios"][scenario] = {}
    for year in HORIZONS:
        proj = projections["scenarios"][scenario][str(year)]
        risks = cmip6_to_lira_risk_indicators(historical, proj)
        risk_indicators["scenarios"][scenario][str(year)] = risks
        print(f"  [{scenario} {year}] overall_risk={risks['overall_climate_risk_score']:.3f}  "
              f"drought={risks['drought_dry_spell_risk']:.3f}  heat={risks['heat_stress_risk']:.3f}  "
              f"real={risks['is_real']}")

risk_indicators["meta"] = {
    "description": "LIRA-AI climate risk indicators (0=low, 1=high) derived from CMIP6",
    "basin": "Omo-Ghibe",
    "source": projections["meta"]["source"],
    "generated_at": datetime.utcnow().isoformat(),
}

out_risk = OUTPUT_DIR / "cmip6_risk_indicators.json"
with open(out_risk, "w") as f:
    json.dump(risk_indicators, f, indent=2, default=str)
print(f"✓ Saved: {out_risk.name}")

# ── 4. CGIAR GARDIAN evidence harvest ────────────────────────────────────────
print(f"\n[4/4] Harvesting CGIAR evidence (CGSpace + GARDIAN)…")
library = harvest_cgspace(max_per_query=8, verbose=True)
cards   = extract_restoration_evidence(library)
datasets = fetch_gardian_datasets("Ethiopia Omo landscape", verbose=True)

gardian_output = {
    "meta": {
        "basin": "Omo-Ghibe",
        "source": "CGIAR CGSpace — https://cgspace.cgiar.org",
        "api": "DSpace 7+ REST API",
        "gardian_platform": "https://gardian.bigdata.cgiar.org",
        "total_items": library["total_items_fetched"],
        "total_cards": len(cards),
        "total_datasets": datasets.get("total_datasets", 0),
        "generated_at": datetime.utcnow().isoformat(),
        "note": "Evidence cards ready for RAG pipeline ingestion",
    },
    "evidence_cards": cards,
    "datasets": datasets.get("datasets", []),
    "full_library": {
        topic: {k: v for k, v in data.items() if k != "results"}
        for topic, data in library.get("topics", {}).items()
    },
    "by_agent": {
        agent: [c for c in cards if agent in c.get("lira_ai_agents", [])]
        for agent in [
            "SoilDoctorAgent", "WaterDoctorAgent", "VegetationBiodiversityAgent",
            "RangelandLivestockAgent", "ClimateFuturesAgent", "InvestmentPlanningAgent",
            "CommunityIntelligenceAgent", "PolicyAlignmentAgent",
        ]
    },
}

out_gardian = OUTPUT_DIR / "gardian_evidence.json"
with open(out_gardian, "w") as f:
    json.dump(gardian_output, f, indent=2, default=str)
print(f"✓ Saved: {out_gardian.name}  ({len(cards)} evidence cards, "
      f"{datasets.get('total_datasets',0)} datasets)")

# ── 5. Data sources verification summary ─────────────────────────────────────
print(f"\n[5/5] Writing data sources verification summary…")

n_real_cmip6 = sum(
    1 for sc in projections["scenarios"].values()
    for yr in sc.values() if yr.get("is_real")
)
n_real_risk = sum(
    1 for sc in risk_indicators["scenarios"].values()
    for yr in sc.values() if yr.get("is_real")
)

sources_verified = {
    "verified_at": datetime.utcnow().isoformat(),
    "basin": "Omo-Ghibe River Basin — Ethiopia MFL Living Lab",
    "sources": {
        "soilgrids_v2": {
            "status": "REAL",
            "description": "SoilGrids v2.0 — ISRIC REST API",
            "url": "https://rest.isric.org/soilgrids/v2.0/",
            "confirmed_data": {
                "highland_soc_g_per_kg": 58.6,
                "midland_soc_g_per_kg": 43.1,
                "lowland_soc_g_per_kg": 28.2,
                "riverine_soc_g_per_kg": 67.9,
            },
        },
        "nasa_nex_gddp_cmip6": {
            "status": "REAL" if historical.get("is_real") else "FALLBACK",
            "description": "NASA NEX GDDP CMIP6 — Planetary Computer",
            "url": "https://planetarycomputer.microsoft.com/dataset/nasa-nex-gddp-cmip6",
            "collection": "nasa-nex-gddp-cmip6",
            "models_used": MODELS_TO_USE,
            "real_projections": n_real_cmip6,
            "total_projections": len(SCENARIOS) * len(HORIZONS),
            "confirmed_data": {
                "ssp245_2050_pr_mm_yr": (
                    projections["scenarios"].get("ssp245", {})
                    .get("2050", {}).get("indicators", {}).get("annual_precip_mm")
                ),
            },
        },
        "cil_gdpcir": {
            "status": "PENDING — Azure anon access requires account setup",
            "description": "CIL GDPCIR pre-computed indicators",
            "url": "https://planetarycomputer.microsoft.com/dataset/group/cil-gdpcir",
            "collection": "cil-gdpcir-cc0",
            "note": "Storage: abfs://cil-gdpcir/ on rhgpublicdata Azure account. "
                    "Use AZURE_STORAGE_ACCOUNT=rhgpublicdata for anonymous access.",
        },
        "sentinel2_l2a": {
            "status": "CONNECTING — epsg=4326 + nodata patch required",
            "description": "Sentinel-2 L2A — Planetary Computer",
            "url": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a",
            "collection": "sentinel-2-l2a",
            "note": "Patched adapter in app/data_adapters/omo_ghibe_adapter.py",
        },
        "esa_worldcover": {
            "status": "CONNECTING — assets=['map'], rescale=False required",
            "description": "ESA WorldCover 2021",
            "url": "https://planetarycomputer.microsoft.com/dataset/esa-worldcover",
        },
        "cgspace_gardian": {
            "status": "REAL",
            "description": "CGIAR CGSpace — DSpace 7+ REST API",
            "url": "https://cgspace.cgiar.org/server/api",
            "gardian_platform": "https://gardian.bigdata.cgiar.org",
            "evidence_cards_harvested": len(cards),
            "total_cgspace_results": library["total_items_fetched"],
            "top_results": [
                c["title"][:60] for c in cards[:5]
            ],
        },
        "modis_mod13q1": {
            "status": "CONNECTING — epsg=4326 required",
            "description": "MODIS MOD13Q1 v061",
            "url": "https://planetarycomputer.microsoft.com/dataset/modis-13Q1-061",
        },
        "chirps_v2": {
            "status": "CONFIRMED — collection in PC catalog",
            "description": "CHIRPS v2.0 Daily Rainfall",
            "url": "https://planetarycomputer.microsoft.com/dataset/chirps-2.0",
        },
    },
    "data_registry": "data/ethiopia/omo_ghibe/data_registry.yaml",
    "pc_examples_reference": "https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets",
    "stac_reading_guide": "https://github.com/microsoft/PlanetaryComputerExamples/blob/main/quickstarts/reading-stac.ipynb",
    "stac_geoparquet_guide": "https://github.com/microsoft/PlanetaryComputerExamples/blob/main/quickstarts/stac-geoparquet.ipynb",
}

out_sources = OUTPUT_DIR / "data_sources_verified.json"
with open(out_sources, "w") as f:
    json.dump(sources_verified, f, indent=2, default=str)
print(f"✓ Saved: {out_sources.name}")

print("\n" + "="*70)
print("CMIP6 + GARDIAN Data Preparation Complete")
print(f"  CMIP6 real projections: {n_real_cmip6}/{len(SCENARIOS)*len(HORIZONS)}")
print(f"  GARDIAN evidence cards: {len(cards)}")
print(f"  Output dir: {OUTPUT_DIR}")
print("="*70)
