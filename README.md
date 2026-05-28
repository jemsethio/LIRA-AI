# LIRA-AI: Landscape Intelligence for Regeneration and Adaptation

> **Predictive intelligence for investable landscape regeneration**
>
> *Multi-agent AI platform that transforms landscape restoration from reactive monitoring into
> climate-resilient, community-grounded, policy-aligned, and investment-ready decision-making.*

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15.3.9-black?logo=nextdotjs)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![CGIAR MFL](https://img.shields.io/badge/CGIAR-MFL%20%26%20CASP-orange)](https://www.cgiar.org)
[![GitHub](https://img.shields.io/badge/GitHub-jemsethio/LIRA--AI-blue?logo=github)](https://github.com/jemsethio/LIRA-AI)

---

## The Central Shift

```
From:  "Where is degradation happening?"

To:    "Why is the landscape degrading, what will happen next under climate change,
        what restoration pathway is most robust, who benefits or loses,
        and which actions should be financed first?"
```

---

## What LIRA-AI Does

| Challenge | LIRA-AI Response |
|---|---|
| Degradation diagnosis | 8 syndromes, 9 indicators, LHII composite, causal graph |
| Climate futures | NASA NEX GDDP CMIP6 (SSP2-4.5 / SSP5-8.5), 3-model ensemble |
| Restoration knowledge | CGIAR CGSpace RAG — 6,218+ publications, 32+ indexed per project |
| Pathway generation | 7 alternative pathway packages per landscape zone |
| Tradeoff evaluation | 13-dimension maladaptation radar |
| Investment planning | GCF/LDCF/AF screening, cost estimates, MRV framework |
| Adaptive monitoring | Before-after NDVI tracking, MELIA framework, re-prescription alerts |
| Community advisory | Audience-specific messages (farmer, pastoralist, planner, investor) |
| AI narratives | Ollama (local) → Groq → HuggingFace — 120-word data-grounded summaries |
| MCP tools | 10 scientific tools callable by AI agents via Model Context Protocol |

---

## System Architecture

```
lira-ai/
├── backend/                           Python 3.11 / FastAPI
│   ├── app/
│   │   ├── main.py                    FastAPI app — 85 API routes
│   │   ├── config.py                  Settings + YAML config loader
│   │   │
│   │   ├── agents/                    14 specialist AI agents (all complete)
│   │   │   ├── base_agent.py
│   │   │   ├── landscape_evidence_agent.py   ← Planetary Computer orchestrator
│   │   │   ├── climate_futures_agent.py      ← NASA NEX GDDP CMIP6
│   │   │   ├── causal_diagnosis_agent.py     ← Syndrome + causal graph + hotspots
│   │   │   ├── soil_agent.py                 ← RUSLE + SoilGrids erosion
│   │   │   ├── water_agent.py                ← SCS CN runoff model
│   │   │   ├── vegetation_agent.py           ← Sentinel-2 NDVI trends
│   │   │   ├── agronomy_agent.py             ← Crop suitability + ISFM
│   │   │   ├── rangeland_agent.py            ← TLU carrying capacity
│   │   │   ├── community_agent.py            ← Equity, tenure, conflict scoring
│   │   │   ├── policy_agent.py               ← 10 frameworks: NDC/NAP/LDN/GBF/CRGE
│   │   │   ├── tradeoff_agent.py             ← 13-dimension risk radar
│   │   │   ├── investment_agent.py           ← GCF/LDCF/AF screening + MRV
│   │   │   ├── adaptive_monitoring_agent.py  ← Before-after NDVI + MELIA
│   │   │   └── advisory_agent.py             ← Multi-audience advisories
│   │   │
│   │   ├── engines/                   Deterministic scientific engines
│   │   │   ├── indicator_engine.py    9 indicator classifiers (YAML thresholds)
│   │   │   ├── syndrome_classifier.py 8 degradation syndromes
│   │   │   ├── causal_graph.py        NetworkX causal chains → JSON
│   │   │   ├── pathway_generator.py   7 pathway packages + 8 option cards
│   │   │   ├── priority_index.py      Landscape Resilience Investment Priority Index
│   │   │   ├── landscape_health_index.py  LHII — 6 weighted components
│   │   │   └── melia.py               MELIA framework tracker
│   │   │
│   │   ├── data_adapters/             Real data source connectors
│   │   │   ├── planetary_computer.py  Sentinel-2, DEM, WorldCover, MODIS, CHIRPS, ERA5
│   │   │   ├── omo_ghibe_adapter.py   Omo-Ghibe basin orchestrator
│   │   │   ├── cmip6_adapter.py       NASA NEX GDDP CMIP6 reader
│   │   │   ├── glsem_adapter.py       GloSEM + Enhanced RUSLE (Hurni 1985)
│   │   │   └── gardian_adapter.py     CGIAR CGSpace DSpace 7+ harvester
│   │   │
│   │   ├── rag/                       RAG knowledge pipeline
│   │   │   ├── ingestion.py           PDF/DOCX/TXT → chunk → embed → ChromaDB
│   │   │   └── card_extractor.py      RestorationOptionCard extraction
│   │   │
│   │   ├── mcp/                       Model Context Protocol server
│   │   │   └── server.py              10 scientific tools via FastMCP
│   │   │
│   │   ├── services/
│   │   │   └── llm_service.py         Ollama → Groq → HuggingFace → template
│   │   │
│   │   └── routers/                   FastAPI route handlers (14 routers)
│   │       ├── projects.py / diagnosis.py / climate.py / pathways.py
│   │       ├── investment.py / community.py / monitoring.py / advisory.py
│   │       ├── evidence.py / spatial.py / agronomy.py
│   │       ├── agents.py              Unified agent API
│   │       ├── rag.py                 RAG knowledge base API
│   │       ├── mcp_router.py          MCP tool REST façade
│   │       ├── ai.py                  AI narrative generation
│   │       ├── omo_ghibe.py           Omo-Ghibe Living Lab
│   │       └── climate_data.py        CMIP6 + GARDIAN
│   │
│   ├── config/
│   │   ├── thresholds.yaml            All indicator thresholds (configurable)
│   │   └── syndromes.yaml             8 syndrome definitions (configurable)
│   │
│   ├── data/ethiopia/omo_ghibe/       100% real confirmed data
│   │   ├── boundary.geojson           Basin + 4 zone boundaries
│   │   ├── indicators_highland.json   7/7 real sources (SOC=58.6 g/kg confirmed)
│   │   ├── indicators_midland.json    7/7 real sources (SOC=43.1 g/kg confirmed)
│   │   ├── indicators_lowland_pastoral.json
│   │   ├── indicators_riverine.json
│   │   ├── cmip6_projections.json     NASA NEX GDDP CMIP6 projections
│   │   ├── data_registry.yaml         Ethiopia data source catalogue
│   │   └── gardian_evidence.json      Pre-harvested CGIAR evidence library
│   │
│   ├── scripts/
│   │   ├── prepare_omo_ghibe_data.py  Fetch all 7 real data sources
│   │   ├── prepare_cmip6_gardian.py   CMIP6 projections + GARDIAN harvest
│   │   └── download_glsem.py          GloSEM download (Borrelli et al. 2021)
│   │
│   └── tests/
│       ├── test_indicator_engine.py   Unit tests
│       └── test_end_to_end.py         67 end-to-end tests (all passing)
│
└── frontend/                          Next.js 15 / React / Tailwind
    └── src/app/                       21 pages
        ├── page.tsx                   Decision cockpit dashboard
        ├── setup/                     Project setup
        ├── evidence/                  Evidence Cloud + 7 data sources
        ├── diagnosis/                 Landscape diagnosis + severity radar
        ├── climate/                   Climate Futures dashboard
        ├── climate-data/              CMIP6 projections + GARDIAN evidence
        ├── syndromes/                 Syndromes + causal graph + driver interactions
        ├── pathways/                  7 regeneration pathway packages
        ├── tradeoffs/                 13-dimension maladaptation radar
        ├── investment/                Investment Passports + GCF screening
        ├── community/                 Community Intelligence + Policy Alignment
        ├── advisory/                  Multi-audience advisories
        ├── monitoring/                MELIA + before-after NDVI tracking
        ├── knowledge/                 RAG Knowledge Base (upload, search, cards)
        ├── mcp-tools/                 MCP Tool Explorer (10 tools, live runner)
        ├── map/                       Interactive spatial map (Leaflet)
        ├── omo-ghibe/                 Omo-Ghibe Living Lab pilot
        └── export/                    JSON + Markdown export
```

---

## 14 Specialist AI Agents — All Implemented

| # | Agent | Function | Data Sources |
|---|---|---|---|
| 1 | **LandscapeEvidenceAgent** | Orchestrates all Planetary Computer data fetch | Sentinel-2, DEM, WorldCover, MODIS, CHIRPS, ERA5 |
| 2 | **ClimateFuturesAgent** | CMIP6 risk projections | NASA NEX GDDP — MIROC6, MRI-ESM2-0, GFDL-ESM4 |
| 3 | **CausalDiagnosisAgent** | Syndrome + causal graph + driver interactions + feedback loops | LHII engine, causal chain templates |
| 4 | **SoilDoctorAgent** | RUSLE erosion, SOC, moisture, hotspot/green-spot | SoilGrids, DEM, Landsat |
| 5 | **WaterDoctorAgent** | SCS CN runoff, gully risk, sedimentation | DEM, rainfall, land cover |
| 6 | **VegetationBiodiversityAgent** | NDVI trends, deforestation, recovery potential | Sentinel-2, WorldCover |
| 7 | **AgronomyAgent** | Crop suitability (8 crops), ISFM, yield gap | FAO EcoCrop, ERA5, SoilGrids |
| 8 | **RangelandLivestockAgent** | TLU carrying capacity, feed balance, grazing | NDVI proxy, community data |
| 9 | **CommunityIntelligenceAgent** | Equity scores, tenure/conflict risk, gender advisory | Community form + conflict assessment |
| 10 | **PolicyAlignmentAgent** | 10 frameworks: NDC, NAP, LDN, GBF, CRGE, watershed, carbon/PES | Ethiopian policy database |
| 11 | **TradeoffMaladaptationAgent** | 13-dimension risk radar | Pathway analysis |
| 12 | **InvestmentPlanningAgent** | GCF/LDCF/AF window screening, cost estimates, MRV | Investment priority index engine |
| 13 | **AdaptiveMonitoringAgent** | Before-after NDVI, MELIA framework, re-prescription alerts | Sentinel-2 trend analysis |
| 14 | **AdvisoryCommunicationAgent** | Farmer / pastoralist / planner / investor briefs | Syndrome + pathway data |

---

## Real Data Sources — All Confirmed

| Source | Status | Confirmed Values (Omo-Ghibe) |
|---|---|---|
| **SoilGrids v2.0** (ISRIC) | ✅ REAL | Highland SOC=58.6 g/kg, pH=5.4 |
| **Sentinel-2 L2A** (Planetary Computer) | ✅ REAL | NDVI=0.446 (60% valid pixels) |
| **Copernicus DEM GLO-30** (PC) | ✅ REAL | Elev=2,194m, Slope=9.8° |
| **ESA WorldCover 2021** (PC) | ✅ REAL | Forest=61.7% (Highland) |
| **MODIS MOD13Q1** (PC) | ✅ REAL | LPI=0.869 |
| **CHIRPS v2.0** (CHC UCSB) | ✅ REAL | 988–1,859 mm/yr |
| **ERA5-Land** (Open-Meteo) | ✅ REAL | T=15.0–29.4°C |
| **NASA NEX GDDP CMIP6** (PC) | ✅ REAL | SSP245 2050: 1,074 mm/yr |
| **CGIAR CGSpace** (DSpace 7+) | ✅ REAL | 6,218+ Ethiopia results |
| **GloSEM v1.2** (Borrelli 2021) | ⚡ Download | `python scripts/download_glsem.py` |

**Key technical note:** All Planetary Computer raster fetches use `epsg=32637` (UTM Zone 37N).
Using `epsg=4326` + `resolution=100` = 100 degrees/pixel (the whole Earth in one pixel!).

---

## Pilot Landscape: Omo-Ghibe Basin, Ethiopia

**Location:** Southwestern Ethiopia — lat 3–10°N, lon 33–42°E (~7.9 million ha)
**Context:** CGIAR MFL Living Lab, Alliance Bioversity-CIAT, Addis Ababa

**Four landscape zones — 7/7 real data sources each (100% confirmed):**

| Zone | NDVI | SOC (g/kg) | Rain (mm/yr) | Temp (°C) | Slope | Primary Syndrome |
|---|---|---|---|---|---|---|
| Kafa-Sheka Highland | 0.446 | **58.6** | 1,859 | 15.0 | 9.8° | Deforestation / vegetation loss |
| Dawro-Wolayita Midland | 0.283 | **43.1** | 1,275 | 17.7 | 4.7° | Erosion–productivity decline |
| South Omo Lowland | 0.111 | **28.2** | 760 | 22.1 | 9.1° | Rangeland overgrazing |
| Omo River Corridor | 0.101 | **67.9** | 686 | 29.4 | 12.3° | Reservoir sedimentation |

---

## RAG Knowledge Pipeline

```
Document ingestion:
  POST /rag/ingest          ← Upload PDF/DOCX/TXT/MD
  POST /rag/ingest-cgspace  ← Auto-index CGSpace (8 Ethiopia queries, 32+ items)
  
Retrieval:
  POST /rag/retrieve        ← Semantic search (0.70–0.78 similarity scores)
  GET  /rag/cards/{id}      ← Extract RestorationOptionCards
  GET  /rag/status          ← ChromaDB collection stats

Vector store: ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
CGIAR coverage: "Restoring degraded landscapes" (Mekuria), "National land restoration 
initiatives Ethiopia", "Gudoberet landscape restoration" — all indexed and retrievable
```

---

## MCP Server — 10 Scientific Tools

The LIRA-AI MCP server exposes scientific tools callable by any AI agent via the
[Model Context Protocol](https://modelcontextprotocol.io).

```bash
# Run standalone MCP server (stdio transport for AI agents)
python -m app.mcp.server

# Or call via REST (for testing)
GET  /mcp/tools       ← List all tools
POST /mcp/call        ← {"tool": "compute_rusle", "inputs": {...}}
```

| MCP Tool | Function | Example Output |
|---|---|---|
| `diagnose_landscape` | Full indicator + syndrome + LHII | severity, health score, LHII class |
| `compute_rusle` | Enhanced RUSLE soil erosion | 62.4 t/ha/yr [very_severe] |
| `fetch_soilgrids` | Real SoilGrids v2.0 | SOC=58.6 g/kg, pH=5.4 (REAL) |
| `fetch_sentinel2_ndvi` | Sentinel-2 NDVI from PC | NDVI=0.446, 60% valid pixels |
| `get_climate_risk` | CMIP6 SSP245/SSP585 risk scores | drought=0.65, erosion=0.72 |
| `search_cgspace` | CGIAR CGSpace evidence | 16 results for Omo-Ghibe |
| `retrieve_rag` | Semantic search indexed docs | similarity 0.777 |
| `generate_pathways` | 7 restoration pathway packages | recommended: investment_ready |
| `get_zone_data` | Real Omo-Ghibe zone indicators | 7/7 real data sources |
| `narrate_summary` | AI narrative via Ollama | 120-word academic summary |

---

## AI Narrative Generation

```
Provider cascade (all open-source / free):
  1. Ollama (local)   → tinyllama:latest — confirmed 2.2s, is_llm=True
  2. Groq (free tier) → Set GROQ_API_KEY in .env
  3. HuggingFace      → Set HF_TOKEN in .env
  4. Template         → Deterministic fallback, always works

Architecture — hybrid approach (no hallucination):
  Para 1: Deterministic from indicator values (Python, zero LLM)
          → injects exact numbers, CGSpace citations
  Para 2: LLM generates "Priority action: [one specific sentence]"
          → extracted by regex, falls back to curated defaults

Used on: Diagnosis, Syndromes, Climate, Pathways, Tradeoffs,
         Investment, Monitoring, Omo-Ghibe, Map, Community, Advisory
```

---

## Quick Start

### Prerequisites
- Python 3.11+ · Node.js 20+ · `uv` (`pip install uv`)

### Backend

```bash
cd lira-ai/backend
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[dev]"

# Start API
PYTHONPATH=. uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (interactive API docs)
```

### Frontend

```bash
cd lira-ai/frontend
npm install
npm run dev
# → http://localhost:3000
```

### Fetch Real Data

```bash
cd backend
# Fetch all 7 real data sources for Omo-Ghibe (takes ~5 min)
PYTHONPATH=. python scripts/prepare_omo_ghibe_data.py

# Fetch CMIP6 climate projections + harvest CGIAR evidence
PYTHONPATH=. python scripts/prepare_cmip6_gardian.py

# (Optional) Download GloSEM real soil erosion raster
PYTHONPATH=. python scripts/download_glsem.py
```

### Start Ollama (for AI narratives)

```bash
brew install ollama
ollama serve &
ollama pull tinyllama   # 637MB — fits in ~700MB free space
```

---

## API Reference (Key Endpoints)

### Core Pipeline
```http
POST /diagnosis/indicators          Run indicator engine (9 classifiers)
POST /diagnosis/syndromes/{id}      Classify degradation syndromes
GET  /diagnosis/causal-graph/{id}   Build causal graph (NetworkX → JSON)
POST /pathways/{id}/generate        Generate 7 pathway packages
POST /pathways/{id}/tradeoffs       13-dimension tradeoff radar
POST /investment/{id}/passport      Generate Investment Passport
POST /monitoring/lhii/{id}         Compute Landscape Health Index (LHII)
POST /monitoring/melia/{id}        Generate MELIA report
POST /agronomy/{id}                Agronomy analysis + crop suitability
POST /advisory/{id}                Multi-audience advisories
```

### All 14 Agents (unified)
```http
POST /agents/community-intelligence  Equity, tenure, conflict, gender advisory
POST /agents/policy-alignment         10 frameworks: NDC/NAP/LDN/GBF/CRGE
POST /agents/investment-planning      GCF/LDCF/AF screening, MRV, co-finance
POST /agents/causal-diagnosis         Driver interactions, feedback loops, hotspots
POST /agents/full-diagnosis           All four agents in one call
GET  /agents/registry                 List all 14 agents with status
```

### RAG Knowledge Base
```http
POST /rag/ingest                Upload document → ChromaDB
POST /rag/ingest-cgspace        Auto-index 8 Ethiopia CGSpace queries
POST /rag/retrieve              Semantic search with similarity scores
GET  /rag/cards/{project_id}    Extract RestorationOptionCards
GET  /rag/status                ChromaDB collection stats
```

### MCP Tools
```http
GET  /mcp/tools                 List all 10 tools
POST /mcp/call                  Call any tool: {"tool": "...", "inputs": {...}}
```

### Omo-Ghibe Living Lab
```http
GET  /omo-ghibe/zones           List 4 landscape zones with real data
POST /omo-ghibe/zones/{id}/diagnose  Full LIRA-AI pipeline on zone
GET  /omo-ghibe/compare         Side-by-side zone comparison
GET  /omo-ghibe/boundary        GeoJSON basin boundary
GET  /omo-ghibe/data-registry   Ethiopia data source catalogue
```

### Spatial Analysis
```http
GET  /spatial/basin/geojson     Enriched GeoJSON (LHII, syndromes, indicators)
GET  /spatial/zone/{id}/soil-erosion  RUSLE / GloSEM soil loss
POST /spatial/zone/{id}/narrative     AI narrative for a zone
```

### AI Narratives
```http
POST /ai/narrate                {"narrative_type": "syndrome|climate|pathway|...",
                                 "context": {...indicator values...}}
GET  /ai/status                 Provider availability (Ollama/Groq/HF)
```

### Climate & GARDIAN
```http
GET  /climate-data/cmip6/models           CMIP6 model catalog
POST /climate-data/cmip6/fetch-live       Live CMIP6 fetch from Planetary Computer
GET  /climate-data/gardian/search?q=...   Live CGSpace search
GET  /climate-data/gardian/evidence       Pre-harvested evidence cards
GET  /climate-data/sources/verified       Data source verification status
```

---

## Diagnostic Thresholds (configurable in `config/thresholds.yaml`)

| Indicator | Very Low | Low | Moderate | Severe | Very Severe |
|---|---|---|---|---|---|
| Soil loss (t/ha/yr) | < 2 | 2–10 | 10–20 | 20–50 | > 50 |
| SOC (g/kg) | < 10 | 10–20 | 20–50 | — | — |
| NDVI | < 0.10 | 0.10–0.25 | 0.25–0.40 | 0.40–0.60 | > 0.60 |
| Land productivity | < 0.2 | 0.2–0.4 | 0.4–0.6 | 0.6–0.8 | 0.8–1.0 |

All thresholds editable in YAML — no code changes needed for recalibration.

---

## 8 Degradation Syndromes (configurable in `config/syndromes.yaml`)

1. **Erosion–Productivity Decline** — steep slopes, exposed soil, high rainfall erosivity
2. **Moisture-Stress Syndrome** — low infiltration, dry spells, low soil cover
3. **Soil Carbon Depletion** — continuous tillage, residue burning, overgrazing
4. **Rangeland/Overgrazing** — overstocking, bare ground, invasive species
5. **Deforestation/Vegetation Loss** — agricultural expansion, fuelwood pressure
6. **Invasive Species/Woody Encroachment** — Prosopis invasion, disturbance
7. **Reservoir Sedimentation** — upstream erosion, gully expansion, deforestation
8. **Mixed High-Risk** — compound degradation across multiple processes

---

## Landscape Resilience Investment Priority Index

```
Priority Score =
  Current degradation severity   (0.20)  ← LHII indicator engine
+ Future climate risk            (0.20)  ← CMIP6 SSP scenarios
+ Ecosystem service value        (0.10)  ← NDVI + erosion proxy
+ Livelihood exposure            (0.10)  ← health score × completeness
+ Community priority             (0.10)  ← community intelligence form
+ Policy alignment               (0.10)  ← PolicyAlignmentAgent (10 frameworks)
+ Investment readiness           (0.10)  ← data completeness + policy score
+ Equity benefit                 (0.05)  ← community preferred future
- Maladaptation risk             (-0.10) ← tradeoff radar alerts
- Implementation barriers        (-0.05) ← safeguard notes count

All weights configurable in config/thresholds.yaml
```

---

## Testing

```bash
cd backend

# Unit tests (indicator engine)
PYTHONPATH=. pytest tests/test_indicator_engine.py -v     # 16 tests

# End-to-end tests (full pipeline + all agents + API)
PYTHONPATH=. pytest tests/test_end_to_end.py -v           # 67 tests

# All tests
PYTHONPATH=. pytest tests/ -v                             # 67/67 passing
```

---

## Frontend Pages (21 total)

| Page | URL | Connected Agents/Endpoints |
|---|---|---|
| Decision Cockpit | `/` | All agents status |
| Project Setup | `/setup` | `/projects/` |
| Evidence Cloud | `/evidence` | LandscapeEvidenceAgent, `/evidence/fetch` |
| Landscape Diagnosis | `/diagnosis` | Indicator engine + CausalDiagnosisAgent |
| Climate Futures | `/climate` | ClimateFuturesAgent + CMIP6 |
| CMIP6 + GARDIAN | `/climate-data` | NASA NEX GDDP, CGIAR CGSpace |
| Syndromes | `/syndromes` | SyndromeClassifier + CausalDiagnosisAgent |
| Regeneration Pathways | `/pathways` | PathwayGenerator |
| Tradeoff Radar | `/tradeoffs` | TradeoffMaladaptationAgent |
| Investment Passports | `/investment` | InvestmentPlanningAgent (GCF screening) |
| Community & Policy | `/community` | CommunityIntelligenceAgent + PolicyAlignmentAgent |
| Advisories | `/advisory` | AdvisoryCommunicationAgent |
| Monitoring & MELIA | `/monitoring` | AdaptiveMonitoringAgent + MELIA |
| **Knowledge Base** | `/knowledge` | RAG — CGSpace ingest, search, cards |
| **MCP Tool Explorer** | `/mcp-tools` | All 10 MCP tools, live runner |
| Spatial Map | `/map` | Leaflet + basin GeoJSON + zone click |
| Omo-Ghibe Lab | `/omo-ghibe` | All zone data + full diagnosis |
| Export | `/export` | JSON + Markdown reports |

All pages include **AI Summary** (Ollama tinyllama, auto-generate on data load).

---

## Design Principles

1. **Transparent calculations** — all thresholds in YAML, all logic in Python
2. **Explicit uncertainty** — every output has confidence level, data gaps, assumptions
3. **No AI invention** — LLM generates narrative only; all numbers from deterministic engines
4. **Human-in-the-loop** — every recommendation includes validation requirements
5. **Modular architecture** — each agent/engine upgradeable independently
6. **Ethiopia-grounded** — concrete use case; architecture scalable to any MFL landscape
7. **All data real** — 7/7 confirmed real data sources; clearly labelled when mock
8. **Academic + practical** — AI summaries cite CGIAR evidence, end with "Priority action:"

---

## Known Issues & Troubleshooting

### Frontend shows Application Error
```bash
# Clear stale .next build cache
rm -rf frontend/.next && cd frontend && npm run dev
```

### "Indexed CGSpace abstracts"

curl -X POST http://localhost:8000/rag/ingest-cgspace \
  -H "Content-Type: application/json" \
  -d '{"project_id":"your-project","multi_query":true}'
```

### Map shows "already initialized" error
The MapContainer cleanup ref handles this — ensure you're on the latest version.
If it persists: hard refresh (Cmd+Shift+R).

### CMIP6 fetch times out
Climate endpoint has a 20-second interactive timeout then falls back to eco-profile.
For full multi-model runs: `PYTHONPATH=. python scripts/prepare_cmip6_gardian.py`

---

## References

- Hurni, H. (1985). Erosion-productivity-conservation systems in Ethiopia. *ISCO Congress*.
- Borrelli, P. et al. (2021). GloSEM v1.2. *Nature Communications*. DOI: 10.5281/zenodo.6539253
- IPCC AR6 Chapter 9: Africa — climate projections for CMIP6 integration.
- Bewket, W. & Teferi, E. (2009). Soil erosion, Blue Nile highland. *Land Degradation & Development*.
- Vanlauwe, B. et al. (2015). ISFM in Sub-Saharan Africa. *Soil Science*.
- SoilGrids v2.0: Poggio, L. et al. (2021). *Soil* 7:217–240.
- CHIRPS: Funk, C. et al. (2015). *Scientific Data* 2:150066.
- Mekuria, W. et al. CGIAR CGSpace — indexed in LIRA-AI RAG knowledge base.

---
## ✍️ Author

- **Jemal Ahmed**  
- ✉️ **Contact:** [J.Ahmed@cgiar.org](mailto:J.Ahmed@cgiar.org)
- [Alliance of Bioversity International and CIAT](https://alliancebioversityciat.org)

---