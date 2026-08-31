"""Bonus: cross-encoder reranking.

The hybrid retriever already places the correct source inside the top-k for most
questions, but not always inside the top-5 — a pure *ordering* problem. A
cross-encoder scores the (question, chunk) pair jointly and is far more accurate
at ordering than bi-encoder similarity, so re-ranking the retrieved candidates
lifts Recall@5 toward Recall@10.

The model runs through `fastembed`, which uses **ONNX Runtime** — no
``torch``/CUDA — so the ~80MB model fits a constrained cluster. The dependency
is imported lazily; enable it with ``--rerank`` after:

    uv sync --extra rerank
"""

from __future__ import annotations

from typing import List, Optional

DEFAULT_RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-12-v2"


class CrossEncoderReranker:
    """Re-order candidate documents by cross-encoder relevance score."""

    def __init__(self, model_name: str = DEFAULT_RERANK_MODEL) -> None:
        """Store the model name; the ONNX model is loaded on first use."""
        self.model_name = model_name
        self._encoder: Optional[object] = None

    def _ensure_loaded(self) -> None:
        """Load the fastembed cross-encoder once, on demand."""
        if self._encoder is not None:
            return
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "Reranking requires 'fastembed'. "
                "Install it with: uv sync --extra rerank"
            ) from exc
        self._encoder = TextCrossEncoder(model_name=self.model_name)

    def order(self, query: str, documents: List[str]) -> List[int]:
        if not documents:
            return []
        self._ensure_loaded()
        encoder = self._encoder
        assert encoder is not None
        truncated = [doc[:1000] for doc in documents]
        scores = list(encoder.rerank(query, truncated))  # type: ignore[attr-defined]
        return sorted(range(len(documents)), key=lambda i: scores[i], reverse=True)
