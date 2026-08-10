"""Document-intelligence tool (RAG) over a local folder of finance documents.

Builds a FAISS index from .txt/.md/.pdf files in DOCS_DIR on first use and
answers with the most relevant passages (with source filenames for citation).
Reuses the retrieval ideas from the author's earlier `askmydocs` project.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.tools.base import Tool, register

_INDEX: _DocIndex | None = None


@dataclass
class _Chunk:
    text: str
    source: str


class _DocIndex:
    def __init__(self, chunks: list[_Chunk], embeddings, model) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self.model = model

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        import numpy as np

        q = self.model.encode([query], normalize_embeddings=True)
        scores = (self.embeddings @ q.T).ravel()
        top = np.argsort(scores)[::-1][:k]
        return [
            {"source": self.chunks[i].source, "score": float(scores[i]), "text": self.chunks[i].text}
            for i in top
        ]


def _read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader

            return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
        except Exception:  # noqa: BLE001
            return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


def _chunk(text: str, source: str, size: int = 800, overlap: int = 120) -> list[_Chunk]:
    words, out, i = text.split(), [], 0
    while i < len(words):
        out.append(_Chunk(" ".join(words[i : i + size]), source))
        i += size - overlap
    return out


def _build_index() -> _DocIndex | None:
    docs_dir = Path(settings.docs_dir)
    if not docs_dir.exists():
        return None
    chunks: list[_Chunk] = []
    for root, _, files in os.walk(docs_dir):
        for f in files:
            if f.lower().endswith((".txt", ".md", ".pdf")):
                text = _read_file(Path(root) / f)
                if text.strip():
                    chunks.extend(_chunk(text, source=f))
    if not chunks:
        return None
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode([c.text for c in chunks], normalize_embeddings=True)
    return _DocIndex(chunks, embeddings, model)


def _search_documents(query: str, k: int = 3) -> dict[str, Any]:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    if _INDEX is None:
        return {
            "error": (
                "No documents are indexed. Add .txt/.md/.pdf files to the DOCS_DIR "
                "folder (e.g. earnings reports or fact sheets) to enable document Q&A."
            )
        }
    passages = _INDEX.search(query, k=k)
    return {"query": query, "passages": passages}


register(
    Tool(
        name="search_documents",
        description=(
            "Search the user's indexed financial documents (earnings reports, filings, "
            "fact sheets) and return the most relevant passages with source filenames."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look up in the documents."},
                "k": {"type": "integer", "default": 3, "minimum": 1, "maximum": 6},
            },
            "required": ["query"],
        },
        func=_search_documents,
    )
)
