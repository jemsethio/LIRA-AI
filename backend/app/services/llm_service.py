"""
LIRA-AI LLM Service — Open-Source First
========================================
Provider priority (all free / open-source):
  1. Ollama   — local inference, zero cost, full privacy
               Models: llama3.2:3b, mistral:7b, qwen2.5:7b
               https://ollama.com

  2. Hugging Face Inference API — free tier
               Models: Mistral-7B-Instruct, Llama-3.2-3B-Instruct
               https://huggingface.co/inference-api
               Set HF_TOKEN in .env (free at huggingface.co/settings/tokens)

  3. Groq API — free tier (6000 tokens/min on open models)
               Models: llama-3.3-70b-versatile, mixtral-8x7b-32768
               https://console.groq.com (free account)
               Set GROQ_API_KEY in .env

  4. Template fallback — always works, no dependencies

Quantitative values are NEVER delegated to the LLM.
The LLM only adds explanatory narrative to pre-computed scientific results.
"""

from __future__ import annotations
import json
import time
import urllib.request
import urllib.error
from typing import Optional
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODELS = ["tinyllama", "llama3.2:1b", "llama3.2:3b", "mistral:7b", "qwen2.5:3b"]

HF_API_URL   = "https://api-inference.huggingface.co/models"
HF_MODELS    = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "meta-llama/Llama-3.2-3B-Instruct",
    "HuggingFaceH4/zephyr-7b-beta",
]

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS  = ["llama-3.3-70b-versatile", "llama3-8b-8192", "mixtral-8x7b-32768"]

# System prompt — tuned for small models (tinyllama, 1-3B)
# Keep short: small models echo long instructions
SYSTEM_PROMPT = (
    "You are a CGIAR landscape scientist. "
    "Write exactly 2 short paragraphs using only the numbers and facts provided. "
    "End with: Priority action: [one specific action]."
)


# ─── Provider implementations ─────────────────────────────────────────────────

def _call_ollama(prompt: str, model: str = "llama3.2:3b", timeout: int = 45) -> str | None:
    """Call local Ollama inference server."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.25, "num_predict": 200, "stop": ["\n\n\n"]},
    }).encode()
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
            return resp.get("response", "").strip() or None
    except Exception:
        return None


def _get_ollama_model() -> str | None:
    """Return first available Ollama model, or None."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            tags = json.loads(r.read())
            available = {m["name"].split(":")[0] for m in tags.get("models", [])}
            for m in OLLAMA_MODELS:
                if m.split(":")[0] in available:
                    return m
    except Exception:
        pass
    return None


def _call_huggingface(prompt: str, hf_token: str = "", timeout: int = 30) -> str | None:
    """Call HuggingFace Inference API (free tier). No token needed for public models."""
    # Format as instruction
    formatted = f"<s>[INST] {SYSTEM_PROMPT}\n\n{prompt} [/INST]"
    payload    = json.dumps({
        "inputs": formatted,
        "parameters": {"max_new_tokens": 400, "temperature": 0.3, "do_sample": True},
    }).encode()

    headers = {"Content-Type": "application/json", "User-Agent": "LIRA-AI/0.1"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    for model in HF_MODELS:
        try:
            req = urllib.request.Request(
                f"{HF_API_URL}/{model}",
                data=payload, headers=headers, method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read())
                if isinstance(resp, list) and resp:
                    text = resp[0].get("generated_text", "")
                    # Strip the input from the output
                    if "[/INST]" in text:
                        text = text.split("[/INST]")[-1].strip()
                    if text and len(text) > 50:
                        return text
        except Exception:
            continue
    return None


def _call_groq(prompt: str, groq_key: str, timeout: int = 20) -> str | None:
    """Call Groq API (free tier, open-source models, very fast)."""
    payload = json.dumps({
        "model": GROQ_MODELS[0],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.3,
    }).encode()
    try:
        req = urllib.request.Request(
            GROQ_API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {groq_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
            return resp["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_narrative(
    prompt: str,
    hf_token:  str = "",
    groq_key:  str = "",
    max_wait:  int = 40,
) -> dict:
    """
    Generate a scientific narrative using the best available open-source LLM.
    Returns: {text, provider, model, is_llm, latency_s}
    Falls back gracefully through all providers.
    """
    t0 = time.time()

    # 1. Try Ollama (local, zero cost)
    model = _get_ollama_model()
    if model:
        text = _call_ollama(prompt, model=model, timeout=max_wait)
        if text:
            return {"text": text, "provider": "ollama", "model": model,
                    "is_llm": True, "latency_s": round(time.time()-t0, 2)}

    # 2. Try Groq (free tier, fastest)
    if groq_key:
        text = _call_groq(prompt, groq_key=groq_key, timeout=15)
        if text:
            return {"text": text, "provider": "groq", "model": GROQ_MODELS[0],
                    "is_llm": True, "latency_s": round(time.time()-t0, 2)}

    # 3. Try HuggingFace (free, no key needed for public models)
    text = _call_huggingface(prompt, hf_token=hf_token, timeout=30)
    if text:
        return {"text": text, "provider": "huggingface", "model": HF_MODELS[0],
                "is_llm": True, "latency_s": round(time.time()-t0, 2)}

    # 4. Template fallback
    return {"text": None, "provider": "template", "model": None,
            "is_llm": False, "latency_s": round(time.time()-t0, 2)}


# ─── Domain-specific narrative generators ─────────────────────────────────────

def narrate_syndrome(
    syndrome_name: str,
    drivers: list[str],
    symptoms: list[str],
    degradation_severity: str,
    lhii_score: float,
    zone_name: str,
    **llm_kwargs,
) -> dict:
    prompt = f"""
Landscape zone: {zone_name}
Degradation severity: {degradation_severity}
Landscape Health Index (LHII): {lhii_score:.2f} / 1.0
Primary degradation syndrome: {syndrome_name}
Key drivers: {', '.join(drivers[:4])}
Main symptoms: {', '.join(symptoms[:4])}

Write a concise causal narrative (2–3 paragraphs) explaining:
1. How these drivers interact to produce the observed syndrome
2. Why this trajectory is concerning for livelihoods and ecosystem services
3. What the LHII score tells us about urgency of intervention
Ground the narrative in the evidence provided. Do not invent numbers.
"""
    return generate_narrative(prompt, **llm_kwargs)


def narrate_climate_risk(
    zone_name: str,
    scenario: str,
    horizon: str,
    risk_scores: dict,
    indicators: dict,
    **llm_kwargs,
) -> dict:
    prompt = f"""
Landscape zone: {zone_name}
Climate scenario: {scenario} to {horizon}
Risk scores (0=low, 1=high):
  Rainfall intensity risk: {risk_scores.get('rainfall_intensity_risk', 'N/A')}
  Drought/dry-spell risk:  {risk_scores.get('drought_dry_spell_risk', 'N/A')}
  Heat stress risk:        {risk_scores.get('heat_stress_risk', 'N/A')}
  Erosion/runoff risk:     {risk_scores.get('erosion_runoff_risk', 'N/A')}
  Restoration suitability stress: {risk_scores.get('restoration_suitability_stress', 'N/A')}
Current indicators: {json.dumps({k:v for k,v in indicators.items() if v is not None and k in ['rainfall_mm_annual','temperature_mean_c','ndvi_mean']}, indent=2)}

Write a concise climate risk narrative (2–3 paragraphs) explaining:
1. Which climate risks are most critical for this landscape
2. How projected changes will affect restoration success and livelihoods
3. Which interventions need to be climate-stress-tested
Be specific to this landscape context. Do not invent numbers beyond those provided.
"""
    return generate_narrative(prompt, **llm_kwargs)


def narrate_investment_passport(
    package_name: str,
    target_geography: str,
    problem_diagnosis: str,
    interventions: list[str],
    readiness_score: float,
    **llm_kwargs,
) -> dict:
    prompt = f"""
Investment Package: {package_name}
Target geography: {target_geography}
Diagnosis: {problem_diagnosis}
Intervention components: {', '.join(interventions)}
Investment readiness score: {readiness_score:.0%}

Write a concise investment narrative (2–3 paragraphs) for a finance audience:
1. Why this landscape needs investment now (urgency and opportunity)
2. What the proposed package will achieve (ecological and livelihood benefits)
3. What makes this investment climate-resilient and community-grounded
Use language suitable for Green Climate Fund or development finance audiences.
Do not invent cost figures.
"""
    return generate_narrative(prompt, **llm_kwargs)


def narrate_pathway(
    pathway_type: str,
    syndrome_name: str,
    options: list[str],
    why_it_fits: str,
    tradeoffs: list[str],
    **llm_kwargs,
) -> dict:
    prompt = f"""
Restoration pathway: {pathway_type.replace('_', ' ')}
Degradation syndrome: {syndrome_name}
Proposed interventions: {', '.join(options)}
Why it fits: {why_it_fits}
Key tradeoffs: {', '.join(tradeoffs[:3])}

Write a concise pathway rationale (1–2 paragraphs) explaining:
1. Why this specific combination of interventions addresses the syndrome
2. What enabling conditions are needed for success
3. How to sequence implementation for maximum early impact
Be practical and grounded in East African restoration experience.
"""
    return generate_narrative(prompt, **llm_kwargs)
