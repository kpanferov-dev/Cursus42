"""Tests for the constraint state machine."""
from __future__ import annotations

import json
from typing import List

import pytest

from src.constraints import (
    ConstraintMachine,
    EnumSeg,
    LiteralSeg,
    ValueSeg,
    _value_can_extend,
    _value_is_complete,
)
from src.schemas import FunctionDefinition, ParamSpec
from src.vocabulary import Vocabulary


# ---------------------------------------------------------------------------
# Value DFA tests
# ---------------------------------------------------------------------------


class TestNumberDfa:
    """Tests for the ``number`` JSON type DFA."""

    def test_accepts_simple_int(self) -> None:
        seg = ValueSeg(json_type="number")
        for ch in "42":
            assert _value_can_extend(seg, ch)
            seg.buf += ch
        assert _value_is_complete(seg)

    def test_accepts_decimal(self) -> None:
        seg = ValueSeg(json_type="number")
        for ch in "3.14":
            assert _value_can_extend(seg, ch)
            seg.buf += ch
        assert _value_is_complete(seg)

    def test_accepts_negative(self) -> None:
        seg = ValueSeg(json_type="number")
        for ch in "-7":
            assert _value_can_extend(seg, ch)
            seg.buf += ch
        assert _value_is_complete(seg)

    def test_rejects_leading_zero(self) -> None:
        seg = ValueSeg(json_type="number", buf="0")
        assert not _value_can_extend(seg, "1")

    def test_rejects_double_dot(self) -> None:
        seg = ValueSeg(json_type="number", buf="3.1")
        assert not _value_can_extend(seg, ".")


class TestIntegerDfa:
    """Tests for the ``integer`` JSON type DFA."""

    def test_rejects_decimal(self) -> None:
        seg = ValueSeg(json_type="integer", buf="3")
        assert not _value_can_extend(seg, ".")

    def test_zero_is_complete(self) -> None:
        seg = ValueSeg(json_type="integer", buf="0")
        assert _value_is_complete(seg)


class TestBooleanDfa:
    """Tests for the ``boolean`` JSON type DFA."""

    def test_partial_true(self) -> None:
        seg = ValueSeg(json_type="boolean", buf="tr")
        assert _value_can_extend(seg, "u")
        assert not _value_is_complete(seg)

    def test_complete_false(self) -> None:
        seg = ValueSeg(json_type="boolean", buf="false")
        assert _value_is_complete(seg)


class TestStringDfa:
    """Tests for the ``string`` JSON type DFA."""

    def test_accepts_any_printable(self) -> None:
        seg = ValueSeg(json_type="string")
        assert _value_can_extend(seg, "h")

    def test_rejects_unescaped_quote(self) -> None:
        seg = ValueSeg(json_type="string", buf="hi")
        assert not _value_can_extend(seg, '"')

    def test_rejects_control_chars(self) -> None:
        seg = ValueSeg(json_type="string")
        assert not _value_can_extend(seg, "\n")


# ---------------------------------------------------------------------------
# Enum lock-in tests
# ---------------------------------------------------------------------------


class TestEnumLockIn:
    """Verify the EnumSeg locks in at the right time."""

    def test_locks_when_no_longer_prefix(self, vocab: Vocabulary) -> None:
        """``fn_greet`` should lock in once typed, because no other choice
        extends it."""
        functions = [
            FunctionDefinition(
                name="fn_greet",
                parameters={"name": ParamSpec(type="string")},
            ),
            FunctionDefinition(
                name="fn_add",
                parameters={"a": ParamSpec(type="number")},
            ),
        ]
        m = ConstraintMachine(functions=functions, vocab=vocab)
        # drive past opening literal
        for ch in '{"name": "':
            tid = vocab.id_of(ch)
            if tid is not None:
                m.advance(tid)
        # type "fn_greet"
        for ch in "fn_greet":
            tid = vocab.id_of(ch)
            assert tid is not None, f"vocab missing {ch}"
            m.advance(tid)
        assert m.chosen_function is not None
        assert m.chosen_function.name == "fn_greet"

    def test_does_not_lock_too_early(self, vocab: Vocabulary) -> None:
        """``fn_add`` should NOT lock when ``fn_add_numbers`` is also a choice."""
        functions = [
            FunctionDefinition(
                name="fn_add",
                parameters={},
            ),
            FunctionDefinition(
                name="fn_add_numbers",
                parameters={"a": ParamSpec(type="number")},
            ),
        ]
        m = ConstraintMachine(functions=functions, vocab=vocab)
        for ch in '{"name": "':
            tid = vocab.id_of(ch)
            if tid is not None:
                m.advance(tid)
        for ch in "fn_add":
            tid = vocab.id_of(ch)
            assert tid is not None
            m.advance(tid)
        # Should NOT have locked yet -- _numbers is still reachable.
        assert m.chosen_function is None


# ---------------------------------------------------------------------------
# End-to-end with stub model
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Run the full machine with a uniform-logit stub."""

    def _run(
        self,
        m: ConstraintMachine,
        vocab: Vocabulary,
        max_steps: int = 500,
    ) -> str:
        """Drive ``m`` to completion by picking the longest allowed token."""
        for _ in range(max_steps):
            if m.finished:
                break
            allowed = m.allowed_token_ids()
            if not allowed:
                break
            # Prefer longer tokens -- stresses multi-char boundary handling.
            best = max(
                allowed, key=lambda t: (len(vocab.text_of(t)), -t)
            )
            m.advance(best)
        return m.rendered()

    def test_produces_valid_json(
        self,
        vocab: Vocabulary,
        functions: List[FunctionDefinition],
    ) -> None:
        m = ConstraintMachine(functions=functions, vocab=vocab)
        out = self._run(m, vocab)
        parsed = json.loads(out)
        assert "name" in parsed
        assert "parameters" in parsed
        assert parsed["name"] in {f.name for f in functions}

    def test_parameters_match_schema(
        self,
        vocab: Vocabulary,
        functions: List[FunctionDefinition],
    ) -> None:
        m = ConstraintMachine(functions=functions, vocab=vocab)
        out = self._run(m, vocab)
        parsed = json.loads(out)
        chosen = next(f for f in functions if f.name == parsed["name"])
        # Every required key is present.
        for key in chosen.parameters:
            assert key in parsed["parameters"], (
                f"missing key {key} in {parsed}"
            )

    def test_nested_object_parameter(self, vocab: Vocabulary) -> None:
        """Bonus: nested object types must produce nested JSON."""
        functions = [
            FunctionDefinition(
                name="fn_greet",
                parameters={
                    "person": ParamSpec(
                        type="object",
                        properties={
                            "name": ParamSpec(type="string"),
                            "age": ParamSpec(type="integer"),
                        },
                    ),
                },
            ),
        ]
        m = ConstraintMachine(functions=functions, vocab=vocab)
        out = self._run(m, vocab)
        parsed = json.loads(out)
        assert parsed["name"] == "fn_greet"
        assert isinstance(parsed["parameters"]["person"], dict)
        assert "name" in parsed["parameters"]["person"]
        assert "age" in parsed["parameters"]["person"]
