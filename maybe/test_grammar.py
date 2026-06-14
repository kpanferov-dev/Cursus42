"""Unit tests for the grammar matchers and the schema guide."""

from __future__ import annotations

from src.grammar import (
    ChoiceMatcher,
    GuideState,
    NumberMatcher,
    SchemaGuide,
    StringMatcher,
    build_name_program,
    build_parameters_program,
    extract_slot_values,
)
from src.models import FunctionDefinition


def _feed(guide: SchemaGuide, text: str) -> GuideState:
    """Feed a whole string through a guide, returning the final state."""
    state = guide.start_state()
    for char in text:
        nxt = guide.consume_char(state, char)
        assert nxt is not None, f"rejected at {char!r} in {text!r}"
        state = nxt
    return state


def test_number_matcher_accepts_valid_prefixes() -> None:
    matcher = NumberMatcher(integer=False)
    assert matcher.allows("", "-")
    assert matcher.allows("-", "4")
    assert matcher.allows("4", ".")
    assert matcher.allows("4.", "2")
    assert not matcher.allows("", ".")
    assert matcher.is_complete("42")
    assert matcher.is_complete("-3.5")
    assert not matcher.is_complete("4.")
    assert matcher.to_value("42") == 42.0


def test_integer_matcher_rejects_dot() -> None:
    matcher = NumberMatcher(integer=True)
    assert matcher.allows("4", "2")
    assert not matcher.allows("4", ".")
    assert matcher.to_value("-17") == -17


def test_string_matcher_blocks_quote_and_control() -> None:
    matcher = StringMatcher()
    assert matcher.allows("a", "b")
    assert not matcher.allows("a", '"')
    assert not matcher.allows("a", "\\")
    assert not matcher.allows("a", "\n")
    assert matcher.is_complete("")


def test_choice_matcher_boolean() -> None:
    matcher = ChoiceMatcher(["true", "false"], as_bool=True)
    assert matcher.allows("", "t")
    assert matcher.allows("tru", "e")
    assert not matcher.allows("t", "x")
    assert matcher.is_complete("true")
    assert matcher.to_value("true") is True
    assert matcher.to_value("false") is False


def test_name_program_extracts_choice() -> None:
    guide = build_name_program(["fn_add", "fn_greet"])
    surface = '{"name": "fn_greet"'
    state = _feed(guide, surface)
    assert guide.is_complete(state)
    assert extract_slot_values(guide, surface) == ["fn_greet"]


def test_parameters_program_roundtrip() -> None:
    function = FunctionDefinition.model_validate({
        "name": "fn_add_numbers",
        "parameters": {"a": {"type": "number"}, "b": {"type": "number"}},
    })
    guide, slots = build_parameters_program(function)
    surface = ', "parameters": {"a": 40, "b": 2}}'
    state = _feed(guide, surface)
    assert guide.is_complete(state)
    values = extract_slot_values(guide, surface)
    assert values == ["40", "2"]
    assert [name for name, _ in slots] == ["a", "b"]


def test_string_parameter_with_special_chars() -> None:
    function = FunctionDefinition.model_validate({
        "name": "fn_greet",
        "parameters": {"name": {"type": "string"}},
    })
    guide, _ = build_parameters_program(function)
    surface = ', "parameters": {"name": "j@ck!"}}'
    state = _feed(guide, surface)
    assert guide.is_complete(state)
    assert extract_slot_values(guide, surface) == ["j@ck!"]
