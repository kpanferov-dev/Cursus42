"""Integration tests: the decoder must always emit valid, typed calls.

These tests use the mock SDK, which returns logits unrelated to any
"correct" answer. Passing them demonstrates that validity comes from the
constrained decoder, not from the model guessing well.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from llm_sdk import Small_LLM_Model
from src.decoder import ConstrainedDecoder
from src.io_utils import InputError, load_json
from src.models import FunctionDefinition, Prompt, parse_function_definitions
from src.pipeline import FunctionCallingPipeline
from src.vocab import Vocabulary

_TYPE_OF: Dict[str, type] = {
    "number": float,
    "integer": int,
    "string": str,
    "boolean": bool,
}


def _make_pipeline(
    definitions: List[Dict[str, Any]],
) -> FunctionCallingPipeline:
    """Build a pipeline backed by the mock SDK."""
    functions: List[FunctionDefinition] = parse_function_definitions(
        definitions)
    model = Small_LLM_Model()
    vocab = Vocabulary.from_file(model.get_path_to_vocab_file())
    decoder = ConstrainedDecoder(model, vocab)
    return FunctionCallingPipeline(functions, decoder)


def _assert_valid(record: Dict[str, Any], definitions: List[Dict[str, Any]]) -> None:
    """Assert a single result record matches the schema exactly."""
    by_name = {item["name"]: item for item in definitions}
    assert set(record) == {"prompt", "name", "parameters"}
    assert record["name"] in by_name
    spec = by_name[record["name"]]["parameters"]
    assert set(record["parameters"]) == set(spec)
    for key, value in record["parameters"].items():
        expected = _TYPE_OF[spec[key]["type"]]
        if expected is int:
            assert type(value) is int
        elif expected is bool:
            assert type(value) is bool
        elif expected is float:
            assert isinstance(value, (int, float))
        else:
            assert isinstance(value, str)


def test_example_functions_always_valid() -> None:
    definitions = load_json("data/input/functions_definition.json")
    pipeline = _make_pipeline(definitions)
    prompts = [Prompt(prompt=text) for text in [
        "What is the sum of 2 and 3?",
        "Greet shrek",
        "Reverse the string 'hello'",
        "Multiply 6 and 7",
        "Enable the flag",
        "",  # empty prompt edge case
    ]]
    results = pipeline.run(prompts)
    assert len(results) == len(prompts)
    for result in results:
        _assert_valid(json.loads(result.model_dump_json()), definitions)


def test_output_is_json_serialisable() -> None:
    definitions = load_json("data/input/functions_definition.json")
    pipeline = _make_pipeline(definitions)
    results = pipeline.run([Prompt(prompt="Greet john")])
    payload = [r.model_dump() for r in results]
    # Must round-trip through JSON without error.
    assert json.loads(json.dumps(payload)) == payload


def test_unknown_type_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_function_definitions([{
            "name": "fn_bad",
            "parameters": {"x": {"type": "complex"}},
        }])


def test_missing_file_raises_input_error() -> None:
    with pytest.raises(InputError):
        load_json("data/input/does_not_exist.json")


def test_single_parameterless_function() -> None:
    definitions: List[Dict[str, Any]] = [{
        "name": "fn_ping",
        "description": "Ping.",
        "parameters": {},
    }]
    pipeline = _make_pipeline(definitions)
    results = pipeline.run([Prompt(prompt="ping it")])
    record = json.loads(results[0].model_dump_json())
    assert record["name"] == "fn_ping"
    assert record["parameters"] == {}
