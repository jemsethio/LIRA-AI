"""
VectorStoreService — LIRA-AI singleton wrapper for ChromaDB
==============================================================
Eliminates the per-call PersistentClient + SentenceTransformer reload
(was costing 200–500 ms latency per RAG call in the MVP).

Instantiated **once** in main.py lifespan and reused for the process lifetime.

Compatibility:
  - Public methods (ingest_chunks, retrieve) preserve the legacy
    `ingest_document` / `retrieve` shapes from app/rag/ingestion.py
  - Returns same {text, source, score} dicts so callers do not change
  - Distance → similarity uses cosine space (correct semantics)
"""

from __future__ import annotations
import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Optional

from app.config import settings
from app.services.chunker import chunk as semantic_chunk

logger = logging.getLogger(__name__)


# ── Optional heavy imports (graceful degradation) ────────────────────────────
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


COLLECTION_NAME    = "lira_documents"
EMBEDDING_MODEL    = "all-MiniLM-L6-v2"
COSINE_SPACE       = "cosine"      # → score = 1 - distance is valid
SAFE_LABEL_RE      = re.compile(r"[^a-zA-Z0-9_\-]")


def _sanitise(label: str, max_len: int = 64) -> str:
    """Strip path traversal / shell-metachars from a label."""
    cleaned = SAFE_LABEL_RE.sub("_", label)[:max_len]
    return cleaned or "unlabeled"


def _extract_text(file_path: Path) -> str:
    """Extract plain text from a supported document format."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        if not PDF_AVAILABLE:
            raise RuntimeError("pypdf not installed — run: pip install pypdf")
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in (".docx", ".doc"):
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx not installed")
        doc = DocxDocument(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix}")


class VectorStoreService:
    """
    Singleton wrapper around ChromaDB.

    Lifecycle:
      vs = VectorStoreService(persist_dir=Path(...))   # in lifespan startup
      vs.ingest_document(...)
      vs.retrieve(...)
      vs.health()                                      # for /health/ready

    Thread-safety:
      ChromaDB PersistentClient is process-safe but not multi-worker safe.
      For multi-worker deployments, switch to ChromaDB HTTP mode (server).
    """

    def __init__(self, persist_dir: Optional[Path] = None) -> None:
        if not CHROMA_AVAILABLE:
            raise RuntimeError("chromadb not installed — run: pip install chromadb sentence-transformers")
        self._persist_dir = Path(persist_dir or settings.chroma_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        t0 = time.time()
        # Single PersistentClient for the process lifetime
        self._client = chromadb.PersistentClient(
            path=str(self._persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # SentenceTransformer loaded ONCE (~80 MB → keep in memory)
        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": COSINE_SPACE},
        )
        logger.info(
            "VectorStoreService ready: model=%s, dir=%s, ms=%d",
            EMBEDDING_MODEL, self._persist_dir, int((time.time() - t0) * 1000)
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest_document(self, file_path: Path, project_id: str, source_label: str) -> int:
        """
        Drop-in replacement for legacy ingest_document().
        Returns: number of chunks indexed.
        """
        text = _extract_text(file_path)
        return self.ingest_text(text, project_id=project_id, source_label=source_label)

    def ingest_text(self, text: str, project_id: str, source_label: str) -> int:
        """Ingest already-extracted text (skips file extraction)."""
        if not text or not text.strip():
            return 0

        # Sanitise IDs so user input cannot construct collisions or unsafe paths
        project_id   = _sanitise(project_id, max_len=80)
        source_label = _sanitise(source_label, max_len=80)

        chunks = semantic_chunk(text)
        if not chunks:
            return 0

        ids, documents, metadatas = [], [], []
        for i, chunk_text in enumerate(chunks):
            chunk_id = hashlib.sha1(
                f"{project_id}:{source_label}:{i}:{chunk_text[:32]}".encode()
            ).hexdigest()
            ids.append(chunk_id)
            documents.append(chunk_text)
            metadatas.append({
                "project_id":    project_id,
                "source":        source_label,
                "chunk_index":   i,
                "chunker_version": "2",     # for future migrations
                "ingested_at":   int(time.time()),
            })

        self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    def retrieve(
        self,
        query: str,
        project_id: str,
        n_results: int = 5,
        source_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Semantic retrieval.
        Returns: list of {text, source, score} where score in [0, 1] (cosine).
        """
        project_id = _sanitise(project_id, max_len=80)

        where: dict = {"project_id": project_id}
        if source_filter:
            where["source"] = _sanitise(source_filter, max_len=80)

        results = self._collection.query(
            query_texts=[query],
            n_results=max(1, min(n_results, 50)),     # clamp
            where=where,
        )

        output: list[dict] = []
        docs    = results.get("documents", [[]])[0] or []
        metas   = results.get("metadatas", [[]])[0] or []
        dists   = results.get("distances", [[]])[0] or []
        for doc, meta, dist in zip(docs, metas, dists):
            # Cosine distance ranges [0,2] for non-normalised, [0,1] for normalised
            # all-MiniLM-L6-v2 produces normalised embeddings → 1 - dist is valid similarity
            similarity = round(max(0.0, 1.0 - float(dist)), 3)
            output.append({
                "text":   doc,
                "source": (meta or {}).get("source", "unknown"),
                "score":  similarity,
            })
        return output

    def collection_stats(self) -> dict:
        """For /rag/status and /health/ready."""
        try:
            count = self._collection.count()
        except Exception:
            count = -1
        return {
            "name":         COLLECTION_NAME,
            "document_count": count,
            "embedding_model": EMBEDDING_MODEL,
            "space":        COSINE_SPACE,
            "persist_dir":  str(self._persist_dir),
        }

    def health(self) -> bool:
        """Quick health check — returns True if Chroma is reachable."""
        try:
            self._collection.count()
            return True
        except Exception as e:
            logger.warning("VectorStore health check failed: %s", e)
            return False

    def close(self) -> None:
        """Called on FastAPI shutdown. Chroma client has no explicit close."""
        logger.info("VectorStoreService closing")
