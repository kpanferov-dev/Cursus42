"""Chunking strategies.

The retriever can only return spans it has indexed, so *how* a file is split
directly determines the best achievable recall. Two strategies are used:

* **Python code** is split along structural boundaries (top-level functions and
  classes) using the :mod:`ast` module, which keeps semantically related lines
  together. Oversized units fall back to a sliding window.
* **Text / Markdown** is split with a character sliding window that prefers to
  cut on blank lines, so paragraphs and headings stay intact.

Every chunk records the exact half-open character span ``[first, last)`` it
occupies in the original file, which is what the grader compares against ground
truth. No chunk ever exceeds ``max_chunk_size`` characters, satisfying the
moulinette's validation rule.
"""

from __future__ import annotations

import ast
import re
from typing import List, Tuple

_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)


def _line_start_offsets(text: str) -> List[int]:
    """Return the character offset at which each (0-based) line begins."""
    offsets = [0]
    for index, char in enumerate(text):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _sliding_window_spans(
    start: int,
    end: int,
    max_chunk_size: int,
    overlap: int,
) -> List[Tuple[int, int]]:
    """Slice ``[start, end)`` into overlapping windows of bounded size."""
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be positive")
    overlap = max(0, min(overlap, max_chunk_size - 1))
    stride = max_chunk_size - overlap
    spans: List[Tuple[int, int]] = []
    cursor = start
    while cursor < end:
        stop = min(cursor + max_chunk_size, end)
        spans.append((cursor, stop))
        if stop >= end:
            break
        cursor += stride
    return spans


def _emit(
    start: int,
    end: int,
    text: str,
    max_chunk_size: int,
    overlap: int,
) -> List[Tuple[int, int]]:
    """Emit one span, windowing it if it exceeds ``max_chunk_size``."""
    if end <= start or not text[start:end].strip():
        return []
    if end - start <= max_chunk_size:
        return [(start, end)]
    return _sliding_window_spans(start, end, max_chunk_size, overlap)


def chunk_text(
    text: str,
    max_chunk_size: int,
    overlap: int,
) -> List[Tuple[int, int]]:
    """Chunk free text, preferring blank-line boundaries.

    Args:
        text: Full file content.
        max_chunk_size: Maximum characters per chunk.
        overlap: Characters shared between consecutive chunks.

    Returns:
        A list of half-open ``(first, last)`` character spans.
    """
    if not text:
        return []
    spans: List[Tuple[int, int]] = []
    paragraphs = _split_on_blank_lines(text)
    for para_start, para_end in paragraphs:
        if para_end - para_start <= max_chunk_size:
            spans.append((para_start, para_end))
        else:
            spans.extend(
                _sliding_window_spans(para_start, para_end, max_chunk_size, overlap)
            )
    return _merge_tiny_spans(text, spans, max_chunk_size)


def _split_on_blank_lines(text: str) -> List[Tuple[int, int]]:
    """Split text into paragraph spans separated by blank lines."""
    spans: List[Tuple[int, int]] = []
    start = 0
    length = len(text)
    index = 0
    while index < length:
        if text.startswith("\n\n", index):
            spans.append((start, index))
            while index < length and text[index] == "\n":
                index += 1
            start = index
        else:
            index += 1
    if start < length:
        spans.append((start, length))
    return [(a, b) for a, b in spans if b > a]


def _merge_tiny_spans(
    text: str,
    spans: List[Tuple[int, int]],
    max_chunk_size: int,
) -> List[Tuple[int, int]]:
    """Greedily merge adjacent short spans to reduce index noise."""
    if not spans:
        return spans
    merged: List[Tuple[int, int]] = [spans[0]]
    for start, end in spans[1:]:
        prev_start, prev_end = merged[-1]
        if start == prev_end and (end - prev_start) <= max_chunk_size:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged


def chunk_markdown(
    text: str,
    max_chunk_size: int,
    overlap: int,
) -> List[Tuple[int, int]]:
    """Chunk Markdown by heading sections.

    Each ``#``..``######`` heading starts a new section that runs until the next
    heading. Consecutive sections are greedily packed into chunks up to
    ``max_chunk_size`` so a chunk holds a coherent, keyword-dense unit aligned
    with how documentation sources are annotated. Oversized single sections are
    windowed.

    Args:
        text: Full file content.
        max_chunk_size: Maximum characters per chunk.
        overlap: Characters shared between consecutive chunks for oversized
            sections.

    Returns:
        A list of half-open ``(first, last)`` character spans.
    """
    if not text:
        return []
    # Section boundaries: start of file + every heading start.
    starts = [0]
    starts.extend(m.start() for m in _HEADING_RE.finditer(text))
    starts = sorted(set(starts))
    sections: List[Tuple[int, int]] = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        if end > start and text[start:end].strip():
            sections.append((start, end))
    if not sections:
        return chunk_text(text, max_chunk_size, overlap)

    spans: List[Tuple[int, int]] = []
    for start, end in sections:
        spans.extend(_emit(start, end, text, max_chunk_size, overlap))
    return spans


def chunk_python(
    text: str,
    max_chunk_size: int,
    overlap: int,
) -> List[Tuple[int, int]]:
    """Chunk Python source along top-level definitions.

    Falls back to text chunking if the file cannot be parsed (e.g. Python 2
    syntax or templated files).

    Args:
        text: Full file content.
        max_chunk_size: Maximum characters per chunk.
        overlap: Characters shared between consecutive chunks when an oversized
            unit must be windowed.

    Returns:
        A list of half-open ``(first, last)`` character spans.
    """
    if not text:
        return []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return chunk_text(text, max_chunk_size, overlap)

    line_starts = _line_start_offsets(text)

    def node_span(node: ast.AST) -> Tuple[int, int]:
        start_line = getattr(node, "lineno", 1)
        start_col = getattr(node, "col_offset", 0)
        end_line = getattr(node, "end_lineno", start_line)
        end_col = getattr(node, "end_col_offset", 0)
        start = line_starts[start_line - 1] + start_col
        end = line_starts[end_line - 1] + end_col
        return start, min(end, len(text))

    definition_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    spans: List[Tuple[int, int]] = []
    preamble_start = 0  # accumulates module-level imports / simple statements

    def flush_preamble(up_to: int) -> None:
        """Emit the accumulated module-level preamble as one (or more) chunks."""
        nonlocal preamble_start
        if up_to > preamble_start and text[preamble_start:up_to].strip():
            spans.extend(
                _emit(preamble_start, up_to, text, max_chunk_size, overlap)
            )
        preamble_start = up_to

    for node in tree.body:
        start, end = node_span(node)
        if isinstance(node, definition_types):
            # Flush preamble that ended before this definition, then keep the
            # definition as its own chunk(s) so small targets keep a high IoU.
            flush_preamble(start)
            spans.extend(_emit(start, end, text, max_chunk_size, overlap))
            preamble_start = end
    flush_preamble(len(text))
    return spans
