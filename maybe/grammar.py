"""The grammar guide that powers constrained decoding.

Rather than hoping the model emits valid JSON, we *force* the structure.
The output object ``{"name": "...", "parameters": {...}}`` is described as
a small program of two instruction kinds:

* :class:`Literal` - a fixed run of characters that must appear verbatim
  (the braces, quotes, keys and separators);
* :class:`Slot` - a model-driven value whose characters are restricted by
  a :class:`Matcher` to a function name, a number, a string or a boolean.

A :class:`SchemaGuide` walks this program one character at a time. The
decoder uses it to ask, for any candidate token, "does appending this
token's text keep us on a valid path?" - and only those tokens are kept.
Because the literals are fixed and every value is constrained to its
declared type, the result is always valid JSON that matches the schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

from src.config import (
    TYPE_BOOLEAN,
    TYPE_INTEGER,
    TYPE_STRING,
)
from src.models import FunctionDefinition, JsonValue


class Matcher:
    """Base class for the value constraint inside a :class:`Slot`."""

    def allows(self, text: str, char: str) -> bool:
        """Return whether ``text + char`` is a valid value prefix."""
        raise NotImplementedError

    def is_complete(self, text: str) -> bool:
        """Return whether ``text`` is already a complete value."""
        raise NotImplementedError

    def to_value(self, text: str) -> JsonValue:
        """Convert finished slot text into a typed Python value."""
        raise NotImplementedError


class ChoiceMatcher(Matcher):
    """Constrain a value to one of a fixed set of words.

    Used both for selecting a function name and for boolean literals.
    """

    def __init__(self, choices: Sequence[str], as_bool: bool = False) -> None:
        """Initialise the matcher.

        Args:
            choices: The exact strings that are accepted.
            as_bool: When ``True`` the value is converted to a ``bool``.
        """
        self._choices = list(choices)
        self._as_bool = as_bool

    def allows(self, text: str, char: str) -> bool:
        candidate = text + char
        return any(choice.startswith(candidate) for choice in self._choices)

    def is_complete(self, text: str) -> bool:
        return text in self._choices

    def to_value(self, text: str) -> JsonValue:
        if self._as_bool:
            return text == "true"
        return text


class NumberMatcher(Matcher):
    """Constrain a value to a JSON number, optionally integer-only."""

    def __init__(self, integer: bool) -> None:
        """Initialise the matcher.

        Args:
            integer: When ``True`` a fractional part is not allowed.
        """
        self._integer = integer

    def allows(self, text: str, char: str) -> bool:
        return self._is_prefix(text + char)

    def is_complete(self, text: str) -> bool:
        return bool(text) and text[-1].isdigit()

    def to_value(self, text: str) -> JsonValue:
        if self._integer:
            return int(text)
        return float(text)

    def _is_prefix(self, candidate: str) -> bool:
        """Return whether ``candidate`` is a valid numeric prefix."""
        index = 0
        length = len(candidate)
        if index < length and candidate[index] == "-":
            index += 1
        seen_digit = False
        while index < length and candidate[index].isdigit():
            index += 1
            seen_digit = True
        if (not self._integer and index < length
                and candidate[index] == "."):
            if not seen_digit:
                return False
            index += 1
            while index < length and candidate[index].isdigit():
                index += 1
        return index == length and candidate != ""


class StringMatcher(Matcher):
    """Constrain a value to the inside of a JSON string."""

    def allows(self, text: str, char: str) -> bool:
        if char in ('"', "\\"):
            return False
        return ord(char) >= 0x20

    def is_complete(self, text: str) -> bool:
        return True

    def to_value(self, text: str) -> JsonValue:
        return text


@dataclass
class Literal:
    """A fixed string that must be matched verbatim."""

    text: str


@dataclass
class Slot:
    """A model-driven value constrained by a :class:`Matcher`."""

    matcher: Matcher
    name: Optional[str] = None


Instruction = Union[Literal, Slot]


@dataclass
class GuideState:
    """Immutable position of the guide within its program.

    Attributes:
        index: Index of the current instruction.
        literal_offset: Offset within the current literal.
        slot_text: Text accumulated for the current slot.
    """

    index: int
    literal_offset: int
    slot_text: str


class SchemaGuide:
    """Walk a program of literals and slots, validating characters."""

    def __init__(self, program: Sequence[Instruction]) -> None:
        """Initialise the guide with a program.

        Args:
            program: The ordered instructions describing the output.
        """
        self._program = list(program)

    @property
    def program(self) -> List[Instruction]:
        """Return the program instructions."""
        return self._program

    def start_state(self) -> GuideState:
        """Return the state positioned at the start of the program."""
        return GuideState(index=0, literal_offset=0, slot_text="")

    def is_complete(self, state: GuideState) -> bool:
        """Return whether the program has been fully consumed."""
        return state.index >= len(self._program)

    def consume_char(
        self, state: GuideState, char: str
    ) -> Optional[GuideState]:
        """Advance the state by one character.

        Args:
            state: The current guide state.
            char: The character to consume.

        Returns:
            The next state, or ``None`` if ``char`` is not allowed.
        """
        index = state.index
        literal_offset = state.literal_offset
        slot_text = state.slot_text
        while index < len(self._program):
            instruction = self._program[index]
            if isinstance(instruction, Literal):
                if literal_offset >= len(instruction.text):
                    index += 1
                    literal_offset = 0
                    continue
                if char != instruction.text[literal_offset]:
                    return None
                literal_offset += 1
                if literal_offset == len(instruction.text):
                    index += 1
                    literal_offset = 0
                return GuideState(index, literal_offset, "")
            if instruction.matcher.allows(slot_text, char):
                return GuideState(index, 0, slot_text + char)
            if instruction.matcher.is_complete(slot_text):
                index += 1
                literal_offset = 0
                slot_text = ""
                continue
            return None
        return None

    def consume_token(
        self, state: GuideState, surface: str
    ) -> Optional[GuideState]:
        """Advance the state by a whole token's surface text.

        Args:
            state: The current guide state.
            surface: The text contributed by a candidate token.

        Returns:
            The resulting state, or ``None`` if the token is not allowed.
        """
        if not surface:
            return None
        current: Optional[GuideState] = state
        for char in surface:
            assert current is not None
            current = self.consume_char(current, char)
            if current is None:
                return None
        return current

    def first_char_allowed(self, state: GuideState, char: str) -> bool:
        """Quickly test whether ``char`` could be the next character."""
        index = state.index
        literal_offset = state.literal_offset
        while index < len(self._program):
            instruction = self._program[index]
            if isinstance(instruction, Literal):
                if literal_offset >= len(instruction.text):
                    index += 1
                    literal_offset = 0
                    continue
                return char == instruction.text[literal_offset]
            if instruction.matcher.allows(state.slot_text, char):
                return True
            if instruction.matcher.is_complete(state.slot_text):
                return self._next_literal_char(index + 1) == char
            return False
        return False

    def _next_literal_char(self, index: int) -> Optional[str]:
        """Return the first character expected at instruction ``index``."""
        while index < len(self._program):
            instruction = self._program[index]
            if isinstance(instruction, Literal):
                if instruction.text:
                    return instruction.text[0]
                index += 1
                continue
            return None
        return None


def build_name_program(names: Sequence[str]) -> SchemaGuide:
    """Build the guide that selects a function name.

    Args:
        names: The available function names.

    Returns:
        A guide for ``{"name": "<one of names>"``.
    """
    program: List[Instruction] = [
        Literal('{"name": "'),
        Slot(ChoiceMatcher(names), name="name"),
        Literal('"'),
    ]
    return SchemaGuide(program)


def build_parameters_program(
    function: FunctionDefinition,
) -> Tuple[SchemaGuide, List[Tuple[str, Matcher]]]:
    """Build the guide that fills in a function's parameters.

    Args:
        function: The chosen function definition.

    Returns:
        A tuple of the guide and the ordered ``(name, matcher)`` pairs so
        the caller can convert each captured slot to a typed value.
    """
    program: List[Instruction] = [Literal(', "parameters": {')]
    slots: List[Tuple[str, Matcher]] = []
    items = list(function.parameters.items())
    for position, (param_name, spec) in enumerate(items):
        matcher = _matcher_for(spec.type)
        slots.append((param_name, matcher))
        program.append(Literal(_key_literal(param_name, spec.type)))
        program.append(Slot(matcher, name=param_name))
        program.append(Literal(_value_suffix(spec.type)))
        if position != len(items) - 1:
            program.append(Literal(", "))
    program.append(Literal("}}"))
    return SchemaGuide(program), slots


def _matcher_for(type_name: str) -> Matcher:
    """Return the matcher enforcing a declared JSON type."""
    if type_name == TYPE_STRING:
        return StringMatcher()
    if type_name == TYPE_BOOLEAN:
        return ChoiceMatcher(["true", "false"], as_bool=True)
    return NumberMatcher(integer=type_name == TYPE_INTEGER)


def _key_literal(param_name: str, type_name: str) -> str:
    """Return the fixed ``"key": `` prefix, opening a quote for strings."""
    prefix = f'"{param_name}": '
    if type_name == TYPE_STRING:
        return prefix + '"'
    return prefix


def _value_suffix(type_name: str) -> str:
    """Return the fixed text that closes a value (quote for strings)."""
    if type_name == TYPE_STRING:
        return '"'
    return ""


def extract_slot_values(
    guide: SchemaGuide, surface: str
) -> List[str]:
    """Replay ``surface`` through ``guide`` and capture each slot's text.

    Args:
        guide: The guide whose program produced ``surface``.
        surface: The full generated text for that program.

    Returns:
        The captured text of each slot, in program order.

    Raises:
        ValueError: If ``surface`` does not conform to the program.
    """
    values: List[str] = []
    index = 0
    literal_offset = 0
    slot_text = ""
    cursor = 0
    program = guide.program
    while index < len(program):
        instruction = program[index]
        if isinstance(instruction, Literal):
            if literal_offset >= len(instruction.text):
                index += 1
                literal_offset = 0
                continue
            if cursor >= len(surface):
                raise ValueError("generated text ended inside a literal")
            if surface[cursor] != instruction.text[literal_offset]:
                raise ValueError("generated text diverged from the schema")
            cursor += 1
            literal_offset += 1
            if literal_offset == len(instruction.text):
                index += 1
                literal_offset = 0
            continue
        if cursor < len(surface) and instruction.matcher.allows(
                slot_text, surface[cursor]):
            slot_text += surface[cursor]
            cursor += 1
            continue
        if instruction.matcher.is_complete(slot_text):
            values.append(slot_text)
            index += 1
            literal_offset = 0
            slot_text = ""
            continue
        raise ValueError("generated text did not complete a slot")
    return values
