"""Project-wide configuration: default paths and tunable constants.

Keeping these in one place makes the CLI thin and the defaults easy to audit
during evaluation.
"""

from __future__ import annotations

from pathlib import Path

# --- Filesystem layout (relative to the current working directory) ----------
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHUNKS_DIR = PROCESSED_DIR / "chunks"
INDEX_DIR = PROCESSED_DIR / "bm25_index"

# Where the extracted repository lives. The grader's file paths are relative to
# this root (e.g. "vllm/...", "docs/..."), so paths are stored the same way.
DEFAULT_REPO_ROOT = RAW_DIR / "vllm-0.10.1"

# --- Chunking ----------------------------------------------------------------
# The subject caps a chunk at 2000 characters and requires the cap to be a CLI
# argument. We default below the cap because smaller spans raise the IoU
# against small ground-truth sources, which improves recall@k.
DEFAULT_MAX_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
HARD_MAX_CHUNK_SIZE = 2000

# File extensions worth indexing in the vLLM repository.
CODE_EXTENSIONS = {".py"}
TEXT_EXTENSIONS = {".md", ".markdown", ".rst", ".txt"}

# Directories that never contain useful knowledge.
IGNORED_DIR_NAMES = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", ".venv", "venv", "build", "dist", ".idea",
}

# --- Retrieval ---------------------------------------------------------------
DEFAULT_K = 10
# Candidate pool re-ordered by the cross-encoder when reranking is enabled.
RERANK_POOL = 100

# --- Generation --------------------------------------------------------------
DEFAULT_MODEL_NAME = "Qwen/Qwen3-0.6B"
DEFAULT_MAX_NEW_TOKENS = 256
# How much retrieved context to feed the LLM (characters, before tokenisation).
DEFAULT_CONTEXT_CHAR_BUDGET = 6000

# --- Evaluation --------------------------------------------------------------
DEFAULT_IOU_THRESHOLD = 0.05
DEFAULT_K_VALUES = (1, 3, 5, 10)
