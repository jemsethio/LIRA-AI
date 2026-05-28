"""
Restoration Option Card Extractor — LIRA-AI RAG
=================================================
Extracts structured RestorationOptionCards from retrieved document chunks.
Uses keyword/pattern matching + LLM enhancement (optional).

Card schema (from concept note):
  option_name, target_symptoms, suitable_conditions, unsuitable_conditions,
  land_use, slope_range, rainfall_range, soil_conditions, required_inputs,
  labor_requirements, community_requirements, benefits, risks,
  maladaptation_risks, complementary_options, monitoring_indicators,
  evidence_sources, confidence_level
"""

from __future__ import annotations
import re
from typing import Optional
from app.models.pathways import RestorationOptionCard


# ── Keyword patterns for each card field ─────────────────────────────────────

FIELD_PATTERNS: dict[str, list[str]] = {
    "target_symptoms": [
        r"target(?:s|ing)?\s*:?\s*(.+?)(?:\n|\.)",
        r"addresses?\s*:?\s*(.+?)(?:\n|\.)",
        r"problem(?:s)?\s*:?\s*(.+?)(?:\n|\.)",
    ],
    "suitable_conditions": [
        r"suitable\s+(?:for|when|where)\s*:?\s*(.+?)(?:\n|\.)",
        r"applicable\s*:?\s*(.+?)(?:\n|\.)",
        r"best\s+(?:for|in)\s*:?\s*(.+?)(?:\n|\.)",
    ],
    "unsuitable_conditions": [
        r"not\s+suitable\s*:?\s*(.+?)(?:\n|\.)",
        r"avoid\s*:?\s*(.+?)(?:\n|\.)",
        r"unsuitable\s*:?\s*(.+?)(?:\n|\.)",
    ],
    "benefits": [
        r"benefit(?:s)?\s*:?\s*(.+?)(?:\n|\.)",
        r"advantages?\s*:?\s*(.+?)(?:\n|\.)",
        r"outcome(?:s)?\s*:?\s*(.+?)(?:\n|\.)",
        r"improve(?:s)?\s+(.+?)(?:\n|\.)",
    ],
    "risks": [
        r"risk(?:s)?\s*:?\s*(.+?)(?:\n|\.)",
        r"limitation(?:s)?\s*:?\s*(.+?)(?:\n|\.)",
        r"challenge(?:s)?\s*:?\s*(.+?)(?:\n|\.)",
    ],
    "required_inputs": [
        r"input(?:s)?\s+required\s*:?\s*(.+?)(?:\n|\.)",
        r"material(?:s)?\s+needed\s*:?\s*(.+?)(?:\n|\.)",
        r"require(?:s)?\s*:?\s*(.+?)(?:\n|\.)",
    ],
    "labor_requirements": [
        r"labor(?:ur)?\s*:?\s*(.+?)(?:\n|\.)",
        r"person.days?\s*:?\s*(.+?)(?:\n|\.)",
        r"workload\s*:?\s*(.+?)(?:\n|\.)",
    ],
    "monitoring_indicators": [
        r"monitor(?:ing)?\s*:?\s*(.+?)(?:\n|\.)",
        r"indicator(?:s)?\s*:?\s*(.+?)(?:\n|\.)",
        r"measure(?:d|s)?\s+by\s*:?\s*(.+?)(?:\n|\.)",
    ],
}

# ── Known restoration options (pre-populated library) ────────────────────────

KNOWN_OPTIONS: list[str] = [
    "soil bund", "stone bund", "terrace", "contour bund",
    "area closure", "exclosure", "enclosure",
    "agroforestry", "FMNR", "farmer-managed natural regeneration",
    "water harvesting", "half-moon", "tied ridges", "percolation pit",
    "check dam", "gully rehabilitation", "gully plug",
    "rotational grazing", "fodder bank", "cut-and-carry",
    "compost", "organic matter", "green manure",
    "reforestation", "afforestation", "planting",
    "mulching", "residue management", "conservation tillage",
    "riparian buffer", "riverine restoration",
    "Prosopis control", "invasive species removal",
]


def _extract_field(text: str, field: str) -> list[str]:
    """Extract a field value from text using regex patterns."""
    results: list[str] = []
    for pattern in FIELD_PATTERNS.get(field, []):
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip().rstrip(".,;")
            if len(cleaned) > 5:
                results.append(cleaned[:200])
    return list(dict.fromkeys(results))[:4]   # deduplicate, max 4


def _extract_numeric(text: str, pattern: str, unit: str = "") -> Optional[str]:
    """Extract a numeric range from text."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return m.group(0).strip() + (f" {unit}" if unit else "")
    return None


def _detect_option_name(text: str) -> Optional[str]:
    """Detect which known restoration option this chunk describes."""
    text_lower = text.lower()
    for option in KNOWN_OPTIONS:
        if option.lower() in text_lower:
            return option.title()
    return None


def extract_cards_from_chunks(
    chunks: list[dict],
    project_id: str,
    source_label: str = "document",
) -> list[RestorationOptionCard]:
    """
    Extract RestoractionOptionCards from retrieved document chunks.
    Each chunk dict has: {text, source, score}
    """
    cards: list[RestorationOptionCard] = []
    seen_names: set[str] = set()

    for chunk in chunks:
        text = chunk.get("text", "")
        source = chunk.get("source", source_label)

        # Only process chunks that describe restoration options
        option_name = _detect_option_name(text)
        if not option_name:
            continue
        if option_name in seen_names:
            continue
        seen_names.add(option_name)

        # Extract structured fields
        target_symptoms = _extract_field(text, "target_symptoms") or [
            "Soil erosion", "Vegetation loss", "Productivity decline"
        ]
        suitable_cond   = _extract_field(text, "suitable_conditions") or ["Context-dependent — field validation required"]
        unsuitable_cond = _extract_field(text, "unsuitable_conditions") or ["Site-specific constraints"]
        benefits        = _extract_field(text, "benefits") or ["Vegetation recovery", "Erosion reduction"]
        risks           = _extract_field(text, "risks") or ["Implementation and maintenance required"]
        inputs          = _extract_field(text, "required_inputs") or ["Community labour", "Local materials"]
        labor           = _extract_field(text, "labor_requirements")
        monitoring      = _extract_field(text, "monitoring_indicators") or [
            "Vegetation cover %", "Rill density", "Yield trend"
        ]

        # Slope and rainfall — look for numeric ranges
        slope_range   = (_extract_numeric(text, r"\d+[\–\-]\d+\s*°") or
                         _extract_numeric(text, r"\d+\s*to\s*\d+\s*degree", "degrees") or
                         "Context-dependent")
        rainfall_range = (_extract_numeric(text, r"\d{3,4}\s*[\–\-]\s*\d{3,4}\s*mm") or
                          "Context-dependent")

        # Confidence based on score
        score = chunk.get("score", 0.5)
        confidence = "high" if score > 0.7 else "medium" if score > 0.4 else "low"

        card = RestorationOptionCard(
            option_name=option_name,
            target_symptoms=target_symptoms,
            suitable_conditions=suitable_cond,
            unsuitable_conditions=unsuitable_cond,
            land_use=["cropland", "degraded_land"],    # default — refine with NLP
            slope_range=slope_range,
            rainfall_range=rainfall_range,
            soil_conditions=["Context-dependent — review with SoilGrids data"],
            required_inputs=inputs,
            labor_requirements="; ".join(labor) if labor else "Medium — 15–60 person-days/ha",
            community_requirements=["Community agreement", "Land tenure clarity"],
            benefits=benefits,
            risks=risks,
            maladaptation_risks=["Intervention may need climate stress testing"],
            complementary_options=[],
            monitoring_indicators=monitoring,
            evidence_sources=[f"{source} (retrieved score: {score:.2f})"],
            confidence_level=confidence,
            is_assumption=True,
        )
        cards.append(card)

    return cards
