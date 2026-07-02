"""Tests for the comment-aware, self-healing config loader."""
from __future__ import annotations

import json
from pathlib import Path

from src.config_loader import DEFAULTS, load_config


def _write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "config.json"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_missing_file_returns_defaults() -> None:
    cfg = load_config("does-not-exist.json")
    assert cfg["lives"] == DEFAULTS["lives"]
    assert len(cfg["levels"]) >= 10


def test_comments_are_stripped(tmp_path: Path) -> None:
    path = _write(tmp_path, """
        # full line hash comment
        // full line slash comment
        {
          "lives": 5,  // trailing comment
          /* block
             comment */
          "seed": 7
        }
    """)
    cfg = load_config(path)
    assert cfg["lives"] == 5
    assert cfg["seed"] == 7


def test_out_of_range_values_are_clamped(tmp_path: Path) -> None:
    path = _write(tmp_path, json.dumps({"lives": 9999, "level_max_time": 1}))
    cfg = load_config(path)
    assert 1 <= cfg["lives"] <= 99
    assert cfg["level_max_time"] >= 5


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    path = _write(tmp_path, json.dumps({"totally_unknown": 1, "lives": 3}))
    cfg = load_config(path)
    assert "totally_unknown" not in cfg
    assert cfg["lives"] == 3


def test_broken_json_falls_back(tmp_path: Path) -> None:
    path = _write(tmp_path, "{ this is not valid json ]")
    cfg = load_config(path)
    assert cfg["lives"] == DEFAULTS["lives"]


def test_bad_types_use_default(tmp_path: Path) -> None:
    path = _write(tmp_path, json.dumps({"lives": "three"}))
    cfg = load_config(path)
    assert cfg["lives"] == DEFAULTS["lives"]
