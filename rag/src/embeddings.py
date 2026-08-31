"""Bonus: dense semantic retrieval with static embeddings (model2vec).

Catches paraphrases that lexical methods miss (questions whose wording shares no
keywords with the source). We use **model2vec** static embeddings instead of a
transformer: inference is pure NumPy, needs no ``torch``/CUDA, and the model is
~30MB — so it fits a constrained cluster where full PyTorch will not. Enable
with the ``--semantic`` flag after installing the extra:

    uv sync --extra semantic

Embeddings are cached to ``data/processed/bm25_index/embeddings.npy`` so they
are computed only once.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from . import config
from .models import Chunk

_EMB_FILE = "embeddings.npy"
DEFAULT_EMBED_MODEL = "minishlab/potion-base-8M"


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """L2-normalise rows so dot product equals cosine similarity."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized: np.ndarray = (matrix / norms).astype(np.float32)
    return normalized


class SemanticIndex:
    """Dense retriever over normalised static chunk embeddings."""

    def __init__(
        self,
        embeddings: np.ndarray,
        model_name: str = DEFAULT_EMBED_MODEL,
    ) -> None:
        """Store the (already L2-normalised) embedding matrix."""
        self.embeddings = embeddings
        self.model_name = model_name
        self._model: Optional[object] = None

    @staticmethod
    def _load_model(model_name: str) -> object:
        """Load a model2vec static model, raising a clear error if absent."""
        try:
            from model2vec import StaticModel
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "Semantic retrieval requires 'model2vec'. "
                "Install it with: uv sync --extra semantic"
            ) from exc
        return StaticModel.from_pretrained(model_name)

    @classmethod
    def build(
        cls,
        chunks: List[Chunk],
        model_name: str = DEFAULT_EMBED_MODEL,
    ) -> "SemanticIndex":
        """Encode every chunk and L2-normalise the resulting vectors."""
        model = cls._load_model(model_name)
        texts = [chunk.text for chunk in chunks]
        vectors = np.asarray(model.encode(texts), dtype=np.float32)  # type: ignore
        index = cls(_l2_normalize(vectors), model_name)
        index._model = model
        return index

    def search(self, query: str, k: int) -> List[Tuple[int, float]]:
        """Return up to ``k`` ``(chunk_id, cosine)`` pairs, best first."""
        if self._model is None:
            self._model = self._load_model(self.model_name)
        query_vec = np.asarray(
            self._model.encode([query]), dtype=np.float32  # type: ignore
        )
        query_arr = _l2_normalize(query_vec)[0]
        scores = self.embeddings @ query_arr
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top]

    def save(self, index_dir: Path = config.INDEX_DIR) -> None:
        """Persist the embedding matrix to disk."""
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(index_dir / _EMB_FILE, self.embeddings)

    @classmethod
    def load(
        cls,
        index_dir: Path = config.INDEX_DIR,
        model_name: str = DEFAULT_EMBED_MODEL,
    ) -> "SemanticIndex":
        """Load persisted embeddings."""
        path = index_dir / _EMB_FILE
        if not path.exists():
            raise FileNotFoundError(
                f"No embeddings at {path}. Re-run 'index --semantic'."
            )
        return cls(np.load(path), model_name)
