"""Bonus: result caching.

Two layers of caching are used. *Index caching* is the persistence layer in
:mod:`student.indexing` — the BM25 index and chunk corpus are written to disk
once and memory-mapped on load, so repeated runs never re-ingest. *Query
caching* (this module) memoises retrieval results keyed by the query and search
options, turning repeated questions into an O(1) disk lookup. This is opt-in via
the ``--cache`` CLI flag and is most useful when the same dataset is searched
repeatedly while tuning.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List, Optional

from . import config
from .models import MinimalSource


class QueryCache:
    """A tiny JSON-file cache mapping query signatures to retrieved sources."""

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        """Create the cache directory if needed."""
        self.cache_dir = cache_dir or (config.PROCESSED_DIR / "query_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _signature(query: str, k: int, options: str) -> str:
        """Return a stable hash for a query and its search options."""
        raw = f"{query}\x00{k}\x00{options}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:24]

    def get(
        self, query: str, k: int, options: str
    ) -> Optional[List[MinimalSource]]:
        """Return cached sources for the signature, or ``None`` on a miss."""
        path = self.cache_dir / f"{self._signature(query, k, options)}.json"
        if not path.exists():
            self.misses += 1
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.hits += 1
            return [MinimalSource.model_validate(item) for item in payload]
        except (json.JSONDecodeError, OSError):
            self.misses += 1
            return None

    def put(
        self, query: str, k: int, options: str, sources: List[MinimalSource]
    ) -> None:
        """Store ``sources`` for the given query signature."""
        path = self.cache_dir / f"{self._signature(query, k, options)}.json"
        payload = [s.model_dump() for s in sources]
        try:
            path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass
