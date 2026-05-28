"""
AI Narrative Router — LIRA-AI
==============================
Hybrid approach:
  Paragraph 1: deterministically assembled from indicator values (zero hallucination)
  Paragraph 2: LLM interprets and gives Priority action (short, guided completion)

This works reliably with small models (tinyllama 1.1B) because:
  - The model only needs to write ~60 words of interpretation
  - All numbers are already stated in Paragraph 1 (model cannot invent new ones)
  - Task is simple completion, not complex reasoning
  - CGSpace/GARDIAN evidence injected where known
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Any
from app.services.llm_service import generate_narrative
from app.middleware.rate_limit import limiter, LIMITS

router = APIRouter(prefix="/ai", tags=["AI Narratives"])


# ── CGSpace evidence inserts ──────────────────────────────────────────────────
CGSPACE_REFS: dict[str, str] = {
    "erosion":      "Bewket & Teferi (2009, CGSpace) document 15–93 t/ha/yr soil loss on unprotected Ethiopian highland slopes.",
    "overgrazing":  "ILRI/CGIAR rangeland assessments confirm widespread carrying-capacity exceedance in South Omo pastoral zones.",
    "deforestation":"CIFOR and Ethiopian Forest Fund (CGSpace) record >40% forest cover loss in Kafa-Sheka since 1980.",
    "sedimentation":"IWMI/WLE studies link upstream catchment erosion to measurable storage loss in Ethiopian reservoirs.",
    "moisture":     "ICPAC/CHIRPS analyses show increasing dry-spell frequency across the Greater Horn of Africa since 2000.",
    "carbon":       "ISRIC SoilGrids v2.0 provides the baseline SOC values; field validation is recommended per CGIAR ISFM protocols.",
}

_SYNDROME_TO_CGSPACE = {
    "erosion_productivity_decline":  "erosion",
    "rangeland_overgrazing":         "overgrazing",
    "deforestation_vegetation_loss": "deforestation",
    "reservoir_sedimentation":       "sedimentation",
    "moisture_stress":               "moisture",
    "soil_carbon_depletion":         "carbon",
}


def _cgref(syndrome_id: str) -> str:
    return CGSPACE_REFS.get(_SYNDROME_TO_CGSPACE.get(syndrome_id, ""), "")


# ── Helper: safe numeric formatting ──────────────────────────────────────────

def _v(ctx: dict, key: str, unit: str = "", precision: int = 2, na: str = "N/A") -> str:
    v = ctx.get(key)
    if v is None: return na
    try:    return f"{round(float(v), precision)}{unit}"
    except: return str(v)


# ── Paragraph 1: data-factual (deterministic) ─────────────────────────────────

def _para1(narrative_type: str, ctx: dict) -> str:
    """Assemble the factual paragraph from indicator values — no LLM needed."""

    t = narrative_type
    rs = ctx.get("risk_scores", {}) or {}

    if t == "syndrome":
        drivers  = ", ".join(str(d) for d in (ctx.get("drivers")  or [])[:3]) or "undetermined"
        symptoms = ", ".join(str(s) for s in (ctx.get("symptoms") or [])[:3]) or "undetermined"
        cgref    = _cgref(str(ctx.get("syndrome_id", "")))
        evidence = f" {cgref}" if cgref else ""
        return (
            f"The {ctx.get('zone_name', 'landscape')} presents {ctx.get('syndrome_name', 'degradation')} "
            f"at {ctx.get('degradation_severity', 'moderate')} severity "
            f"(Landscape Health Index: {_v(ctx,'lhii_score')}, class '{ctx.get('lhii_class','—')}'). "
            f"Primary drivers — {drivers} — produce symptoms including {symptoms}."
            f"{evidence}"
        )

    if t == "climate":
        return (
            f"Under {ctx.get('scenario','SSP2-4.5')} to {ctx.get('horizon','2050')}, "
            f"{ctx.get('zone_name','this landscape')} faces elevated climate stress. "
            f"Drought/dry-spell risk scores {rs.get('drought_dry_spell_risk','—')}/1.0, "
            f"erosion/runoff risk {rs.get('erosion_runoff_risk','—')}/1.0, "
            f"and heat stress risk {rs.get('heat_stress_risk','—')}/1.0 "
            f"(Source: NASA NEX GDDP CMIP6, Planetary Computer). "
            f"Restoration suitability stress stands at {rs.get('restoration_suitability_stress','—')}/1.0, "
            f"indicating a narrowing implementation window."
        )

    if t == "pathway":
        pkg = ", ".join(str(i) for i in (ctx.get("interventions") or [])[:4]) or "undetermined"
        return (
            f"The {str(ctx.get('pathway_type','—')).replace('_',' ')} pathway targets "
            f"{ctx.get('syndrome_name','landscape degradation')} through a package of: {pkg}. "
            f"Cost category: {ctx.get('cost_category','medium')}. "
            f"Selection rationale: {ctx.get('why_it_fits','context-matched intervention package')}."
        )

    if t == "tradeoffs":
        risks = ", ".join(str(r).replace('_',' ') for r in (ctx.get("cross_cutting_risks") or [])[:3]) or "none"
        return (
            f"Across seven pathway options, the {str(ctx.get('lowest_risk','low cost')).replace('_',' ')} pathway "
            f"carries the lowest aggregate risk, while the {str(ctx.get('highest_risk','—')).replace('_',' ')} pathway "
            f"carries the highest. Cross-cutting risks affecting all pathways include: {risks}."
        )

    if t == "investment":
        pkgs  = ", ".join(str(i) for i in (ctx.get("interventions") or [])[:4]) or "restoration package"
        hooks = ", ".join(str(p) for p in (ctx.get("policy_hooks")  or [])[:3]) or "national restoration priorities"
        return (
            f"The '{ctx.get('package_name','—')}' investment package targets "
            f"{ctx.get('target_geography','Omo-Ghibe basin')} "
            f"through {pkgs}. "
            f"Investment readiness score: {ctx.get('readiness_score','—')}; "
            f"climate robustness score: {ctx.get('climate_score','—')}. "
            f"Policy alignment confirmed with: {hooks}."
        )

    if t == "monitoring":
        alerts = ctx.get("alerts") or []
        alert_str = "; ".join(str(a.get("alert_type","")).replace("_"," ") for a in alerts[:2]) or "none triggered"
        repx = "re-prescription required" if ctx.get("re_prescription_needed") else "no re-prescription needed"
        return (
            f"NDVI monitoring over {ctx.get('monitoring_period','the assessment period')} shows "
            f"baseline {_v(ctx,'baseline_ndvi')} → current {_v(ctx,'current_ndvi')} "
            f"(change: {_v(ctx,'ndvi_change_pct','%')}), trajectory: {ctx.get('recovery_trajectory','—')}. "
            f"Active alerts: {alert_str}. Assessment: {repx} "
            f"(Source: Sentinel-2 L2A, Planetary Computer)."
        )

    if t == "lhii":
        hot = ctx.get("hotspots",  []) or []
        grn = ctx.get("green_spots",[]) or []
        return (
            f"{ctx.get('zone_name','This landscape')} scores {_v(ctx,'lhii_score')} on the "
            f"Landscape Health Intelligence Index (class: '{ctx.get('lhii_class','—')}'). "
            f"Dominant constraint: {ctx.get('dominant_constraint','—')}; "
            f"recovery potential: {ctx.get('recovery_potential','—')}. "
            + (f"Hotspot: {hot[0]}. " if hot else "")
            + (f"Green spot: {grn[0]}." if grn else "No green spots identified.")
        )

    if t == "agronomy":
        crops = ", ".join(str(c) for c in (ctx.get("suitable_crops") or [])[:3]) or "general cereals"
        isfm  = "; ".join(str(r) for r in (ctx.get("isfm_recs") or [])[:2]) or "compost application, legume intercropping"
        return (
            f"Soil fertility in {ctx.get('zone_name','this zone')} is '{ctx.get('fertility_status','—')}' "
            f"with an estimated yield gap of {_v(ctx,'yield_gap_pct','%')}. "
            f"Most suitable crops: {crops}. "
            f"Priority ISFM interventions: {isfm} "
            f"(Reference: CGIAR Excellence in Agronomy; Vanlauwe et al. ISFM for Sub-Saharan Africa)."
        )

    if t == "advisory":
        prio  = "; ".join(str(p) for p in (ctx.get("priorities")  or [])[:2]) or "restoration and food security"
        const = "; ".join(str(c) for c in (ctx.get("constraints") or [])[:2]) or "labour and tenure constraints"
        return (
            f"For {ctx.get('audience','planners')}: {ctx.get('zone_name','the landscape')} shows "
            f"{ctx.get('syndrome_name','degradation')} at {ctx.get('degradation_severity','moderate')} severity. "
            f"Community priorities include {prio}; key constraints are {const}."
        )

    if t == "comparison":
        zones = ctx.get("zones") or []
        zone_lines = "; ".join(
            f"{z.get('zone_name','?')} (LHII {z.get('lhii_score','?')}, "
            f"erosion {z.get('soil_loss_t_ha_yr','?')} t/ha/yr, "
            f"{str(z.get('syndrome_name','?'))[:25]})"
            for z in zones[:4]
        )
        return f"Across {ctx.get('basin_name','the basin')}: {zone_lines}."

    return f"Analysis context: {str(ctx)[:200]}."


# ── Paragraph 2 prompt: model completes the interpretation ───────────────────

def _para2_prompt(narrative_type: str, ctx: dict, para1: str) -> str:
    """
    Short guided prompt for Paragraph 2.
    The model has already seen the facts in para1; it only needs to interpret.
    """
    audience = {
        "syndrome":    "CGIAR landscape restoration scientists",
        "climate":     "climate adaptation planners",
        "pathway":     "field restoration practitioners",
        "tradeoffs":   "investment decision-makers",
        "investment":  "GCF/development finance officers",
        "monitoring":  "adaptive management teams",
        "lhii":        "landscape restoration planners",
        "agronomy":    "extension workers and farmers",
        "advisory":    "community facilitators",
        "comparison":  "CGIAR MFL program managers",
    }.get(narrative_type, "restoration planners")

    return (
        f"{para1}\n\n"
        f"Write one paragraph for {audience} interpreting the above. "
        f"State the key implication for restoration planning, then end with exactly: "
        f"'Priority action: [one specific, measurable action].' "
        f"Use only the facts above. Max 70 words."
    )


# ── Main endpoint ─────────────────────────────────────────────────────────────

class NarrateRequest(BaseModel):
    narrative_type: str
    context:        dict[str, Any]
    hf_token:       str = ""
    groq_key:       str = ""
    max_wait:       int = 45


def _extract_priority_action(llm_text: str) -> str:
    """
    Extract the 'Priority action:' sentence from LLM output.
    Handles variations in capitalisation and punctuation.
    Returns empty string if not found.
    """
    import re
    if not llm_text:
        return ""
    # Find "Priority action: ..." pattern (case-insensitive)
    match = re.search(
        r"[Pp]riority\s+[Aa]ction\s*:\s*(.+?)(?:\.|$)",
        llm_text,
        re.DOTALL
    )
    if match:
        action = match.group(1).strip()
        # Clean up — remove bullet chars, newlines, truncation
        action = re.sub(r"[\n\r\-\*•]+", " ", action).strip()
        action = action[:200]  # hard cap
        if len(action) > 15:
            return f"Priority action: {action}."
    return ""


# ── Default priority actions per narrative type ───────────────────────────────
_DEFAULT_ACTIONS: dict[str, str] = {
    "syndrome":   "Implement targeted soil-water conservation works on the highest-severity hotspot areas identified by the LHII.",
    "climate":    "Conduct climate stress testing on all proposed restoration options before investment commitments.",
    "pathway":    "Begin community co-design workshops to validate feasibility and secure tenure agreements.",
    "tradeoffs":  "Adopt the lowest-risk pathway and establish a community monitoring protocol for the top three risk dimensions.",
    "investment": "Initiate a field feasibility assessment and community validation process as prerequisites to funding mobilisation.",
    "monitoring": "Review intervention implementation and field conditions with the adaptive management team to determine re-prescription needs.",
    "lhii":       "Focus immediate restoration investment on the identified hotspot areas while protecting green spots as reference sites.",
    "agronomy":   "Scale up ISFM practices through existing extension networks, prioritising micro-dose fertiliser and legume intercropping.",
    "advisory":   "Convene a community validation workshop to confirm priorities and agree on seasonal implementation calendar.",
    "comparison": "Prioritise investment in the zone with lowest LHII and highest erosion rate for maximum landscape-level impact.",
}


@router.post("/narrate")
@limiter.limit(LIMITS["ai"])
async def narrate(request: Request, req: NarrateRequest) -> dict:
    """
    Hybrid AI summary:
      Para1  — deterministic (100% data-grounded, no hallucination)
      Ending — LLM-generated 'Priority action:' sentence, or template fallback

    Uses async AsyncLLMService (singleton on app.state.llm_service) when
    available; falls back to the sync generate_narrative() for safety.
    """
    para1  = _para1(req.narrative_type, req.context)
    prompt = _para2_prompt(req.narrative_type, req.context, para1)

    # Prefer async singleton; fall back to sync if not initialised
    llm = getattr(request.app.state, "llm_service", None) if hasattr(request, "app") else None
    if llm is not None:
        result = await llm.generate(
            prompt, hf_token=req.hf_token, groq_key=req.groq_key, max_wait=req.max_wait,
        )
    else:
        # Sync fallback (still works for any caller that doesn't pass request)
        result = generate_narrative(
            prompt=prompt, hf_token=req.hf_token,
            groq_key=req.groq_key, max_wait=req.max_wait,
        )

    # Track Prometheus metrics
    try:
        from app.observability.metrics import llm_calls_total, llm_latency_seconds
        provider = result.get("provider", "unknown")
        llm_calls_total.labels(provider=provider, is_llm=str(result.get("is_llm", False))).inc()
        llm_latency_seconds.labels(provider=provider).observe(result.get("latency_s", 0))
    except Exception:
        pass

    # Extract only the Priority action sentence — ignore the rest
    llm_action = _extract_priority_action(result.get("text") or "")
    fallback_action = _DEFAULT_ACTIONS.get(
        req.narrative_type,
        "Priority action: Validate findings with field teams and initiate restoration planning."
    )
    priority_sentence = llm_action or f"Priority action: {fallback_action}"

    # Full text: clean factual paragraph + priority sentence
    full_text = f"{para1}\n\n{priority_sentence}"

    return {
        "narrative_type": req.narrative_type,
        "text":           full_text,
        "provider":       result.get("provider", "template"),
        "model":          result.get("model"),
        "is_llm":         bool(llm_action),   # True only if LLM produced a valid Priority action
        "latency_s":      result.get("latency_s", 0),
    }


@router.get("/status")
def ai_status() -> dict:
    import urllib.request as _ur, json as _j
    status: dict = {}
    try:
        with _ur.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            models = [m["name"] for m in _j.loads(r.read()).get("models", [])]
            status["ollama"] = {"available": True, "models": models}
    except Exception:
        status["ollama"] = {"available": False, "models": []}
    try:
        with _ur.urlopen("https://huggingface.co", timeout=5) as r:
            status["huggingface"] = {"available": r.status == 200}
    except Exception:
        status["huggingface"] = {"available": False}

    primary = ("ollama" if status["ollama"]["available"] and status["ollama"]["models"]
               else "huggingface" if status["huggingface"]["available"] else "template")
    return {
        "providers": status, "active_provider": primary,
        "ollama_models": status["ollama"].get("models", []),
        "ready": primary != "template",
    }
