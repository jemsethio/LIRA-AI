"""
Degradation syndrome classifier.
Rule-based matching against SYNDROMES config — fully transparent and auditable.
"""

from __future__ import annotations
from app.config import SYNDROMES
from app.models.indicators import DiagnosticResult, IndicatorResult
from app.models.syndromes import SyndromeMatch, SyndromeDiagnosis


# Map syndrome triggering_indicator strings to indicator result keys + severity logic
_TRIGGER_MAP: dict[str, tuple[str, str, float]] = {
    # "trigger_string": (result_key, comparator, threshold)
    "soil_loss_rate >= moderate":           ("soil_loss_rate",     "sev>=", 0.4),
    "soil_loss_rate >= severe":             ("soil_loss_rate",     "sev>=", 0.7),
    "land_productivity_index <= low":       ("land_productivity",  "sev>=", 0.7),
    "land_productivity_index <= moderate_low": ("land_productivity", "sev>=", 0.4),
    "soil_moisture_pct <= limiting":        ("soil_moisture",      "sev>=", 0.6),
    "ndvi <= sparse":                       ("ndvi",               "sev>=", 0.4),
    "ndvi <= degraded":                     ("ndvi",               "sev>=", 0.6),
    "ndvi >= moderate":                     ("ndvi",               "sev<=", 0.4),
    "overgrazing_proxy >= high":            ("overgrazing",        "sev>=", 0.6),
    "land_cover_change_risk >= high":       ("land_cover_change",  "sev>=", 0.7),
    "slope_dominant >= steep":              ("slope",              "sev>=", 0.6),
    "soil_organic_carbon_g_per_kg <= low":  ("soil_organic_carbon","sev>=", 0.7),
    "multiple_severe_indicators >= 3":      ("_multi",             "count>=", 3),
}


def _check_trigger(trigger: str, indicators: dict[str, IndicatorResult]) -> bool:
    mapping = _TRIGGER_MAP.get(trigger)
    if mapping is None:
        return False

    key, op, threshold = mapping

    if key == "_multi":
        severe_count = sum(
            1 for r in indicators.values()
            if not r.data_gap and r.severity_score >= 0.6
        )
        return severe_count >= int(threshold)

    result = indicators.get(key)
    if result is None or result.data_gap:
        return False

    if op == "sev>=":
        return result.severity_score >= threshold
    elif op == "sev<=":
        return result.severity_score <= threshold
    return False


def _match_syndrome(
    syndrome_id: str,
    syndrome_def: dict,
    indicators: dict[str, IndicatorResult],
) -> SyndromeMatch | None:
    triggers = syndrome_def.get("triggering_indicators", [])
    if not triggers:
        return None

    matched = [t for t in triggers if _check_trigger(t, indicators)]
    match_ratio = len(matched) / len(triggers)

    if match_ratio == 0:
        return None

    # Confidence: reduce if data gaps exist
    gaps = [k for k, v in indicators.items() if v.data_gap]
    confidence = syndrome_def.get("default_confidence", "medium")
    if len(gaps) > 3:
        confidence = "low"

    return SyndromeMatch(
        syndrome_id=syndrome_id,
        name=syndrome_def["name"],
        risk_level=syndrome_def.get("risk_level", "medium"),
        confidence=confidence,
        triggering_indicators=matched,
        main_symptoms=syndrome_def.get("main_symptoms", []),
        likely_drivers=syndrome_def.get("likely_drivers", []),
        data_gaps=syndrome_def.get("data_gaps", []),
        suggested_validation=syndrome_def.get("suggested_validation", []),
        match_score=round(match_ratio, 2),
    )


def classify_syndromes(diagnostic: DiagnosticResult) -> SyndromeDiagnosis:
    indicators = diagnostic.indicators
    matches: list[SyndromeMatch] = []

    for sid, sdef in SYNDROMES.items():
        match = _match_syndrome(sid, sdef, indicators)
        if match:
            matches.append(match)

    matches.sort(key=lambda m: (m.match_score, _risk_order(m.risk_level)), reverse=True)

    primary = matches[0] if matches else _unknown_syndrome()
    secondary = matches[1:4]

    # Narrative — template-based (LLM can enhance this later)
    narrative = _build_narrative(primary, secondary, diagnostic)

    assumptions = [
        "Proxy indicators (overgrazing, land cover change) are estimated from available data.",
        "Confidence levels reflect data completeness, not field validation.",
        "Syndrome matching uses rule-based thresholds; field verification is required.",
    ]
    needs_validation = list({
        item
        for m in matches
        for item in m.suggested_validation
    })

    return SyndromeDiagnosis(
        project_id=diagnostic.project_id,
        primary_syndrome=primary,
        secondary_syndromes=secondary,
        all_syndromes=matches,
        causal_narrative=narrative,
        assumptions=assumptions,
        needs_validation=needs_validation,
        is_mock=diagnostic.is_mock,
    )


def _risk_order(risk: str) -> int:
    return {"very_high": 4, "high": 3, "medium": 2, "low": 1}.get(risk, 0)


def _unknown_syndrome() -> SyndromeMatch:
    return SyndromeMatch(
        syndrome_id="unknown",
        name="Insufficient data for syndrome classification",
        risk_level="unknown",
        confidence="none",
        triggering_indicators=[],
        main_symptoms=[],
        likely_drivers=[],
        suggested_validation=["Collect baseline indicator data across all categories"],
        match_score=0.0,
    )


def _build_narrative(
    primary: SyndromeMatch,
    secondary: list[SyndromeMatch],
    diagnostic: DiagnosticResult,
) -> str:
    sev = diagnostic.degradation_severity.replace("_", " ")
    narrative = (
        f"The landscape shows {sev} overall degradation. "
        f"The primary syndrome identified is '{primary.name}' "
        f"(confidence: {primary.confidence}, match: {int(primary.match_score * 100)}%). "
    )
    if primary.likely_drivers:
        narrative += f"Key drivers include: {', '.join(primary.likely_drivers[:3])}. "
    if secondary:
        sec_names = ", ".join(m.name for m in secondary)
        narrative += f"Secondary syndromes detected: {sec_names}. "
    if diagnostic.data_gaps:
        narrative += (
            f"NOTE: {len(diagnostic.data_gaps)} indicator(s) had data gaps "
            f"({', '.join(diagnostic.data_gaps[:3])}); field verification recommended."
        )
    return narrative
