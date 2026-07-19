"""Knowledge-base ingestion.

Walk a repository, read every code/text file, split it with the appropriate
chunking strategy, and emit :class:`~student.models.Chunk` objects whose
``file_path`` is stored *relative to the repository root* — exactly the form the
grader's ground-truth sources use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, List

from tqdm import tqdm

from . import config
from .chunking import chunk_markdown, chunk_python, chunk_text
from .models import Chunk


def _iter_files(repo_root: Path) -> Iterator[Path]:
    """Yield indexable files under ``repo_root``, skipping junk directories."""
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in config.IGNORED_DIR_NAMES for part in path.parts):
            continue
        suffix = path.suffix.lower()
        if suffix in config.CODE_EXTENSIONS or suffix in config.TEXT_EXTENSIONS:
            yield path


def _read_text(path: Path) -> str:
    """Read a file as UTF-8 text, replacing undecodable bytes."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""


def ingest_repository(
    repo_root: Path,
    max_chunk_size: int = config.DEFAULT_MAX_CHUNK_SIZE,
    overlap: int = config.DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """Read and chunk every relevant file under ``repo_root``.

    Args:
        repo_root: Directory containing the extracted repository.
        max_chunk_size: Maximum characters per chunk (hard-capped at 2000).
        overlap: Characters shared between consecutive chunks.

    Returns:
        All chunks, each carrying a unique ``chunk_id`` and a repo-relative
        ``file_path``.

    Raises:
        FileNotFoundError: If ``repo_root`` does not exist.
    """
    repo_root_display = Path(repo_root)
    repo_root = repo_root.resolve()
    if not repo_root.is_dir():
        raise FileNotFoundError(f"Repository root not found: {repo_root}")

    max_chunk_size = min(max_chunk_size, config.HARD_MAX_CHUNK_SIZE)
    chunks: List[Chunk] = []
    chunk_id = 0

    files = list(_iter_files(repo_root))
    for path in tqdm(files, desc="Ingesting", unit="file"):
        text = _read_text(path)
        if not text.strip():
            continue
        rel_path = (repo_root_display / path.relative_to(repo_root)).as_posix()
        suffix = path.suffix.lower()
        if suffix in config.CODE_EXTENSIONS:
            spans = chunk_python(text, max_chunk_size, overlap)
            kind = "code"
        elif suffix in {".md", ".markdown"}:
            spans = chunk_markdown(text, max_chunk_size, overlap)
            kind = "text"
        else:
            spans = chunk_text(text, max_chunk_size, overlap)
            kind = "text"
        for first, last in spans:
            snippet = text[first:last]
            if not snippet.strip():
                continue
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    file_path=rel_path,
                    first_character_index=first,
                    last_character_index=last,
                    text=snippet,
                    kind=kind,
                )
            )
            chunk_id += 1

    return chunks
