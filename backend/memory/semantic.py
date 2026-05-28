from __future__ import annotations

import re


def _tokenize(text: str) -> set[str]:
    """Lower-case word tokens, stripping punctuation."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _overlap_score(query_tokens: set[str], text_tokens: set[str]) -> float:
    """Jaccard-style word-overlap score in [0, 1]."""
    if not query_tokens or not text_tokens:
        return 0.0
    intersection = len(query_tokens & text_tokens)
    union = len(query_tokens | text_tokens)
    return intersection / union


class SemanticMemory:
    """
    L2 in-memory semantic store.

    Uses word-overlap (TF-IDF placeholder) for retrieval — no FAISS dependency
    required in dev.  Drop-in replaceable with a real vector store later.
    """

    def __init__(self) -> None:
        self._store: list[tuple[str, dict]] = []  # (text, metadata)

    def add(self, text: str, metadata: dict) -> None:
        """Embed (placeholder) and store a text chunk with its metadata."""
        self._store.append((text, dict(metadata)))

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Return up to *top_k* entries ranked by word overlap with *query*.

        Each result is ``{"text": str, "metadata": dict, "score": float}``.
        """
        query_tokens = _tokenize(query)
        scored = [
            {
                "text": text,
                "metadata": meta,
                "score": _overlap_score(query_tokens, _tokenize(text)),
            }
            for text, meta in self._store
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        """Remove all stored entries."""
        self._store.clear()
