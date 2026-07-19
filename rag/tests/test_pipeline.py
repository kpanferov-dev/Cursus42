"""Unit tests for the core pipeline logic (not part of the graded deliverable).

Run with ``uv run pytest -q``.
"""

from __future__ import annotations

from student.chunking import chunk_python, chunk_text
from student.evaluation import compare_sources, recall_for_one_question
from student.indexing import tokenize
from student.models import MinimalSource


def _src(a: int, b: int, path: str = "f.py") -> MinimalSource:
    return MinimalSource(
        file_path=path, first_character_index=a, last_character_index=b
    )


def test_tokenizer_splits_identifiers() -> None:
    tokens = tokenize("get_supported_mm_limits")
    assert "get_supported_mm_limits" in tokens
    assert "limits" in tokens


def test_tokenizer_splits_camel_case() -> None:
    tokens = tokenize("BaseProcessingInfo")
    assert "base" in tokens and "processing" in tokens and "info" in tokens


def test_chunk_python_keeps_functions_separate() -> None:
    code = (
        "import os\n\n\n"
        "def alpha():\n    return 1\n\n\n"
        "def beta():\n    return 2\n"
    )
    spans = chunk_python(code, max_chunk_size=1000, overlap=100)
    bodies = [code[a:b] for a, b in spans]
    assert any("def alpha" in b and "def beta" not in b for b in bodies)
    assert any("def beta" in b for b in bodies)


def test_chunk_respects_max_size() -> None:
    text = "word " * 1000
    spans = chunk_text(text, max_chunk_size=200, overlap=20)
    assert all((b - a) <= 200 for a, b in spans)


def test_iou_same_file() -> None:
    # interval [0,100) vs [0,100): IoU == 1.0
    assert compare_sources(_src(0, 100), _src(0, 100)) == 1.0
    # disjoint -> 0
    assert compare_sources(_src(0, 50), _src(50, 100)) == 0.0
    # different files -> 0
    assert compare_sources(_src(0, 100, "a"), _src(0, 100, "b")) == 0.0


def test_recall_partial() -> None:
    true_sources = [_src(0, 100), _src(200, 300)]
    pred_sources = [_src(10, 110)]  # overlaps only the first
    assert recall_for_one_question(pred_sources, true_sources, 0.05) == 0.5


def test_recall_empty_truth_is_one() -> None:
    assert recall_for_one_question([_src(0, 10)], [], 0.05) == 1.0


def test_query_expansion_adds_synonyms() -> None:
    from student.expansion import expand_query

    expanded = expand_query("how to configure the endpoint")
    assert "configure" in expanded  # original preserved
    assert "route" in expanded or "api" in expanded  # synonym added


def test_tfidf_ranks_relevant_chunk() -> None:
    from student.models import Chunk
    from student.tfidf import TfidfIndex

    chunks = [
        Chunk(chunk_id=0, file_path="a.py", first_character_index=0,
              last_character_index=20, text="load lora adapter route"),
        Chunk(chunk_id=1, file_path="b.py", first_character_index=0,
              last_character_index=20, text="unrelated tensor math"),
    ]
    index = TfidfIndex.build(chunks)
    top = index.search("lora adapter", k=2)
    assert top and top[0][0] == 0


def test_rrf_prefers_consensus() -> None:
    from student.fusion import reciprocal_rank_fusion

    fused = reciprocal_rank_fusion([[1, 2, 3], [1, 3, 2]])
    assert fused[0] == 1  # ranked first by both lists


def test_query_cache_roundtrip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from student.cache import QueryCache
    from student.models import MinimalSource

    cache = QueryCache(cache_dir=tmp_path)
    sources = [MinimalSource(file_path="a.py",
                             first_character_index=0, last_character_index=10)]
    assert cache.get("q", 5, "bm25") is None
    cache.put("q", 5, "bm25", sources)
    restored = cache.get("q", 5, "bm25")
    assert restored is not None and restored[0].file_path == "a.py"
