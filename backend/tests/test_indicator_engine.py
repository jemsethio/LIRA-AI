"""
Unit tests for the LIRA-AI diagnostic indicator engine.
All tests use transparent inputs and expected outputs — no mocking of scientific values.
"""

import pytest
from app.models.indicators import LandscapeIndicators
from app.engines.indicator_engine import run_indicator_engine


def make_indicators(**kwargs) -> LandscapeIndicators:
    defaults = dict(
        project_id="TEST-001",
        soil_loss_rate_t_ha_yr=None,
        soil_moisture_pct=None,
        soil_organic_carbon_g_per_kg=None,
        land_productivity_index=None,
        ndvi_mean=None,
        slope_mean_degrees=None,
        rainfall_mm_annual=None,
        overgrazing_proxy=None,
        land_cover_change_pct_10yr=None,
        is_mock=True,
    )
    defaults.update(kwargs)
    return LandscapeIndicators(**defaults)


class TestSoilLossClassification:
    def test_very_low(self):
        ind = make_indicators(soil_loss_rate_t_ha_yr=1.0)
        result = run_indicator_engine(ind)
        r = result.indicators["soil_loss_rate"]
        assert r.category == "very_low"
        assert r.severity_score < 0.2

    def test_moderate(self):
        ind = make_indicators(soil_loss_rate_t_ha_yr=15.0)
        result = run_indicator_engine(ind)
        r = result.indicators["soil_loss_rate"]
        assert r.category == "moderate"
        assert 0.3 < r.severity_score < 0.7

    def test_severe(self):
        ind = make_indicators(soil_loss_rate_t_ha_yr=32.0)
        result = run_indicator_engine(ind)
        r = result.indicators["soil_loss_rate"]
        assert r.category == "severe"
        assert r.severity_score > 0.6

    def test_very_severe(self):
        ind = make_indicators(soil_loss_rate_t_ha_yr=75.0)
        result = run_indicator_engine(ind)
        r = result.indicators["soil_loss_rate"]
        assert r.category == "very_severe"
        assert r.severity_score > 0.9


class TestSoilMoistureClassification:
    def test_deficit(self):
        ind = make_indicators(soil_moisture_pct=20.0)
        result = run_indicator_engine(ind)
        r = result.indicators["soil_moisture"]
        assert r.category == "deficit"
        assert r.severity_score == 1.0

    def test_adequate(self):
        ind = make_indicators(soil_moisture_pct=75.0)
        result = run_indicator_engine(ind)
        r = result.indicators["soil_moisture"]
        assert r.category == "adequate"
        assert r.severity_score == 0.0


class TestSOCClassification:
    def test_very_low(self):
        ind = make_indicators(soil_organic_carbon_g_per_kg=5.0)
        result = run_indicator_engine(ind)
        r = result.indicators["soil_organic_carbon"]
        assert r.category == "very_low"
        assert r.severity_score == 1.0

    def test_high(self):
        ind = make_indicators(soil_organic_carbon_g_per_kg=60.0)
        result = run_indicator_engine(ind)
        r = result.indicators["soil_organic_carbon"]
        assert r.category == "high"
        assert r.severity_score == 0.0


class TestLandProductivityClassification:
    def test_very_low(self):
        ind = make_indicators(land_productivity_index=0.1)
        result = run_indicator_engine(ind)
        r = result.indicators["land_productivity"]
        assert r.category == "very_low"
        assert r.severity_score == 1.0

    def test_high(self):
        ind = make_indicators(land_productivity_index=0.9)
        result = run_indicator_engine(ind)
        r = result.indicators["land_productivity"]
        assert r.category == "high"
        assert r.severity_score == 0.0


class TestCompositeHealthScore:
    def test_all_degraded_gives_low_health(self):
        ind = make_indicators(
            soil_loss_rate_t_ha_yr=60.0,
            soil_moisture_pct=15.0,
            soil_organic_carbon_g_per_kg=5.0,
            land_productivity_index=0.1,
            ndvi_mean=0.05,
        )
        result = run_indicator_engine(ind)
        assert result.composite_health_score < 0.3

    def test_all_healthy_gives_high_health(self):
        ind = make_indicators(
            soil_loss_rate_t_ha_yr=1.0,
            soil_moisture_pct=75.0,
            soil_organic_carbon_g_per_kg=55.0,
            land_productivity_index=0.9,
            ndvi_mean=0.7,
        )
        result = run_indicator_engine(ind)
        assert result.composite_health_score > 0.7

    def test_data_gaps_counted(self):
        ind = make_indicators()  # all None
        result = run_indicator_engine(ind)
        assert result.data_completeness_pct == 0.0
        assert len(result.data_gaps) > 0

    def test_partial_data_completeness(self):
        ind = make_indicators(
            soil_loss_rate_t_ha_yr=10.0,
            ndvi_mean=0.3,
        )
        result = run_indicator_engine(ind)
        assert 0 < result.data_completeness_pct < 100


class TestSyndromeMockEthiopiaCase:
    def test_ethiopia_sample_triggers_erosion_syndrome(self):
        from app.engines.syndrome_classifier import classify_syndromes

        ind = make_indicators(
            soil_loss_rate_t_ha_yr=32.5,
            soil_moisture_pct=38,
            soil_organic_carbon_g_per_kg=14.2,
            land_productivity_index=0.31,
            ndvi_mean=0.28,
            slope_mean_degrees=18,
            land_cover_change_pct_10yr=15.4,
            overgrazing_proxy=0.68,
        )
        diagnostic = run_indicator_engine(ind)
        syndrome_diag = classify_syndromes(diagnostic)

        # Primary syndrome should be erosion or high-risk
        assert syndrome_diag.primary_syndrome.syndrome_id in (
            "erosion_productivity_decline", "mixed_high_risk", "rangeland_overgrazing"
        )
        assert syndrome_diag.primary_syndrome.risk_level in ("high", "very_high")


class TestPriorityIndex:
    def test_score_between_0_and_1(self):
        from app.models.investment import InvestmentPassport
        from app.engines.priority_index import calculate_priority_index, generate_investment_passport
        import uuid

        ind = make_indicators(
            soil_loss_rate_t_ha_yr=32.5,
            soil_moisture_pct=38,
            ndvi_mean=0.28,
        )
        diagnostic = run_indicator_engine(ind)

        passport = generate_investment_passport(
            project_id="TEST-001",
            package_name="Test Package",
            target_geography="Test Zone",
            diagnostic=diagnostic,
            climate=None,
            community=None,
            policy=None,
            pathway_components=["Soil Bunds", "Area Closure"],
        )

        result = calculate_priority_index(passport, diagnostic, None, None, None)
        assert 0.0 <= result.weighted_score <= 1.0
        assert result.project_id == "TEST-001"
