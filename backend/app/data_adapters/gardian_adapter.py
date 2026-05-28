"""
CGIAR GARDIAN / CGSpace Data Harvester — LIRA-AI
=================================================
Harvests scientific evidence, datasets, and publications from:

1. CGIAR CGSpace (DSpace 7+ API) — institutional repository
   https://cgspace.cgiar.org/server/api
   ~100,000 CGIAR publications and datasets

2. CGIAR GARDIAN — big data platform
   https://gardian.bigdata.cgiar.org
   Cross-repository dataset discovery

3. CGIAR Open Data Portal
   https://data.cgiar-system.org

Priority search queries for Omo-Ghibe / LIRA-AI:
  - Ethiopia landscape degradation
  - Omo River basin restoration
  - Ethiopia soil erosion land degradation
  - Ethiopia rangeland pastoral South Omo
  - Ethiopia NDVI vegetation land cover change
  - Ethiopia climate change drought food security
  - Landscape Doctor CGIAR Ethiopia
  - Ethiopia agroforestry FMNR restoration
  - CGIAR MFL multifunctional landscapes Ethiopia

Each result is classified by LIRA-AI agent/indicator relevance.
"""

from __future__ import annotations
import json
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional

CGSPACE_API = "https://cgspace.cgiar.org/server/api"
GARDIAN_WEB = "https://gardian.bigdata.cgiar.org"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "LIRA-AI/0.1 (CGIAR MFL Landscape Futures Lab)",
}

# Priority search queries mapped to LIRA-AI agents
SEARCH_QUERIES: dict[str, dict] = {
    "ethiopia_landscape_degradation": {
        "query": "Ethiopia landscape degradation soil erosion",
        "lira_ai_agents": ["SoilDoctorAgent", "WaterDoctorAgent", "CausalDiagnosisAgent"],
        "lira_ai_indicators": ["soil_loss_rate", "land_cover_change", "composite_health_score"],
    },
    "omo_basin_restoration": {
        "query": "Omo River basin Ethiopia restoration",
        "lira_ai_agents": ["VegetationBiodiversityAgent", "InvestmentPlanningAgent"],
        "lira_ai_indicators": ["forest_cover_pct", "investment_readiness"],
    },
    "ethiopia_rangeland_pastoral": {
        "query": "Ethiopia rangeland pastoral South Omo overgrazing",
        "lira_ai_agents": ["RangelandLivestockAgent", "CommunityIntelligenceAgent"],
        "lira_ai_indicators": ["overgrazing_proxy", "carrying_capacity"],
    },
    "ethiopia_climate_drought": {
        "query": "Ethiopia climate change drought food security FEWS",
        "lira_ai_agents": ["ClimateFuturesAgent", "AdaptiveMonitoringAgent"],
        "lira_ai_indicators": ["drought_frequency", "rainfall_anomaly"],
    },
    "ethiopia_agroforestry_fmnr": {
        "query": "Ethiopia agroforestry FMNR restoration landscape",
        "lira_ai_agents": ["VegetationBiodiversityAgent", "AgronomyAgent"],
        "lira_ai_indicators": ["ndvi_trend", "land_productivity_index"],
    },
    "mfl_living_lab": {
        "query": "multifunctional landscapes living lab CGIAR MFL",
        "lira_ai_agents": ["PolicyAlignmentAgent", "InvestmentPlanningAgent"],
        "lira_ai_indicators": ["policy_alignment", "investment_readiness"],
    },
    "landscape_doctor": {
        "query": "Landscape Doctor toolbox restoration diagnosis Ethiopia",
        "lira_ai_agents": ["CausalDiagnosisAgent", "SoilDoctorAgent"],
        "lira_ai_indicators": ["syndrome_classification", "restoration_suitability"],
    },
    "ethiopia_soil_carbon": {
        "query": "Ethiopia soil organic carbon SoilGrids land degradation",
        "lira_ai_agents": ["SoilDoctorAgent"],
        "lira_ai_indicators": ["soil_organic_carbon_g_per_kg"],
    },
    "gibe_reservoir": {
        "query": "Gibe III dam sedimentation Omo Ethiopia",
        "lira_ai_agents": ["WaterDoctorAgent", "RangelandLivestockAgent"],
        "lira_ai_indicators": ["reservoir_sedimentation_proxy"],
    },
    "ethiopia_ndvi_vegetation": {
        "query": "Ethiopia NDVI vegetation trends remote sensing Sentinel",
        "lira_ai_agents": ["VegetationBiodiversityAgent", "LandscapeEvidenceAgent"],
        "lira_ai_indicators": ["ndvi_mean", "ndvi_trend_5yr"],
    },
}


def _cgspace_search(
    query: str,
    page: int = 0,
    size: int = 10,
) -> list[dict]:
    """
    Search CGSpace (CGIAR institutional repository) via DSpace 7+ REST API.
    Returns list of normalized result dicts.

    API docs: https://cgspace.cgiar.org/server/api
    """
    q_encoded = urllib.parse.quote(query)
    url = (
        f"{CGSPACE_API}/discover/search/objects"
        f"?query={q_encoded}&page={page}&size={size}"
        f"&embed=thumbnail&embed=item%2Fmappedcollections"
    )
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        embedded = data.get("_embedded", {})
        search_r = embedded.get("searchResult", {})
        objects  = search_r.get("_embedded", {}).get("objects", [])
        total    = search_r.get("page", {}).get("totalElements", 0)

        results = []
        for obj in objects:
            inner = obj.get("_embedded", {}).get("indexableObject", {})
            meta  = inner.get("metadata", {})

            def _meta(field: str) -> str:
                vals = meta.get(field, [{}])
                return vals[0].get("value", "") if vals else ""

            results.append({
                "id":         inner.get("id") or inner.get("uuid", ""),
                "type":       inner.get("type", "item"),
                "title":      _meta("dc.title"),
                "author":     _meta("dc.contributor.author"),
                "year":       _meta("dc.date.issued")[:4] if _meta("dc.date.issued") else "",
                "abstract":   _meta("dc.description.abstract")[:400],
                "subject":    [s["value"] for s in meta.get("dc.subject", [])[:5]],
                "publisher":  _meta("dc.publisher"),
                "identifier": _meta("dc.identifier.uri"),
                "doi":        _meta("dc.identifier.doi"),
                "handle":     inner.get("handle", ""),
                "cgspace_url": f"https://cgspace.cgiar.org/handle/{inner.get('handle','')}" if inner.get("handle") else "",
            })

        return results, total
    except Exception as exc:
        return [], 0


def harvest_cgspace(
    queries: Optional[list[str]] = None,
    max_per_query: int = 8,
    verbose: bool = True,
) -> dict:
    """
    Harvest CGIAR evidence from CGSpace across all LIRA-AI priority queries.
    Returns structured evidence library keyed by topic.
    """
    queries = queries or list(SEARCH_QUERIES.keys())
    library: dict = {}
    total_fetched = 0

    for query_key in queries:
        cfg   = SEARCH_QUERIES[query_key]
        query = cfg["query"]

        if verbose:
            print(f"  → CGSpace: '{query[:50]}'…", end=" ", flush=True)

        results, total = _cgspace_search(query, size=max_per_query)

        if verbose:
            print(f"✓ {total} total, showing {len(results)}")

        library[query_key] = {
            "query": query,
            "total_results": total,
            "lira_ai_agents": cfg["lira_ai_agents"],
            "lira_ai_indicators": cfg["lira_ai_indicators"],
            "results": results,
            "source": "CGIAR CGSpace — DSpace 7+ REST API",
            "api_url": f"{CGSPACE_API}/discover/search/objects",
            "is_real": len(results) > 0,
        }
        total_fetched += len(results)

    return {
        "source": "CGIAR CGSpace — https://cgspace.cgiar.org",
        "api": CGSPACE_API,
        "harvested_at": datetime.utcnow().isoformat(),
        "total_topics": len(library),
        "total_items_fetched": total_fetched,
        "topics": library,
    }


def extract_restoration_evidence(library: dict) -> list[dict]:
    """
    Extract restoration-relevant evidence cards from harvested library.
    Used to populate RAG knowledge base.
    """
    cards = []
    for topic_key, topic in library.get("topics", {}).items():
        for item in topic.get("results", []):
            if not item.get("title"):
                continue
            card = {
                "source_id":    f"cgspace_{item.get('id','')[:8]}",
                "title":        item["title"],
                "year":         item.get("year", ""),
                "abstract":     item.get("abstract", ""),
                "cgspace_url":  item.get("cgspace_url", ""),
                "doi":          item.get("doi", ""),
                "subjects":     item.get("subject", []),
                "lira_ai_topic":topic_key,
                "lira_ai_agents": topic.get("lira_ai_agents", []),
                "confidence":   "medium",
                "is_real":      True,
            }
            cards.append(card)
    # Deduplicate by title
    seen: set[str] = set()
    unique = []
    for c in cards:
        key = c["title"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def fetch_gardian_datasets(
    keyword: str = "Ethiopia",
    verbose: bool = True,
) -> dict:
    """
    Attempt to harvest datasets from GARDIAN big data platform.
    GARDIAN is a SPA — falls back to CGSpace search for Ethiopia datasets.
    """
    if verbose:
        print(f"  → GARDIAN/CGSpace datasets: '{keyword}'…", end=" ", flush=True)

    # GARDIAN SPA doesn't expose a simple REST endpoint — use CGSpace data collection search
    q = urllib.parse.quote(f"{keyword} dataset")
    url = (
        f"{CGSPACE_API}/discover/search/objects"
        f"?query={q}&page=0&size=20"
        f"&f.type=dataset,equals"
    )
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        embedded = data.get("_embedded", {})
        objects  = embedded.get("searchResult", {}).get("_embedded", {}).get("objects", [])
        total    = embedded.get("searchResult", {}).get("page", {}).get("totalElements", 0)

        datasets = []
        for obj in objects:
            inner = obj.get("_embedded", {}).get("indexableObject", {})
            meta  = inner.get("metadata", {})
            def _m(field): return (meta.get(field,[{}])[0].get("value","") if meta.get(field) else "")
            datasets.append({
                "id":     inner.get("uuid",""),
                "title":  _m("dc.title"),
                "year":   _m("dc.date.issued")[:4],
                "type":   "dataset",
                "handle": inner.get("handle",""),
                "url":    f"https://cgspace.cgiar.org/handle/{inner.get('handle','')}",
                "format": _m("dc.format"),
            })

        if verbose:
            print(f"✓ {total} datasets, {len(datasets)} returned")

        return {
            "keyword": keyword,
            "total_datasets": total,
            "datasets": datasets,
            "source": "CGIAR CGSpace — dataset type filter",
            "gardian_platform": GARDIAN_WEB,
            "note": "GARDIAN SPA resolved via CGSpace DSpace 7+ API",
            "is_real": True,
        }
    except Exception as exc:
        if verbose:
            print(f"✗ ({exc})")
        return {"keyword": keyword, "datasets": [], "is_real": False, "error": str(exc)}


def get_ethiopia_evidence_summary() -> dict:
    """
    Quick summary of available CGIAR evidence for Ethiopia LIRA-AI use case.
    Uses targeted queries for highest-relevance topics.
    """
    key_queries = [
        "ethiopia_landscape_degradation",
        "omo_basin_restoration",
        "ethiopia_rangeland_pastoral",
        "ethiopia_climate_drought",
        "ethiopia_agroforestry_fmnr",
    ]
    library = harvest_cgspace(queries=key_queries, max_per_query=6, verbose=True)
    cards   = extract_restoration_evidence(library)

    return {
        "summary": {
            "total_cgspace_results": library["total_items_fetched"],
            "total_evidence_cards": len(cards),
            "topics_covered": key_queries,
            "source": library["source"],
        },
        "evidence_cards": cards[:40],   # top 40 for RAG
        "full_library": library,
    }
