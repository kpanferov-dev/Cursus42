"""Bonus: a self-contained TF-IDF retriever (second signal for hybrid search).

A compact inverted index stores, for every term, the list of
``(chunk_id, l2_normalised_weight)`` postings. Cosine similarity against a query
is then a sparse dot product over the query's terms. Implemented with the
standard library + a tiny bit of math only, so it adds no heavy dependency and
runs fully offline.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from . import config
from .indexing import tokenize
from .models import Chunk

_TFIDF_FILE = "tfidf_index.json"


class TfidfIndex:
    """Sparse TF-IDF index with cosine-similarity retrieval."""

    def __init__(
        self,
        idf: Dict[str, float],
        postings: Dict[str, List[Tuple[int, float]]],
        num_docs: int,
    ) -> None:
        """Store the IDF table and inverted postings."""
        self.idf = idf
        self.postings = postings
        self.num_docs = num_docs

    @classmethod
    def build(cls, chunks: List[Chunk]) -> "TfidfIndex":
        """Build a TF-IDF index over the chunk corpus."""
        num_docs = len(chunks)
        doc_freq: Counter = Counter()
        tokenised: List[Counter] = []
        for chunk in chunks:
            counts = Counter(tokenize(chunk.text))
            tokenised.append(counts)
            doc_freq.update(counts.keys())

        idf: Dict[str, float] = {
            term: math.log((num_docs + 1) / (df + 1)) + 1.0
            for term, df in doc_freq.items()
        }

        postings: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        for doc_id, counts in enumerate(tokenised):
            weights = {
                term: (1.0 + math.log(tf)) * idf[term]
                for term, tf in counts.items()
            }
            norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
            for term, weight in weights.items():
                postings[term].append((doc_id, weight / norm))
        return cls(idf, dict(postings), num_docs)

    def search(self, query: str, k: int) -> List[Tuple[int, float]]:
        """Return up to ``k`` ``(chunk_id, score)`` pairs, best first."""
        counts = Counter(tokenize(query))
        if not counts:
            return []
        q_weights = {
            term: (1.0 + math.log(tf)) * self.idf.get(term, 0.0)
            for term, tf in counts.items()
        }
        norm = math.sqrt(sum(w * w for w in q_weights.values())) or 1.0
        scores: Dict[int, float] = defaultdict(float)
        for term, q_weight in q_weights.items():
            if q_weight == 0.0:
                continue
            for doc_id, d_weight in self.postings.get(term, []):
                scores[doc_id] += (q_weight / norm) * d_weight
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:k]

    def save(self, index_dir: Path = config.INDEX_DIR) -> None:
        """Persist the TF-IDF index as JSON."""
        index_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "num_docs": self.num_docs,
            "idf": self.idf,
            "postings": {t: p for t, p in self.postings.items()},
        }
        (index_dir / _TFIDF_FILE).write_text(
            json.dumps(payload), encoding="utf-8"
        )

    @classmethod
    def load(cls, index_dir: Path = config.INDEX_DIR) -> "TfidfIndex":
        """Load a persisted TF-IDF index."""
        path = index_dir / _TFIDF_FILE
        if not path.exists():
            raise FileNotFoundError(
                f"No TF-IDF index at {path}. Re-run 'index --tfidf'."
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        postings = {
            term: [(int(d), float(w)) for d, w in plist]
            for term, plist in payload["postings"].items()
        }
        return cls(payload["idf"], postings, int(payload["num_docs"]))
