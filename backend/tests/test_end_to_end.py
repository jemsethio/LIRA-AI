"""
End-to-end integration tests for LIRA-AI.
Tests the complete pipeline: Indicators → Syndromes → LHII → Pathways → Investment.
Also tests each agent independently with the Omo-Ghibe Ethiopia use case.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.indicators import LandscapeIndicators
from app.engines.indicator_engine import run_indicator_engine
from app.engines.syndrome_classifier import classify_syndromes
from app.engines.landscape_health_index import compute_lhii
from app.engines.causal_graph import build_causal_graph
from app.engines.pathway_generator import generate_pathways
from app.engines.priority_index import generate_investment_passport, calculate_priority_index
from app.engines.melia import generate_melia_report

client = TestClient(app)

# ── Ethiopia use case fixtures ─────────────────────────────────────────────────

OMO_HIGHLAND = {
    "project_id": "TEST-OMO-HIGHLAND",
    "soil_loss_rate_t_ha_yr": 28.4,
    "soil_moisture_pct": 62.0,
    "soil_organic_carbon_g_per_kg": 58.6,   # real SoilGrids value
    "soil_texture": "clay",
    "land_productivity_index": 0.61,
    "ndvi_mean": 0.446,                      # real Sentinel-2 value
    "evi_mean": 0.38,
    "ndvi_trend_5yr": -0.018,
    "slope_mean_degrees": 9.8,              # real DEM value
    "forest_cover_pct": 61.7,               # real WorldCover value
    "bare_soil_pct": 0.0,
    "land_cover_change_pct_10yr": -18.5,
    "rainfall_mm_annual": 1859.4,           # real CHIRPS value
    "temperature_mean_c": 15.0,             # real ERA5 value
    "dry_spell_days_per_year": 28,
    "drought_frequency_per_decade": 1,
    "overgrazing_proxy": 0.25,
    "reservoir_sedimentation_proxy": 0.38,
    "is_mock": False,
}

OMO_LOWLAND = {
    "project_id": "TEST-OMO-LOWLAND",
    "soil_loss_rate_t_ha_yr": 12.8,
    "soil_moisture_pct": 28.0,
    "soil_organic_carbon_g_per_kg": 28.2,   # real SoilGrids
    "soil_texture": "clay-loam",
    "land_productivity_index": 0.28,
    "ndvi_mean": 0.111,                     # real Sentinel-2
    "evi_mean": 0.09,
    "ndvi_trend_5yr": -0.031,
    "slope_mean_degrees": 9.1,
    "forest_cover_pct": 8.2,
    "bare_soil_pct": 32.5,
    "land_cover_change_pct_10yr": 21.8,
    "rainfall_mm_annual": 760.0,            # real CHIRPS
    "temperature_mean_c": 22.1,             # real ERA5
    "dry_spell_days_per_year": 82,
    "drought_frequency_per_decade": 5,
    "overgrazing_proxy": 0.78,
    "reservoir_sedimentation_proxy": 0.52,
    "is_mock": False,
}


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealth:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "LIRA-AI" in data["system"]
        assert data["status"] == "operational"
        assert len(data["agents"]) >= 10   # all 14 agents listed

    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_docs(self):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_openapi(self):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        assert "paths" in spec
        assert len(spec["paths"]) >= 40   # 64 routes


# ── Projects API ──────────────────────────────────────────────────────────────

class TestProjects:
    def test_create_project(self):
        r = client.post("/projects/", json={
            "name": "Omo-Ghibe Highland Test",
            "country": "Ethiopia",
            "region": "SNNPR",
            "admin_level": "Zone",
            "landscape_type": "watershed",
            "target_objective": "integrated",
            "notes": "Kafa-Sheka coffee-forest agroforestry zone",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Omo-Ghibe Highland Test"
        assert "id" in data
        return data["id"]

    def test_list_projects(self):
        r = client.get("/projects/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_project_lifecycle(self):
        # Create
        create = client.post("/projects/", json={
            "name": "Lifecycle Test",
            "country": "Ethiopia",
            "region": "Oromia",
            "admin_level": "Kebele",
            "landscape_type": "rangeland",
            "target_objective": "rangeland_restoration",
        })
        assert create.status_code == 201
        pid = create.json()["id"]

        # Get
        get = client.get(f"/projects/{pid}")
        assert get.status_code == 200
        assert get.json()["id"] == pid

        # Delete
        delete = client.delete(f"/projects/{pid}")
        assert delete.status_code == 204

        # Confirm deleted
        missing = client.get(f"/projects/{pid}")
        assert missing.status_code == 404


# ── Core engine pipeline ──────────────────────────────────────────────────────

class TestIndicatorEngine:
    def test_highland_real_data_classification(self):
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        result = run_indicator_engine(inds)

        # With real SoilGrids SOC=58.6 g/kg → "high" category
        soc = result.indicators["soil_organic_carbon"]
        assert soc.category == "high"
        assert soc.severity_score == 0.0

        # NDVI=0.446 → "moderate"
        ndvi = result.indicators["ndvi"]
        assert ndvi.category in ("moderate", "sparse", "healthy")

        # Rainfall=1859mm → sub_humid or humid
        rain = result.indicators["rainfall"]
        assert rain.category in ("sub_humid", "humid")
        assert rain.severity_score < 0.3   # adequate rainfall

        # Completeness should be high (all filled)
        assert result.data_completeness_pct >= 80.0
        assert result.is_mock is False

    def test_lowland_degraded_classification(self):
        inds = LandscapeIndicators(**OMO_LOWLAND)
        result = run_indicator_engine(inds)

        assert result.degradation_severity in ("severe", "very_severe", "moderate")
        assert result.composite_health_score < 0.5

        moist = result.indicators["soil_moisture"]
        assert moist.category == "deficit"
        assert moist.severity_score == 1.0

    def test_data_completeness(self):
        # Minimal input
        inds = LandscapeIndicators(project_id="MIN-TEST", is_mock=True)
        r = run_indicator_engine(inds)
        assert r.data_completeness_pct == 0.0
        assert len(r.data_gaps) > 0

    def test_composite_score_range(self):
        for indicators in [OMO_HIGHLAND, OMO_LOWLAND]:
            inds = LandscapeIndicators(**indicators)
            r = run_indicator_engine(inds)
            assert 0.0 <= r.composite_health_score <= 1.0


class TestSyndromeClassifier:
    def test_highland_primary_syndrome(self):
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)

        # Highland: declining forest, moderate erosion → deforestation or mixed
        assert synd.primary_syndrome.syndrome_id in (
            "deforestation_vegetation_loss", "erosion_productivity_decline",
            "reservoir_sedimentation", "mixed_high_risk"
        )
        assert synd.primary_syndrome.risk_level in ("high", "very_high", "medium")
        assert synd.primary_syndrome.match_score > 0
        assert synd.causal_narrative != ""
        assert len(synd.assumptions) > 0

    def test_lowland_overgrazing_syndrome(self):
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)

        # Lowland: high overgrazing proxy, low NDVI, moisture deficit
        all_syndromes = [s.syndrome_id for s in synd.all_syndromes]
        # At least one rangeland-related or moisture-related syndrome
        has_relevant = any(
            s in all_syndromes for s in
            ["rangeland_overgrazing", "moisture_stress", "mixed_high_risk"]
        )
        assert has_relevant, f"Expected rangeland/moisture syndrome, got: {all_syndromes}"
        assert synd.primary_syndrome.risk_level in ("high", "very_high")

    def test_syndrome_has_required_fields(self):
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)

        p = synd.primary_syndrome
        assert p.syndrome_id != ""
        assert p.name != ""
        assert isinstance(p.main_symptoms, list)
        assert isinstance(p.likely_drivers, list)
        assert isinstance(p.suggested_validation, list)


class TestLandscapeHealthIndex:
    def test_lhii_highland(self):
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        lhii = compute_lhii(diag)

        assert 0.0 <= lhii.overall_lhii <= 1.0
        assert lhii.lhii_class in ("good", "fair", "excellent")
        assert len(lhii.components) == 6  # 6 weighted components
        assert lhii.dominant_constraint != ""
        assert lhii.interpretation != ""

    def test_lhii_lowland_degraded(self):
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        lhii = compute_lhii(diag)

        assert lhii.lhii_class in ("degraded", "severely_degraded", "fair")
        assert lhii.overall_lhii < 0.55

    def test_lhii_has_hotspots_greenspots(self):
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        lhii = compute_lhii(diag)
        # Must return some zone classification
        total_zones = len(lhii.hotspots) + len(lhii.green_spots) + len(lhii.transition_zones)
        assert total_zones > 0


class TestCausalGraph:
    def test_graph_has_nodes_edges(self):
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)
        graph = build_causal_graph(synd)

        assert graph["node_count"] > 0
        assert graph["edge_count"] > 0
        assert isinstance(graph["nodes"], list)
        assert isinstance(graph["edges"], list)
        assert "active_syndromes" in graph

    def test_node_types_valid(self):
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)
        graph = build_causal_graph(synd)

        valid_types = {"driver", "process", "impact", "intervention"}
        for node in graph["nodes"]:
            assert node["type"] in valid_types


# ── Agent layer ───────────────────────────────────────────────────────────────

class TestSoilAgent:
    def test_soil_report_highland(self):
        from app.agents.soil_agent import SoilAgent
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        agent = SoilAgent()
        output = agent.run(project_id="TEST", diagnostic=diag, soil_texture="clay")
        assert output.success
        r = output.result
        assert r.erosion_risk != ""
        assert 0.0 <= r.erosion_severity_score <= 1.0
        assert isinstance(r.restoration_entry_points, list)

    def test_soil_report_lowland(self):
        from app.agents.soil_agent import SoilAgent
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        agent = SoilAgent()
        output = agent.run(project_id="TEST", diagnostic=diag)
        assert output.success
        r = output.result
        assert len(r.hotspot_flags) > 0   # lowland should have hotspots


class TestWaterAgent:
    def test_water_report(self):
        from app.agents.water_agent import WaterHydrologyAgent
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        agent = WaterHydrologyAgent()
        output = agent.run(project_id="TEST", diagnostic=diag)
        assert output.success
        r = output.result
        assert 0.0 <= r.runoff_risk_score <= 1.0
        assert 0.0 <= r.sediment_risk_score <= 1.0
        assert isinstance(r.intervention_priorities, list)


class TestVegetationAgent:
    def test_vegetation_report(self):
        from app.agents.vegetation_agent import VegetationBiodiversityAgent
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        agent = VegetationBiodiversityAgent()
        output = agent.run(project_id="TEST", diagnostic=diag)
        assert output.success
        r = output.result
        assert 0.0 <= r.vegetation_score <= 1.0
        assert r.deforestation_risk in ("low", "moderate", "high", "very_high")
        assert 0.0 <= r.recovery_potential_score <= 1.0


class TestRangelandAgent:
    def test_rangeland_report_lowland(self):
        from app.agents.rangeland_agent import RangelandLivestockAgent
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        agent = RangelandLivestockAgent()
        output = agent.run(project_id="TEST", diagnostic=diag)
        assert output.success
        r = output.result
        assert r.grazing_pressure in ("low", "moderate", "high", "very_high")
        assert r.rangeland_condition in ("good", "fair", "degraded", "severely_degraded")
        assert isinstance(r.restoration_options, list)
        assert len(r.restoration_options) > 0


class TestAgronomyAgent:
    def test_agronomy_highland(self):
        from app.agents.agronomy_agent import AgronomyAgent
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        agent = AgronomyAgent()
        output = agent.run(project_id="TEST", diagnostic=diag, soil_texture="clay")
        assert output.success
        r = output.result
        assert r.soil_fertility_status in ("adequate", "moderate", "low", "severely_depleted")
        assert len(r.crop_suitability) == 8  # all 8 crops scored
        # Coffee should be highly suitable in highland
        coffee = next((c for c in r.crop_suitability if c.crop == "coffee"), None)
        assert coffee is not None
        assert coffee.suitability in ("highly_suitable", "suitable")
        assert isinstance(r.isfm_recommendations, list)
        assert isinstance(r.climate_smart_practices, list)

    def test_agronomy_lowland_drought_crops(self):
        from app.agents.agronomy_agent import AgronomyAgent
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        agent = AgronomyAgent()
        output = agent.run(project_id="TEST", diagnostic=diag)
        assert output.success
        r = output.result
        # Sorghum should score better than maize in drought-prone lowland
        sorghum = next((c for c in r.crop_suitability if c.crop == "sorghum"), None)
        maize   = next((c for c in r.crop_suitability if c.crop == "maize"),   None)
        assert sorghum and maize
        assert sorghum.score >= maize.score


class TestAdaptiveMonitoringAgent:
    def test_monitoring_with_mock_bbox(self):
        from app.agents.adaptive_monitoring_agent import AdaptiveMonitoringAgent
        agent = AdaptiveMonitoringAgent()
        output = agent.run(
            project_id="TEST",
            bbox=[36.1, 7.6, 36.4, 7.9],
            baseline_date_range="2020-01-01/2021-01-01",
            current_date_range="2023-01-01/2024-01-01",
            is_mock=True,
        )
        assert output.success
        r = output.result
        assert r.recovery_trajectory in ("improving", "stable", "declining", "insufficient_data")
        assert isinstance(r.alerts, list)
        assert r.next_monitoring_date != ""


class TestAdvisoryAgent:
    def test_advisory_generates_all_audiences(self):
        from app.agents.advisory_agent import AdvisoryCommunicationAgent
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)
        agent = AdvisoryCommunicationAgent()
        output = agent.run(
            project_id="TEST",
            syndrome=synd,
            degradation_severity="severe",
        )
        assert output.success
        r = output.result
        assert r.farmer_advisory.headline != ""
        assert r.pastoralist_advisory.headline != ""
        assert r.planner_brief.title != ""
        assert r.investor_note.title != ""
        assert len(r.extension_messages) > 0
        assert len(r.equity_notes) > 0


# ── Pathway and investment pipeline ──────────────────────────────────────────

class TestPathwayGenerator:
    def test_seven_pathways_generated(self):
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)
        ps = generate_pathways(synd)

        assert len(ps.pathways) == 7
        assert ps.recommended_primary != ""
        pathway_types = {p.pathway_type.value for p in ps.pathways}
        assert "investment_ready" in pathway_types
        assert "climate_robust" in pathway_types

    def test_each_pathway_has_package(self):
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)
        ps = generate_pathways(synd)

        for pathway in ps.pathways:
            assert len(pathway.recommended_package) > 0
            assert pathway.why_it_fits != ""
            assert pathway.cost_category in ("low", "medium", "high", "very_high")
            assert len(pathway.monitoring_indicators) > 0
            assert len(pathway.assumptions) > 0


class TestTradeoffAgent:
    def test_tradeoff_radar_13_dimensions(self):
        from app.agents.tradeoff_agent import TradeoffMaladaptationAgent
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)
        ps = generate_pathways(synd)
        agent = TradeoffMaladaptationAgent()
        output = agent.run(project_id="TEST", pathways=ps.pathways)
        assert output.success
        r = output.result
        assert len(r.radars) == 7
        for radar in r.radars:
            assert len(radar.scores) == 13
            assert 0.0 <= radar.overall_risk <= 1.0
            assert radar.pathway_type != ""


class TestInvestmentPassport:
    def test_passport_generated(self):
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        passport = generate_investment_passport(
            project_id="TEST-OMO-LOWLAND",
            package_name="South Omo Rangeland Restoration Package",
            target_geography="South Omo Zone — Lowland Pastoral Areas",
            diagnostic=diag,
            climate=None,
            community=None,
            policy=None,
            pathway_components=["Rotational Grazing", "Area Closure", "Water Harvesting"],
        )
        assert passport.passport_id != ""
        assert 0.0 <= passport.investment_readiness_score <= 1.0
        assert 0.0 <= passport.climate_robustness_score <= 1.0
        assert 0.0 <= passport.confidence_score <= 1.0
        assert len(passport.intervention_components) == 3
        assert len(passport.expected_ecosystem_benefits) > 0
        assert len(passport.assumptions) > 0

    def test_priority_index_calculated(self):
        inds = LandscapeIndicators(**OMO_LOWLAND)
        diag = run_indicator_engine(inds)
        passport = generate_investment_passport(
            project_id="TEST", package_name="Test Package",
            target_geography="Test", diagnostic=diag,
            climate=None, community=None, policy=None,
            pathway_components=["Area Closure"],
        )
        idx = calculate_priority_index(passport, diag, None, None, None)
        assert 0.0 <= idx.weighted_score <= 1.0
        assert len(idx.scores) >= 8   # 8+ component scores
        assert idx.explanation != ""


# ── MELIA framework ───────────────────────────────────────────────────────────

class TestMELIA:
    def test_melia_report_generated(self):
        report = generate_melia_report(
            project_id="TEST",
            syndromes_classified=1,
            pathways_generated=7,
            passports_created=1,
            community_score=0.65,
            field_validation_done=False,
            policy_briefs_generated=1,
            re_prescriptions=0,
        )
        assert report.project_id == "TEST"
        assert len(report.indicators) == 7
        assert report.overall_progress in ("on_track", "partial", "lagging")
        assert report.summary != ""
        assert report.next_review_date != ""

    def test_melia_status_reflects_inputs(self):
        # High performance inputs → on_track
        r_good = generate_melia_report(
            "TEST", syndromes_classified=1, pathways_generated=7,
            passports_created=2, community_score=0.8,
            field_validation_done=True, policy_briefs_generated=3, re_prescriptions=1,
        )
        # No performance → lagging
        r_poor = generate_melia_report("TEST", syndromes_classified=0,
            pathways_generated=0, passports_created=0)
        assert r_good.overall_progress in ("on_track", "partial")
        assert r_poor.overall_progress in ("lagging", "partial")


# ── Omo-Ghibe API endpoints ───────────────────────────────────────────────────

class TestOmoGhibeAPI:
    def test_zones_endpoint(self):
        r = client.get("/omo-ghibe/zones")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # All 4 zones should be present (files on disk)
        zone_ids = {z["zone_id"] for z in data if "zone_id" in z}
        assert "highland" in zone_ids
        assert "lowland_pastoral" in zone_ids

    def test_boundary_endpoint(self):
        r = client.get("/omo-ghibe/boundary")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) >= 5   # 1 basin + 4 zones

    def test_highland_indicators(self):
        r = client.get("/omo-ghibe/zones/highland/indicators")
        assert r.status_code == 200
        data = r.json()
        assert data["ndvi_mean"] is not None
        assert data["soil_organic_carbon_g_per_kg"] is not None
        assert data["rainfall_mm_annual"] is not None
        # Real values from confirmed fetch
        assert 40 < data["soil_organic_carbon_g_per_kg"] < 80  # SoilGrids real: 58.6
        assert data["is_mock"] is False

    def test_diagnose_zone_pipeline(self):
        r = client.post("/omo-ghibe/zones/highland/diagnose")
        assert r.status_code == 200
        data = r.json()
        assert "diagnostic" in data
        assert "syndromes" in data
        assert "lhii" in data
        assert data["diagnostic"]["data_completeness_pct"] > 0
        assert data["lhii"]["overall_lhii"] > 0
        assert data["syndromes"]["primary_syndrome"]["name"] != ""

    def test_compare_all_zones(self):
        r = client.get("/omo-ghibe/compare")
        assert r.status_code == 200
        data = r.json()
        assert "zones" in data
        assert len(data["zones"]) == 4
        # Highland should have higher NDVI than lowland
        h = data["zones"].get("highland", {})
        l = data["zones"].get("lowland_pastoral", {})
        if h.get("ndvi_mean") and l.get("ndvi_mean"):
            assert h["ndvi_mean"] > l["ndvi_mean"]

    def test_data_registry(self):
        r = client.get("/omo-ghibe/data-registry")
        assert r.status_code == 200
        data = r.json()
        assert "sources" in data
        assert len(data["sources"]) >= 5


# ── Evidence and CMIP6 endpoints ─────────────────────────────────────────────

class TestClimateDataAPI:
    def test_cmip6_models_endpoint(self):
        r = client.get("/climate-data/cmip6/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert "MIROC6" in data["models"]
        assert "collection" in data
        assert data["collection"] == "nasa-nex-gddp-cmip6"

    def test_gardian_search(self):
        r = client.get("/climate-data/gardian/search?q=Ethiopia+landscape+degradation&size=5")
        assert r.status_code == 200
        data = r.json()
        assert data["total_results"] > 0
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0
        # Verify result structure
        if data["results"]:
            first = data["results"][0]
            assert "title" in first
            assert "cgspace_url" in first

    def test_evidence_catalog(self):
        r = client.get("/evidence/sources/catalog")
        assert r.status_code == 200
        data = r.json()
        assert "sources" in data
        src_names = [s["name"] for s in data["sources"]]
        assert "Sentinel-2 L2A" in src_names
        assert "SoilGrids v2.0" in src_names
        assert "CHIRPS v2.0" in src_names


# ── Agronomy endpoint ─────────────────────────────────────────────────────────

class TestAgronomyAPI:
    def test_agronomy_endpoint(self):
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)

        r = client.post(
            "/agronomy/TEST-AGRO",
            json=diag.model_dump(),
        )
        assert r.status_code == 200
        data = r.json()
        assert "soil_fertility_status" in data
        assert "crop_suitability" in data
        assert len(data["crop_suitability"]) == 8
        assert "isfm_recommendations" in data
        assert "climate_smart_practices" in data

    def test_agronomy_get(self):
        # Run first, then get
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        client.post("/agronomy/TEST-AGRO-GET", json=diag.model_dump())
        r = client.get("/agronomy/TEST-AGRO-GET")
        assert r.status_code == 200


# ── Export pipeline ───────────────────────────────────────────────────────────

class TestExport:
    def _make_bundle(self, zone_id="highland"):
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        synd = classify_syndromes(diag)
        ps   = generate_pathways(synd)
        passport = generate_investment_passport(
            project_id="TEST", package_name="Highland Restoration",
            target_geography="Kafa-Sheka", diagnostic=diag,
            climate=None, community=None, policy=None,
            pathway_components=["Area Closure", "FMNR", "Compost"],
        )
        return {
            "project_id": "TEST",
            "project_name": "Omo-Ghibe Highland Test",
            "diagnostic": diag.model_dump(),
            "syndrome": synd.model_dump(),
            "climate": None,
            "pathways": ps.model_dump(),
            "tradeoffs": None,
            "passports": [passport.model_dump()],
            "priority_index": [],
        }

    def test_json_export(self):
        bundle = self._make_bundle()
        r = client.post("/export/json", json=bundle)
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == "TEST"
        assert "diagnostic" in data

    def test_markdown_export(self):
        bundle = self._make_bundle()
        r = client.post("/export/markdown", json=bundle)
        assert r.status_code == 200
        md = r.text
        assert "LIRA-AI Report" in md
        assert "Landscape Diagnosis" in md
        assert "Degradation Syndrome" in md
        assert "Investment Passport" in md
        assert "ASSUMPTION" in md or "Generated by LIRA-AI" in md

    def test_markdown_has_all_sections(self):
        bundle = self._make_bundle()
        r = client.post("/export/markdown", json=bundle)
        md = r.text
        sections = ["Landscape Diagnosis", "Degradation Syndrome", "Regeneration Pathways", "Investment Passports"]
        for section in sections:
            assert section in md, f"Missing section: {section}"


# ── Full pipeline integration ─────────────────────────────────────────────────

class TestFullPipeline:
    """Test the complete LIRA-AI pipeline end-to-end."""

    def test_complete_pipeline_highland(self):
        """End-to-end: indicators → syndromes → LHII → causal graph → pathways → passport → priority index."""
        # 1. Indicators
        inds = LandscapeIndicators(**OMO_HIGHLAND)
        diag = run_indicator_engine(inds)
        assert diag.composite_health_score > 0
        assert diag.is_mock is False

        # 2. Syndromes
        synd = classify_syndromes(diag)
        assert synd.primary_syndrome.syndrome_id != "unknown"
        assert len(synd.all_syndromes) >= 1

        # 3. LHII
        lhii = compute_lhii(diag)
        assert lhii.overall_lhii > 0
        assert len(lhii.components) == 6

        # 4. Causal graph
        graph = build_causal_graph(synd)
        assert graph["node_count"] > 0
        assert graph["edge_count"] > 0

        # 5. Pathways (7 types)
        ps = generate_pathways(synd)
        assert len(ps.pathways) == 7

        # 6. Investment passport
        passport = generate_investment_passport(
            project_id="OMO-HIGHLAND",
            package_name="Highland Restoration",
            target_geography="Kafa-Sheka", diagnostic=diag,
            climate=None, community=None, policy=None,
            pathway_components=["FMNR", "Area Closure", "Native Reforestation"],
        )
        assert 0.0 <= passport.investment_readiness_score <= 1.0

        # 7. Priority index
        idx = calculate_priority_index(passport, diag, None, None, None)
        assert 0.0 <= idx.weighted_score <= 1.0
        assert idx.rank == 1

    def test_complete_pipeline_via_api(self):
        """Test the same pipeline through the HTTP API."""
        # Create project
        proj = client.post("/projects/", json={
            "name": "API E2E Test",
            "country": "Ethiopia",
            "region": "SNNPR",
            "admin_level": "Zone",
            "landscape_type": "watershed",
            "target_objective": "integrated",
        })
        assert proj.status_code == 201
        pid = proj.json()["id"]

        # Run indicators
        ind_payload = {**OMO_HIGHLAND, "project_id": pid}
        diag_r = client.post("/diagnosis/indicators", json=ind_payload)
        assert diag_r.status_code == 200
        diag_data = diag_r.json()
        assert diag_data["data_completeness_pct"] > 0

        # Classify syndromes
        synd_r = client.post(f"/diagnosis/syndromes/{pid}", json={})
        assert synd_r.status_code == 200
        synd_data = synd_r.json()
        assert synd_data["primary_syndrome"]["name"] != ""

        # Causal graph
        graph_r = client.get(f"/diagnosis/causal-graph/{pid}")
        assert graph_r.status_code == 200
        assert graph_r.json()["node_count"] > 0

        # Generate pathways — router expects {"syndrome": {...}, "climate": null}
        pw_r = client.post(f"/pathways/{pid}/generate", json={"syndrome": synd_data, "climate": None})
        assert pw_r.status_code == 200
        pw_data = pw_r.json()
        assert len(pw_data["pathways"]) == 7

        # Tradeoffs
        tr_r = client.post(f"/pathways/{pid}/tradeoffs")
        assert tr_r.status_code == 200
        tr_data = tr_r.json()
        assert len(tr_data["radars"]) == 7

        # Cleanup
        client.delete(f"/projects/{pid}")


# ── Phase 13 spatial endpoint stubs (RED phase — XFAIL until Plan 13-01) ─────

@pytest.mark.xfail(reason="endpoint not yet implemented — Plan 13-01", strict=False)
def test_spatial_zones_aggregate():
    r = client.get("/spatial/zones/aggregate?zone_ids=highland")
    assert r.status_code == 200
    body = r.json()
    assert "lhii_score" in body or "mean_lhii" in body, f"Expected lhii field, got: {list(body.keys())}"
    assert "ndvi" in str(body), f"Expected ndvi field, got: {list(body.keys())}"
    assert "dominant_syndrome" in body or "aggregate" in body, f"Expected syndrome field, got: {list(body.keys())}"


@pytest.mark.xfail(reason="endpoint not yet implemented — Plan 13-01", strict=False)
def test_spatial_zone_ndvi_history():
    r = client.get("/spatial/zone/highland/ndvi-history?start_year=2020&end_year=2025")
    assert r.status_code == 200
    body = r.json()
    history = body.get("series") or body.get("history") or body.get("data") or []
    assert len(history) == 6, f"Expected 6 items (2020-2025), got {len(history)}: {history}"


@pytest.mark.xfail(reason="endpoint not yet implemented — Plan 13-01", strict=False)
def test_spatial_export_geotiff_ok():
    r = client.get("/spatial/export/geotiff?layer=ndvi&zone_ids=highland")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/tiff"), \
        f"Expected image/tiff, got: {r.headers.get('content-type')}"
    disp = r.headers.get("content-disposition", "")
    assert ".tif" in disp, f"Expected .tif in Content-Disposition, got: {disp!r}"


@pytest.mark.xfail(reason="endpoint not yet implemented — Plan 13-01", strict=False)
def test_spatial_export_geotiff_unknown_zone():
    r = client.get("/spatial/export/geotiff?layer=ndvi&zone_ids=nonexistent")
    assert r.status_code == 404
