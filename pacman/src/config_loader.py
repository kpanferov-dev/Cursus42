"""Load and validate the game configuration file.

The configuration is JSON, extended with comment support:

* full-line comments starting with ``#``
* C / C++ style comments (``//`` and ``/* ... */``)

Any problem (missing file, bad JSON, missing key, out-of-range value) is
handled gracefully: a clear message is printed, a safe default is used and
the program keeps running.  No Python traceback ever reaches the user.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

# Safe default values.  Every key the game relies on must appear here so that
# a totally empty (or broken) config still produces a playable game.
DEFAULTS: Dict[str, Any] = {
    "highscore_filename": "highscores.json",
    "lives": 3,
    "pacgum": 42,
    "points_per_pacgum": 10,
    "points_per_super_pacgum": 50,
    "points_per_ghost": 200,
    "seed": 42,
    "level_max_time": 90,
    "levels": [
        {"width": 21, "height": 21},
        {"width": 21, "height": 21},
        {"width": 23, "height": 23},
        {"width": 23, "height": 23},
        {"width": 25, "height": 25},
        {"width": 25, "height": 25},
        {"width": 27, "height": 27},
        {"width": 27, "height": 27},
        {"width": 29, "height": 29},
        {"width": 31, "height": 31},
    ],
}

# Acceptable ranges for numeric keys -> (minimum, maximum).
_RANGES: Dict[str, tuple[int, int]] = {
    "lives": (1, 99),
    "pacgum": (1, 9999),
    "points_per_pacgum": (0, 100000),
    "points_per_super_pacgum": (0, 100000),
    "points_per_ghost": (0, 100000),
    "seed": (1, 2 ** 31),
    "level_max_time": (5, 6000),
}

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(raw: str) -> str:
    """Remove ``#``, ``//`` and ``/* */`` comments from *raw* text.

    Args:
        raw: The original file contents.

    Returns:
        A string that is valid standard JSON.
    """
    raw = _BLOCK_COMMENT.sub("", raw)
    cleaned: List[str] = []
    for line in raw.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        # Drop trailing "  // ..." comments while keeping "://" inside strings
        # safe enough for a config file (no URLs expected here).
        if "//" in line and not _inside_string(line, line.index("//")):
            line = line[: line.index("//")]
        cleaned.append(line)
    return "\n".join(cleaned)


def _inside_string(line: str, pos: int) -> bool:
    """Return True if character index *pos* lies inside a JSON string."""
    return line[:pos].count('"') % 2 == 1


def _clamp_int(name: str, value: Any) -> int:
    """Coerce *value* to an int and clamp it to the range of *name*."""
    default = DEFAULTS[name]
    try:
        number = int(value)
    except (TypeError, ValueError):
        print(f"[config] '{name}' is not an integer, "
              f"using default {default}.")
        return int(default)
    low, high = _RANGES[name]
    if number < low or number > high:
        clamped = max(low, min(high, number))
        print(f"[config] '{name}'={number} out of range "
              f"[{low}, {high}], clamped to {clamped}.")
        return clamped
    return number


def _validate_levels(value: Any) -> List[Dict[str, int]]:
    """Validate the list of levels, falling back to defaults when needed."""
    if not isinstance(value, list) or not value:
        print("[config] 'levels' missing or empty, using default levels.")
        return [dict(lv) for lv in DEFAULTS["levels"]]
    levels: List[Dict[str, int]] = []
    for index, item in enumerate(value):
        width = 21
        height = 21
        if isinstance(item, dict):
            width = _clamp_dimension(item.get("width", 21))
            height = _clamp_dimension(item.get("height", 21))
        else:
            print(f"[config] level #{index} is malformed, using 21x21.")
        levels.append({"width": width, "height": height})
    return levels


def _clamp_dimension(value: Any) -> int:
    """Clamp a maze width/height to a sane, odd-friendly range."""
    try:
        size = int(value)
    except (TypeError, ValueError):
        size = 21
    # The A-Maze-ing package needs at least ~14 cells to insert the "42".
    return max(14, min(60, size))


def load_config(path: str) -> Dict[str, Any]:
    """Read and validate the configuration file at *path*.

    Args:
        path: Path to the JSON (with comments) configuration file.

    Returns:
        A fully populated, validated configuration dictionary.  When the
        file cannot be read the returned dictionary is the set of defaults.
    """
    config: Dict[str, Any] = {}
    for key, value in DEFAULTS.items():
        if isinstance(value, list):
            config[key] = [dict(item) for item in value]
        else:
            config[key] = value
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as error:
        print(f"[config] cannot read '{path}': {error}. Using defaults.")
        return config

    try:
        data = json.loads(_strip_comments(raw))
    except json.JSONDecodeError as error:
        print(f"[config] invalid JSON in '{path}': {error}. Using defaults.")
        return config

    if not isinstance(data, dict):
        print("[config] top-level JSON must be an object. Using defaults.")
        return config

    # Known keys are validated; unknown keys are silently ignored.
    for name in _RANGES:
        if name in data:
            config[name] = _clamp_int(name, data[name])
    if "highscore_filename" in data:
        value = data["highscore_filename"]
        config["highscore_filename"] = (
            value if isinstance(value, str) and value
            else DEFAULTS["highscore_filename"])
    config["levels"] = _validate_levels(data.get("levels"))
    return config
