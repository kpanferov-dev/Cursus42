"""File I/O helpers with graceful error handling.

All public functions either return a valid object or raise a single
custom :class:`InputError`, which the entry point converts into a
clean user-facing message instead of a stack trace.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import FunctionDefinition, TestPrompt


class InputError(Exception):
    """Raised when an input file is missing or malformed."""


def _load_json(path: Path) -> Any:
    """Read ``path`` as UTF-8 JSON with friendly error messages.

    Args:
        path: Filesystem path to the JSON file.

    Returns:
        Parsed JSON object (list or dict).

    Raises:
        InputError: If the file is missing, unreadable, or invalid JSON.
    """
    if not path.exists():
        raise InputError(f"Input file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise InputError(
            f"Invalid JSON in {path}: {exc.msg} (line {exc.lineno})"
        ) from exc
    except OSError as exc:
        raise InputError(f"Could not read {path}: {exc}") from exc


def load_function_definitions(path: Path) -> list[FunctionDefinition]:
    """Load and validate the function-definitions file."""
    raw = _load_json(path)
    if not isinstance(raw, list):
        raise InputError(
            f"{path} must contain a JSON array of function definitions."
        )
    try:
        return [FunctionDefinition.model_validate(item) for item in raw]
    except Exception as exc:  # pydantic.ValidationError + others
        raise InputError(
            f"Invalid function definition in {path}: {exc}"
        ) from exc


def load_test_prompts(path: Path) -> list[TestPrompt]:
    """Load and validate the test-prompts file."""
    raw = _load_json(path)
    if not isinstance(raw, list):
        raise InputError(f"{path} must contain a JSON array of prompts.")
    try:
        return [TestPrompt.model_validate(item) for item in raw]
    except Exception as exc:
        raise InputError(f"Invalid prompt entry in {path}: {exc}") from exc


def write_output(path: Path, payload: list[dict[str, Any]]) -> None:
    """Write ``payload`` as pretty-printed JSON to ``path``.

    Creates parent directories as needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
