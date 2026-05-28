"""
Diagnostic indicator engine.
All threshold-based classifications are deterministic Python functions.
No LLM guessing of scientific values.
"""

from __future__ import annotations
from typing import Optional
from app.config import THRESHOLDS
from app.models.indicators import IndicatorResult, LandscapeIndicators, DiagnosticResult


def _classify_by_ranges(value: float, threshold_key: str) -> tuple[str, float]:
    """
    Returns (category_name, severity_score 0-1).
    Severity score: 1 = worst / most degraded, 0 = best / healthy.
    """
    ranges = THRESHOLDS.get(threshold_key, {})
    # Severity ordering for soil loss rate
    if threshold_key == "soil_loss_rate":
        order = ["very_low", "low", "moderate", "severe", "very_severe"]
    elif threshold_key == "soil_moisture_pct":
        order = ["deficit", "limiting", "adequate", "surplus"]
    elif threshold_key == "soil_organic_carbon_g_per_kg":
        order = ["very_low", "low", "moderate", "high"]
    elif threshold_key == "land_productivity_index":
        order = ["very_low", "low", "moderate_low", "moderately_high", "high"]
    elif threshold_key == "ndvi":
        order = ["severe_degradation", "degraded", "sparse", "moderate", "healthy"]
    elif threshold_key == "slope_degrees":
        order = ["flat", "gentle", "moderate", "steep", "very_steep"]
    elif threshold_key == "rainfall_mm_annual":
        order = ["arid", "semi_arid", "sub_humid", "humid"]
    else:
        order = list(ranges.keys())

    matched = "unknown"
    for cat, bounds in ranges.items():
        lo = bounds.get("min", float("-inf"))
        hi = bounds.get("max", float("inf"))
        if lo <= value < hi or (bounds.get("min") is None and value < hi) or (bounds.get("max") is None and value >= lo):
            matched = cat
            break

    # Calculate severity score
    try:
        idx = order.index(matched)
    except ValueError:
        return matched, 0.5

    # Indicators where higher = worse (erosion, slope)
    higher_is_worse = {"soil_loss_rate", "slope_degrees"}
    # Indicators where lower = worse (productivity, SOC, moisture adequacy, NDVI, rainfall)
    lower_is_worse = {
        "land_productivity_index",
        "soil_organic_carbon_g_per_kg",
        "ndvi",
        "rainfall_mm_annual",
    }
    # Special moisture: deficit is worst, surplus is second-worst
    if threshold_key == "soil_moisture_pct":
        severity_map = {"deficit": 1.0, "limiting": 0.6, "adequate": 0.0, "surplus": 0.3}
        return matched, severity_map.get(matched, 0.5)

    if threshold_key in higher_is_worse:
        severity_score = idx / max(len(order) - 1, 1)
    elif threshold_key in lower_is_worse:
        severity_score = 1.0 - idx / max(len(order) - 1, 1)
    else:
        severity_score = 0.5

    return matched, round(severity_score, 3)


def _indicator_result(
    value: Optional[float],
    threshold_key: str,
    label: str,
    is_mock: bool = False,
) -> IndicatorResult:
    if value is None:
        return IndicatorResult(
            value=None,
            category="unknown",
            severity_score=0.5,
            threshold_used=threshold_key,
            data_gap=True,
            note=f"No data for {label}",
            is_mock=is_mock,
        )
    cat, score = _classify_by_ranges(value, threshold_key)
    return IndicatorResult(
        value=value,
        category=cat,
        severity_score=score,
        threshold_used=threshold_key,
        is_mock=is_mock,
    )


def run_indicator_engine(inp: LandscapeIndicators) -> DiagnosticResult:
    """
    Classify all available indicators and produce a composite health score.
    """
    m = inp.is_mock
    results: dict[str, IndicatorResult] = {}

    results["soil_loss_rate"] = _indicator_result(
        inp.soil_loss_rate_t_ha_yr, "soil_loss_rate", "Soil loss rate", m
    )
    results["soil_moisture"] = _indicator_result(
        inp.soil_moisture_pct, "soil_moisture_pct", "Soil moisture", m
    )
    results["soil_organic_carbon"] = _indicator_result(
        inp.soil_organic_carbon_g_per_kg,
        "soil_organic_carbon_g_per_kg",
        "Soil organic carbon",
        m,
    )
    results["land_productivity"] = _indicator_result(
        inp.land_productivity_index,
        "land_productivity_index",
        "Land productivity index",
        m,
    )
    results["ndvi"] = _indicator_result(
        inp.ndvi_mean, "ndvi", "NDVI mean", m
    )
    results["slope"] = _indicator_result(
        inp.slope_mean_degrees, "slope_degrees", "Mean slope", m
    )
    results["rainfall"] = _indicator_result(
        inp.rainfall_mm_annual, "rainfall_mm_annual", "Annual rainfall", m
    )

    # Land cover change: positive change = more degradation
    if inp.land_cover_change_pct_10yr is not None:
        change = inp.land_cover_change_pct_10yr
        if change > 20:
            lcc_cat, lcc_sev = "high", 0.9
        elif change > 10:
            lcc_cat, lcc_sev = "moderate", 0.6
        elif change > 0:
            lcc_cat, lcc_sev = "low", 0.3
        else:
            lcc_cat, lcc_sev = "stable_or_improving", 0.0
        results["land_cover_change"] = IndicatorResult(
            value=change,
            category=lcc_cat,
            severity_score=lcc_sev,
            threshold_used="land_cover_change_pct_10yr",
            is_mock=m,
        )
    else:
        results["land_cover_change"] = IndicatorResult(
            value=None, category="unknown", severity_score=0.5,
            threshold_used="land_cover_change_pct_10yr", data_gap=True, is_mock=m,
        )

    # Overgrazing proxy (already 0–1 severity)
    if inp.overgrazing_proxy is not None:
        og = inp.overgrazing_proxy
        results["overgrazing"] = IndicatorResult(
            value=og,
            category="high" if og > 0.66 else ("moderate" if og > 0.33 else "low"),
            severity_score=og,
            threshold_used="overgrazing_proxy",
            is_mock=m,
        )
    else:
        results["overgrazing"] = IndicatorResult(
            value=None, category="unknown", severity_score=0.5,
            threshold_used="overgrazing_proxy", data_gap=True, is_mock=m,
        )

    # Composite health score (inverse of mean severity, excluding data gaps)
    valid_scores = [
        r.severity_score for r in results.values() if not r.data_gap
    ]
    if valid_scores:
        mean_severity = sum(valid_scores) / len(valid_scores)
        composite_health = round(1.0 - mean_severity, 3)
    else:
        composite_health = 0.5

    total = len(results)
    gaps = [k for k, v in results.items() if v.data_gap]
    completeness = round((total - len(gaps)) / total * 100, 1)

    severity_label = (
        "very_severe" if composite_health < 0.2 else
        "severe"      if composite_health < 0.4 else
        "moderate"    if composite_health < 0.6 else
        "low"         if composite_health < 0.8 else
        "very_low"
    )

    return DiagnosticResult(
        project_id=inp.project_id,
        indicators=results,
        composite_health_score=composite_health,
        degradation_severity=severity_label,
        data_completeness_pct=completeness,
        data_gaps=gaps,
        is_mock=m,
    )
