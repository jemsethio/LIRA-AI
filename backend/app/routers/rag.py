"""
RAG Router — LIRA-AI
======================
Exposes the full RAG pipeline via API:
  POST /rag/ingest          — upload + chunk + embed a document
  POST /rag/retrieve        — semantic search across project documents
  GET  /rag/cards/{project} — extracted restoration option cards
  POST /rag/ingest-cgspace  — ingest CGIAR CGSpace evidence cards automatically
  GET  /rag/status          — ChromaDB collection stats
"""

import os, re, json, tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

from app.middleware.rate_limit import limiter, LIMITS
from app.observability.metrics import rag_retrievals_total, vector_store_documents

router = APIRouter(prefix="/rag", tags=["RAG Knowledge Base"])


# ── Helpers — singleton accessors via request.app.state ──────────────────────

SAFE_NAME_RE  = re.compile(r"[^a-zA-Z0-9_\-]")
ALLOWED_EXTS  = {".pdf", ".docx", ".doc", ".txt", ".md"}
MAX_UPLOAD_MB = 25


def _safe(name: str, max_len: int = 80) -> str:
    """Strip path traversal / shell metachars from any user-controlled string."""
    return SAFE_NAME_RE.sub("_", str(name))[:max_len] or "unlabeled"


def _vector_store(request: Request):
    vs = getattr(request.app.state, "vector_store", None)
    if vs is None:
        raise HTTPException(503, "VectorStoreService not available — install chromadb + sentence-transformers")
    return vs


def _llm_service(request: Request):
    return getattr(request.app.state, "llm_service", None)


# Legacy fallback if anything still imports from app.rag.ingestion directly
def _legacy_rag():
    try:
        from app.rag.ingestion import ingest_document, retrieve
        return ingest_document, retrieve
    except Exception as e:
        raise HTTPException(503, f"RAG not available: {e}")


# ── Ingest a document file ────────────────────────────────────────────────────

@router.post("/ingest", summary="Upload and index a document")
@limiter.limit(LIMITS["rag"])
async def ingest_document_route(
    request:      Request,
    project_id:   str        = Form(...),
    source_label: str        = Form("uploaded_document"),
    file:         UploadFile = File(...),
) -> dict:
    """
    Upload a PDF, DOCX, TXT, or MD file (max 25 MB).
    Sanitises project_id/source_label, validates extension, uses secure tempfile.
    """
    vs = _vector_store(request)

    # Validate filename and extension
    filename = file.filename or "uploaded.txt"
    suffix   = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTS:
        raise HTTPException(415, f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTS)}")

    # Sanitise IDs
    project_id_safe   = _safe(project_id)
    source_label_safe = _safe(source_label)

    # Stream-read with size cap
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    content   = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, f"File too large ({len(content)//1024//1024} MB). Max: {MAX_UPLOAD_MB} MB")
    if len(content) == 0:
        raise HTTPException(400, "Empty file")

    # Secure tempfile (mkstemp prevents predictable paths / race conditions)
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix=f"lira_rag_{project_id_safe}_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        n_chunks = vs.ingest_document(
            Path(tmp_path),
            project_id=project_id_safe,
            source_label=source_label_safe,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(400, f"Ingest failed: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Update Prometheus gauge
    try:
        vector_store_documents.set(vs.collection_stats()["document_count"])
    except Exception:
        pass

    return {
        "project_id":   project_id_safe,
        "source_label": source_label_safe,
        "filename":     filename,
        "n_chunks":     n_chunks,
        "status":       "indexed",
        "message":      f"Successfully indexed {n_chunks} chunks into ChromaDB",
    }


# ── Ingest CGIAR CGSpace evidence automatically ───────────────────────────────

class CGSpaceIngestRequest(BaseModel):
    project_id: str
    query:      str = "Ethiopia Omo-Ghibe landscape restoration degradation"
    n_results:  int = 20
    # Run multiple targeted queries for comprehensive Ethiopia coverage
    multi_query: bool = True


# Pre-built Ethiopia-specific queries for comprehensive coverage
ETHIOPIA_QUERIES = [
    "Ethiopia landscape restoration soil erosion degradation",
    "Omo-Ghibe Ethiopia watershed management restoration",
    "Ethiopia rangeland pastoral overgrazing South Omo",
    "Ethiopia NDVI vegetation land cover change CGIAR",
    "Ethiopia agroforestry FMNR reforestation Kafa",
    "Ethiopia soil organic carbon SoilGrids land degradation",
    "Ethiopia climate change drought food security adaptation",
    "Ethiopia community watershed investment restoration",
]


@router.post("/ingest-cgspace", summary="Auto-ingest CGIAR CGSpace evidence")
@limiter.limit(LIMITS["rag"])
def ingest_cgspace(request: Request, req: CGSpaceIngestRequest) -> dict:
    """
    Search CGSpace and index ALL results — title, subjects, abstract, author.
    Many CGSpace items have no abstract; we use all available metadata.
    With multi_query=True runs 8 Ethiopia-specific queries automatically.
    """
    from app.data_adapters.gardian_adapter import _cgspace_search

    vs = _vector_store(request)
    project_id_safe = _safe(req.project_id)

    queries = ETHIOPIA_QUERIES if req.multi_query else [req.query]
    indexed   = 0
    skipped   = 0
    seen_ids: set[str] = set()
    all_total = 0

    for query in queries:
        results, total = _cgspace_search(query, size=req.n_results // len(queries) + 3)
        all_total = max(all_total, total)

        for item in results:
            item_id = item.get("id","") or item.get("cgspace_url","")
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            title    = (item.get("title") or "").strip()
            abstract = (item.get("abstract") or "").strip()
            author   = (item.get("author") or "").strip()
            year     = item.get("year", "")
            url      = item.get("cgspace_url", "")
            subjects = "; ".join(item.get("subject", [])[:5])

            if not title and not abstract:
                skipped += 1
                continue

            # Build rich content from ALL available metadata
            parts = []
            if title:    parts.append(f"Title: {title}")
            if author:   parts.append(f"Author: {author}")
            if year:     parts.append(f"Year: {year}")
            if url:      parts.append(f"Source: {url}")
            if subjects: parts.append(f"Keywords: {subjects}")
            parts.append(f"Query context: {query}")
            if abstract:
                parts.append(f"\nAbstract: {abstract}")
            else:
                parts.append(f"\nNote: Full text available at {url}")

            content = "\n".join(parts)
            try:
                # Use singleton vector store with in-memory text ingest (no tempfile!)
                vs.ingest_text(
                    content,
                    project_id=project_id_safe,
                    source_label=f"cgspace_{_safe(item_id[:12])}",
                )
                indexed += 1
            except Exception:
                skipped += 1

    # Update Prometheus gauge
    try:
        vector_store_documents.set(vs.collection_stats()["document_count"])
    except Exception:
        pass

    return {
        "project_id":   req.project_id,
        "queries_run":  len(queries),
        "total_found":  all_total,
        "indexed":      indexed,
        "skipped":      skipped,
        "status":       "complete",
        "message":      (
            f"Indexed {indexed} CGIAR CGSpace items for project '{req.project_id}' "
            f"using {len(queries)} Ethiopia-specific queries. "
            f"Items include title + keywords + abstract (when available)."
        ),
    }



# ── Semantic retrieval ────────────────────────────────────────────────────────

class RetrieveRequest(BaseModel):
    project_id: str
    query:      str = Field(..., min_length=2, max_length=400)
    n_results:  int = Field(5, ge=1, le=50)


@router.post("/retrieve", summary="Semantic search across indexed documents")
@limiter.limit(LIMITS["rag"])
def retrieve(request: Request, req: RetrieveRequest) -> dict:
    """
    Search the project RAG knowledge base for relevant evidence.
    Returns ranked chunks with similarity scores and source citations.
    """
    vs = _vector_store(request)
    project_id_safe = _safe(req.project_id)

    try:
        results = vs.retrieve(req.query, project_id=project_id_safe, n_results=req.n_results)
    except Exception as e:
        raise HTTPException(500, f"Retrieval failed: {e}")

    rag_retrievals_total.labels(project_id=project_id_safe).inc()

    return {
        "project_id": project_id_safe,
        "query":      req.query,
        "n_results":  len(results),
        "results":    results,
    }


# ── Extract restoration option cards ─────────────────────────────────────────

@router.get("/cards/{project_id}", summary="Extract restoration option cards from indexed docs")
@limiter.limit(LIMITS["rag"])
async def get_cards(
    request: Request,
    project_id: str,
    query: str = "restoration intervention option",
    use_llm: bool = False,
) -> dict:
    """
    Retrieve relevant chunks and extract structured RestorationOptionCards.
    Cards can be used directly by the Pathway Generator.

    use_llm=True → uses Ollama JSON mode for structured extraction (slower, more accurate)
    use_llm=False → regex extractor (default, fast, deterministic)
    """
    vs              = _vector_store(request)
    project_id_safe = _safe(project_id)

    try:
        chunks = vs.retrieve(query, project_id=project_id_safe, n_results=15)
    except Exception as e:
        raise HTTPException(500, f"Retrieval failed: {e}")

    # Choose extractor
    if use_llm:
        from app.rag.card_extractor_v2 import extract_cards_v2
        llm   = _llm_service(request)
        cards = await extract_cards_v2(chunks, project_id=project_id_safe, llm=llm, use_llm=True)
        extractor_used = "llm" if llm else "regex_fallback"
    else:
        from app.rag.card_extractor import extract_cards_from_chunks
        cards = extract_cards_from_chunks(chunks, project_id=project_id_safe)
        extractor_used = "regex"

    return {
        "project_id":      project_id_safe,
        "query":           query,
        "extractor":       extractor_used,
        "chunks_searched": len(chunks),
        "cards_extracted": len(cards),
        "cards":           [c.model_dump() for c in cards],
        "note":            "Cards are extracted from indexed documents. Confidence reflects retrieval score.",
    }


# ── RAG status ────────────────────────────────────────────────────────────────

@router.get("/status", summary="ChromaDB collection status")
def rag_status(request: Request) -> dict:
    """Check how many documents are indexed in the RAG knowledge base."""
    vs = getattr(request.app.state, "vector_store", None)
    if vs is None:
        return {"status": "unavailable", "note": "VectorStoreService not initialised"}
    try:
        stats = vs.collection_stats()
        return {
            "status":         "ready" if stats["document_count"] > 0 else "empty",
            "total_chunks":   stats["document_count"],
            "collections":    [stats],
            "chroma_dir":     stats["persist_dir"],
            "embedding_model":stats["embedding_model"],
        }
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}
