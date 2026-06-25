"""Tests for I/O and graceful error handling."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.io_utils import (
    InputError,
    load_function_definitions,
    load_test_prompts,
    write_output,
)


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="not found"):
        load_function_definitions(tmp_path / "missing.json")


def test_load_invalid_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(InputError, match="Invalid JSON"):
        load_test_prompts(bad)


def test_load_non_array_raises(tmp_path: Path) -> None:
    bad = tmp_path / "obj.json"
    bad.write_text('{"not": "an array"}', encoding="utf-8")
    with pytest.raises(InputError, match="JSON array"):
        load_function_definitions(bad)


def test_load_invalid_schema_raises(tmp_path: Path) -> None:
    bad = tmp_path / "schema.json"
    bad.write_text('[{"name": 123}]', encoding="utf-8")
    with pytest.raises(InputError, match="Invalid function definition"):
        load_function_definitions(bad)


def test_load_valid_functions(tmp_path: Path) -> None:
    good = tmp_path / "good.json"
    good.write_text(
        json.dumps(
            [
                {
                    "name": "fn_add",
                    "description": "add",
                    "parameters": {"a": {"type": "number"}},
                    "returns": {"type": "number"},
                }
            ]
        ),
        encoding="utf-8",
    )
    fns = load_function_definitions(good)
    assert len(fns) == 1
    assert fns[0].name == "fn_add"
    assert fns[0].parameters["a"].type == "number"


def test_write_output_creates_parent(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "deep" / "out.json"
    write_output(out, [{"prompt": "p", "name": "fn", "parameters": {}}])
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded[0]["name"] == "fn"
