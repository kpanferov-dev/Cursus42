"""Retrieval over the indexed knowledge base.

The :class:`Retriever` loads every enabled backend once (BM25 always; TF-IDF and
semantic embeddings when requested) and answers queries by fusing their ranked
lists with Reciprocal Rank Fusion. It also supports opt-in query expansion and a
disk-backed query cache. These extras are the project's bonus features and are
all controlled by constructor flags / CLI flags.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import bm25s

from . import config
from .cache import QueryCache
from .expansion import expand_query
from .fusion import reciprocal_rank_fusion
from .indexing import load_chunks, load_index, tokenize
from .models import Chunk, RankedChunk

# How many candidates to pull from each backend before fusing.
_FUSION_POOL = 100

# RRF weight given to the dense retriever: documentation misses are
# paraphrase-driven, so the semantic ranking is favoured over BM25.
_SEMANTIC_WEIGHT = 2.0


class Retriever:
    """Rank indexed chunks against text queries.

    Args:
        index_dir: Directory holding the persisted indices.
        chunks_dir: Directory holding the persisted chunk corpus.
        use_tfidf: Also load the TF-IDF index and fuse it with BM25 (bonus).
        use_semantic: Also load dense embeddings and fuse them (bonus).
        expand: Expand queries with domain synonyms before searching (bonus).
        use_cache: Memoise query results to disk (bonus).
    """

    def __init__(
        self,
        index_dir: Path = config.INDEX_DIR,
        chunks_dir: Path = config.CHUNKS_DIR,
        use_tfidf: bool = False,
        use_semantic: bool = False,
        expand: bool = False,
        use_cache: bool = False,
    ) -> None:
        """Load the chunk corpus and every enabled retrieval backend."""
        self._retriever: bm25s.BM25 = load_index(index_dir)
        self._chunks: List[Chunk] = load_chunks(chunks_dir)
        self.expand = expand
        self._tfidf = None
        self._semantic = None
        self._cache: Optional[QueryCache] = QueryCache() if use_cache else None

        if use_tfidf:
            from .tfidf import TfidfIndex
            self._tfidf = TfidfIndex.load(index_dir)
        if use_semantic:
            from .embeddings import SemanticIndex
            self._semantic = SemanticIndex.load(index_dir)

    @property
    def num_chunks(self) -> int:
        """Return the number of indexed chunks."""
        return len(self._chunks)

    @property
    def is_hybrid(self) -> bool:
        """Return True when more than one backend is active."""
        return self._tfidf is not None or self._semantic is not None

    def _options_signature(self) -> str:
        """Return a string describing the active retrieval options."""
        parts = ["bm25"]
        if self._tfidf is not None:
            parts.append("tfidf")
        if self._semantic is not None:
            parts.append("semantic")
        if self.expand:
            parts.append("expand")
        return "+".join(parts)

    def _bm25_ids(self, query: str, n: int) -> List[int]:
        """Return up to ``n`` chunk ids ranked by BM25."""
        indices, _ = self._retriever.retrieve(
            [tokenize(query)], k=n, show_progress=False
        )
        return [int(i) for i in indices[0]]

    def search(self, query: str, k: int = config.DEFAULT_K) -> List[RankedChunk]:
        """Return the ``k`` best chunks for ``query`` across active backends."""
        if not query or not query.strip():
            return []
        k = max(1, min(k, len(self._chunks)))
        effective_query = expand_query(query) if self.expand else query
        options = self._options_signature()

        if self._cache is not None:
            cached = self._cache.get(query, k, options)
            if cached is not None:
                by_source = {
                    (c.file_path, c.first_character_index): c
                    for c in self._chunks
                }
                ranked: List[RankedChunk] = []
                for rank, src in enumerate(cached):
                    chunk = by_source.get(
                        (src.file_path, src.first_character_index)
                    )
                    if chunk is not None:
                        ranked.append(
                            RankedChunk(chunk=chunk, score=1.0 / (rank + 1))
                        )
                return ranked

        pool = min(max(k, _FUSION_POOL), len(self._chunks))
        if not self.is_hybrid:
            indices, scores = self._retriever.retrieve(
                [tokenize(effective_query)], k=k, show_progress=False
            )
            result = [
                RankedChunk(chunk=self._chunks[int(i)], score=float(s))
                for i, s in zip(indices[0], scores[0])
            ]
        else:
            rankings: List[List[int]] = [self._bm25_ids(effective_query, pool)]
            weights: List[float] = [1.0]
            if self._tfidf is not None:
                rankings.append(
                    [cid for cid, _ in self._tfidf.search(effective_query, pool)]
                )
                weights.append(1.0)
            if self._semantic is not None:
                rankings.append(
                    [cid for cid, _ in
                     self._semantic.search(effective_query, pool)]
                )
                weights.append(_SEMANTIC_WEIGHT)
            fused = reciprocal_rank_fusion(rankings, weights=weights)[:k]
            result = [
                RankedChunk(chunk=self._chunks[cid], score=1.0 / (rank + 1))
                for rank, cid in enumerate(fused)
            ]

        if self._cache is not None:
            self._cache.put(
                query, k, options, [r.chunk.to_source() for r in result]
            )
        return result
