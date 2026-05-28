"""
RAG pipeline — document ingestion, chunking, embedding, retrieval.
MVP: uses ChromaDB + sentence-transformers.
Embedding provider is abstracted so it can be swapped without touching retrieval logic.
"""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Generator

# Optional heavy imports — only load if available
try:
    import chromadb
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

from app.config import settings


CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
COLLECTION_NAME = "lira_documents"


def _get_chroma_client():
    if not CHROMA_AVAILABLE:
        raise RuntimeError("chromadb not installed — run: pip install chromadb sentence-transformers")
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
    )
    return client, collection


def _extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        if not PDF_AVAILABLE:
            raise RuntimeError("pypdf not installed")
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix in (".docx", ".doc"):
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx not installed")
        doc = DocxDocument(str(file_path))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    elif suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _chunk(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> Generator[str, None, None]:
    start = 0
    while start < len(text):
        end = start + size
        yield text[start:end]
        start = end - overlap


def ingest_document(file_path: Path, project_id: str, source_label: str) -> int:
    """
    Ingest a document into the vector store. Returns number of chunks added.
    """
    _, collection = _get_chroma_client()
    text = _extract_text(file_path)
    chunks = list(_chunk(text))

    ids, documents, metadatas = [], [], []
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{project_id}:{source_label}:{i}".encode()).hexdigest()
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({
            "project_id": project_id,
            "source": source_label,
            "chunk_index": i,
        })

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    return len(chunks)


def retrieve(query: str, project_id: str, n_results: int = 5) -> list[dict]:
    """
    Semantic retrieval from the project's document store.
    Returns list of {text, source, score} dicts.
    """
    _, collection = _get_chroma_client()
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where={"project_id": project_id},
    )
    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "score": round(1.0 - dist, 3),  # convert distance to similarity
        })
    return output
