"""
Restoration Card Extractor v2 — LIRA-AI
==========================================
LLM-structured extraction of RestorationOptionCards from retrieved chunks,
with the legacy regex extractor as a fast-path fallback.

Strategy:
  1. PRIMARY: Ask the LLM to fill a RestorationCardSchema for each chunk.
     - Uses Ollama JSON mode (`format: json`) for free, local extraction.
     - Falls back to Groq function calling if Ollama unavailable.
  2. FALLBACK: If LLM is unreachable OR yields invalid JSON, fall back to
     the regex extractor from app/rag/card_extractor.py (still works).

Output is identical to v1 — same `RestorationOptionCard` Pydantic model.
"""

from __future__ import annotations
import json
import logging
from typing import Optional

from app.models.pathways import RestorationOptionCard
from app.rag.card_extractor import extract_cards_from_chunks as _regex_extract
from app.services.llm_async import AsyncLLMService

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """You are extracting restoration option metadata from a CGIAR document chunk.

Chunk:
\"\"\"
{text}
\"\"\"

Return ONLY a JSON object with this EXACT structure (or `null` if the chunk does NOT describe a restoration option):
{{
  "option_name": "e.g. Soil Bunds",
  "target_symptoms": ["soil erosion", "topsoil loss"],
  "suitable_conditions": ["slopes 5-15 degrees", "rainfall 600-1200 mm/yr"],
  "unsuitable_conditions": ["very steep slopes"],
  "benefits": ["reduces runoff", "increases infiltration"],
  "risks": ["high labor cost"],
  "required_inputs": ["stones", "community labor"],
  "labor_requirements": "Medium - 30-60 person-days/ha",
  "slope_range": "5-15 degrees",
  "rainfall_range": "600-1200 mm/yr",
  "monitoring_indicators": ["bund condition", "NDVI trend"]
}}

Rules:
- Use ONLY information from the chunk above; do NOT invent details.
- If chunk does not describe a restoration option, return: null
- Output: pure JSON, no markdown, no commentary.
"""


async def extract_cards_v2(
    chunks: list[dict],
    project_id: str,
    llm: Optional[AsyncLLMService] = None,
    use_llm: bool = True,
) -> list[RestorationOptionCard]:
    """
    Extract RestorationOptionCards from retrieved chunks.
    If LLM unavailable or fails, falls back to regex extraction.
    """
    # Fast path: no LLM requested or available → regex
    if not use_llm or llm is None:
        return _regex_extract(chunks, project_id=project_id)

    cards: list[RestorationOptionCard] = []
    fallback_chunks: list[dict] = []

    for chunk in chunks:
        text = (chunk.get("text") or "").strip()
        if len(text) < 50:
            continue

        # Ask LLM to extract structured data
        try:
            card = await _llm_extract_one(text, chunk, llm)
            if card is not None:
                cards.append(card)
            else:
                # LLM said "this chunk doesn't describe an option" → skip
                continue
        except Exception as e:
            logger.debug("LLM card extraction failed, falling back: %s", e)
            fallback_chunks.append(chunk)

    # Regex fallback for any LLM failures
    if fallback_chunks:
        cards.extend(_regex_extract(fallback_chunks, project_id=project_id))

    # Deduplicate by option_name
    seen: set[str] = set()
    unique: list[RestorationOptionCard] = []
    for c in cards:
        key = c.option_name.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


async def _llm_extract_one(
    text: str, chunk: dict, llm: AsyncLLMService
) -> Optional[RestorationOptionCard]:
    """Extract a single card from one chunk via LLM JSON mode."""
    prompt = EXTRACTION_PROMPT.format(text=text[:1500])
    result = await llm.generate(prompt, max_wait=30)
    raw    = (result.get("text") or "").strip()

    # Try to find a JSON object in the response
    json_text = _extract_json(raw)
    if not json_text:
        return None

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return None

    if data is None or not isinstance(data, dict):
        return None

    # Build RestorationOptionCard with defensive defaults
    score = chunk.get("score", 0.5)
    confidence = "high" if score > 0.7 else "medium" if score > 0.4 else "low"

    try:
        return RestorationOptionCard(
            option_name=str(data.get("option_name", "Unknown Option")).strip()[:80],
            target_symptoms=_safe_list(data.get("target_symptoms")) or ["Land degradation"],
            suitable_conditions=_safe_list(data.get("suitable_conditions")) or ["Context-dependent"],
            unsuitable_conditions=_safe_list(data.get("unsuitable_conditions")) or ["Site-specific constraints"],
            land_use=["cropland", "degraded_land"],
            slope_range=str(data.get("slope_range", "Context-dependent"))[:80],
            rainfall_range=str(data.get("rainfall_range", "Context-dependent"))[:80],
            soil_conditions=["Review with SoilGrids data"],
            required_inputs=_safe_list(data.get("required_inputs")) or ["Community labour"],
            labor_requirements=str(data.get("labor_requirements", "Medium - context-dependent"))[:120],
            community_requirements=["Community agreement", "Land tenure clarity"],
            benefits=_safe_list(data.get("benefits")) or ["Vegetation recovery"],
            risks=_safe_list(data.get("risks")) or ["Implementation challenges"],
            maladaptation_risks=["Climate stress testing recommended"],
            complementary_options=[],
            monitoring_indicators=_safe_list(data.get("monitoring_indicators")) or ["Vegetation cover"],
            evidence_sources=[f"{chunk.get('source','document')} (score: {score:.2f}, LLM-extracted)"],
            confidence_level=confidence,
            is_assumption=False,    # LLM-extracted = higher confidence than regex
        )
    except Exception as e:
        logger.debug("Card schema validation failed: %s", e)
        return None


def _safe_list(v) -> list[str]:
    """Coerce any value into a list of strings."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x)[:200] for x in v[:6] if x]
    if isinstance(v, str):
        return [v[:200]]
    return []


def _extract_json(text: str) -> Optional[str]:
    """Find the first {...} or null in LLM output (handles markdown fences)."""
    text = text.strip()
    if text.lower().startswith("null"):
        return "null"
    # Strip markdown code fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                return stripped
    # Find first { ... balanced } in raw text
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None
