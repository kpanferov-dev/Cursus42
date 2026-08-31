"""Bonus: Reciprocal Rank Fusion (RRF) for hybrid retrieval.

RRF combines several ranked lists without needing their scores to be on the
same scale: a document's fused score is the sum of ``1 / (rrf_k + rank)`` over
the lists it appears in (rank is 1-based). It is robust and parameter-light,
which is why it is the standard way to blend BM25 with TF-IDF or dense
retrievers.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[int]],
    rrf_k: int = DEFAULT_RRF_K,
    weights: Sequence[float] | None = None,
) -> List[int]:
    """Fuse several ranked lists of chunk ids into one ordering.

    Args:
        ranked_lists: Each inner sequence is chunk ids ordered best-first.
        rrf_k: The RRF damping constant.
        weights: Optional per-list weight; a list contributes
            ``weight / (rrf_k + rank)``. Defaults to 1.0 for every list. Used to
            favour the dense retriever on documentation queries.

    Returns:
        Chunk ids ordered by fused score, best first.
    """
    if weights is None:
        weights = [1.0] * len(ranked_lists)
    scores: Dict[int, float] = defaultdict(float)
    for weight, ranking in zip(weights, ranked_lists):
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += weight / (rrf_k + rank)
    return [cid for cid, _ in sorted(
        scores.items(), key=lambda kv: kv[1], reverse=True
    )]
