"""BM25 indexing and persistence.

Retrieval quality on a *code* base hinges on tokenisation: a question about
``get_supported_mm_limits`` must match the identifier in the source. The
tokenizer therefore lowercases, splits on non-alphanumerics, and additionally
breaks ``snake_case`` and ``camelCase`` into sub-tokens while keeping the whole
identifier — so both "limits" and "get_supported_mm_limits" are searchable.

The index is built with the `bm25s` library (fast, NumPy-backed) and persisted
under ``data/processed`` so subsequent searches load in well under the
cold-start budget.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

import bm25s

from . import config
from .models import Chunk

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def tokenize(text: str) -> List[str]:
    """Tokenise text/code into lowercase BM25 terms.

    Splits identifiers on underscores and camel-case boundaries, keeping both
    the parts and the original identifier so either form can match.
    """
    tokens: List[str] = []
    for raw in _TOKEN_RE.findall(text):
        lowered = raw.lower()
        tokens.append(lowered)
        parts = [p.lower() for p in _CAMEL_RE.findall(raw)]
        if "_" in raw:
            parts.extend(p for p in lowered.split("_") if p)
        for part in parts:
            if part and part != lowered:
                tokens.append(part)
    return tokens


def tokenize_corpus(chunks: List[Chunk]) -> List[List[str]]:
    """Tokenise every chunk, preserving list order (== chunk_id order)."""
    return [tokenize(chunk.text) for chunk in chunks]


def build_index(chunks: List[Chunk]) -> bm25s.BM25:
    """Build a BM25 index over the chunk corpus."""
    corpus_tokens = tokenize_corpus(chunks)
    retriever = bm25s.BM25()
    retriever.index(corpus_tokens, show_progress=True)
    return retriever


def save_index(
    retriever: bm25s.BM25,
    chunks: List[Chunk],
    index_dir: Path = config.INDEX_DIR,
    chunks_dir: Path = config.CHUNKS_DIR,
    meta: dict | None = None,
) -> None:
    """Persist the BM25 index, the chunk metadata and build parameters."""
    index_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    retriever.save(str(index_dir))
    chunks_path = chunks_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(chunk.model_dump_json() + "\n")
    if meta is not None:
        (chunks_dir / "meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )


def load_chunks(chunks_dir: Path = config.CHUNKS_DIR) -> List[Chunk]:
    """Load the persisted chunk corpus in indexing order."""
    chunks_path = chunks_dir / "chunks.jsonl"
    if not chunks_path.exists():
        raise FileNotFoundError(
            f"No chunks found at {chunks_path}. Run the 'index' command first."
        )
    chunks: List[Chunk] = []
    with chunks_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                chunks.append(Chunk.model_validate_json(line))
    return chunks


def load_index(index_dir: Path = config.INDEX_DIR) -> bm25s.BM25:
    """Load a persisted BM25 index from disk."""
    if not index_dir.exists():
        raise FileNotFoundError(
            f"No index found at {index_dir}. Run the 'index' command first."
        )
    return bm25s.BM25.load(str(index_dir), mmap=False)
