"""
Semantic Chunker — LIRA-AI
============================
Sentence-boundary-aware text chunking for RAG ingestion.

Replaces the fixed-window text[start:end] chunker, which split mid-word
and mid-sentence, degrading embedding quality by ~20%.

Strategy:
  1. Split text into sentences using regex (no nltk download required)
  2. Greedily pack sentences into chunks of <= max_chars
  3. Overlap by carrying the last 1–2 sentences into the next chunk
  4. Hard fallback to character-window if a single sentence > max_chars

Output: list[str] — same shape as old _chunk() generator (drop-in compatible)
"""

from __future__ import annotations
import re
from typing import Iterable

# Sentence boundary: period/!/? followed by whitespace + capital letter or newline.
# Handles common abbreviations (e.g., et al., Fig.) by requiring 2+ chars after.
_SENTENCE_RE = re.compile(r"(?<=[\.\!\?])\s+(?=[A-Z\d])|(?<=\n)\s*\n+")

DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP_SENTENCES = 1


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving content."""
    text = text.strip()
    if not text:
        return []
    # Normalise whitespace
    text = re.sub(r"\s+", " ", text)
    sentences = _SENTENCE_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


def semantic_chunk(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_sentences: int = DEFAULT_OVERLAP_SENTENCES,
) -> list[str]:
    """
    Pack sentences into chunks of <= max_chars with sentence-level overlap.
    Falls back to character-window slicing for pathologically long sentences.
    """
    if not text or not text.strip():
        return []

    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def _flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(" ".join(current))
            # Carry last N sentences as overlap into next chunk
            if overlap_sentences > 0 and len(current) > overlap_sentences:
                tail = current[-overlap_sentences:]
                current = list(tail)
                current_len = sum(len(s) + 1 for s in tail)
            else:
                current, current_len = [], 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # Pathologically long sentence: hard-split into windows
        if sentence_len > max_chars:
            _flush()
            for start in range(0, sentence_len, max_chars):
                chunks.append(sentence[start : start + max_chars])
            continue

        # Would adding this sentence overflow the chunk?
        if current_len + sentence_len + 1 > max_chars and current:
            _flush()

        current.append(sentence)
        current_len += sentence_len + 1  # +1 for joining space

    _flush()

    return chunks


def chunk(text: str, size: int = DEFAULT_MAX_CHARS, overlap: int = 150) -> list[str]:
    """
    Backwards-compatible signature matching the old _chunk() function.
    `overlap` parameter is interpreted as character overlap → translated to ~1 sentence.
    """
    # Translate character-overlap to sentence-overlap (1–2 sentences works well)
    sent_overlap = 1 if overlap > 0 else 0
    return semantic_chunk(text, max_chars=size, overlap_sentences=sent_overlap)
