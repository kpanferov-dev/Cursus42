"""Robust JSON file input/output helpers.

Every file access in the project goes through these helpers so that
missing files and malformed JSON are reported with clear, uniform error
messages and so that file handles are always closed via context
managers.
"""

from __future__ import annotations

import json
import os
from typing import Any


class InputError(Exception):
    """Raised when an input file is missing or contains invalid JSON."""


def load_json(path: str) -> Any:
    """Load and decode a JSON file.

    Args:
        path: Path to the file to read.

    Returns:
        The decoded JSON object.

    Raises:
        InputError: If the file is missing, unreadable, or not valid JSON.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as error:
        raise InputError(f"file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise InputError(
            f"invalid JSON in {path}: {error.msg} "
            f"(line {error.lineno}, column {error.colno})") from error
    except OSError as error:
        raise InputError(f"cannot read {path}: {error}") from error


def dump_json(path: str, data: Any) -> None:
    """Write ``data`` to ``path`` as formatted JSON.

    The parent directory is created if necessary. Output is written to a
    temporary file first and then moved into place so that a partial
    write never leaves a corrupt result file behind.

    Args:
        path: Destination path.
        data: A JSON-serialisable object.

    Raises:
        InputError: If the destination cannot be written.
    """
    directory = os.path.dirname(os.path.abspath(path))
    try:
        os.makedirs(directory, exist_ok=True)
        temporary = f"{path}.tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    except OSError as error:
        raise InputError(f"cannot write {path}: {error}") from error
