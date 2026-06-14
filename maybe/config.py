"""Project-wide configuration constants for the function-calling tool.

This module centralises the values that the rest of the package relies
on: the default model name, the default input/output locations, the set
of JSON types the constrained decoder understands, and a few safety
limits used while generating tokens.
"""

from __future__ import annotations

from typing import Final, FrozenSet

# Default model. Any model exposed through the ``llm_sdk`` interface works;
# the project is developed and validated against Qwen/Qwen3-0.6B.
DEFAULT_MODEL: Final[str] = "Qwen/Qwen3-0.6B"

# Default file locations (relative to the working directory).
DEFAULT_FUNCTIONS_FILE: Final[str] = "data/input/functions_definition.json"
DEFAULT_INPUT_FILE: Final[str] = "data/input/function_calling_tests.json"
DEFAULT_OUTPUT_FILE: Final[str] = "data/output/function_calling_results.json"

# JSON types accepted in a function definition. ``integer`` is treated as a
# whole number; ``number`` allows an optional fractional part.
TYPE_NUMBER: Final[str] = "number"
TYPE_INTEGER: Final[str] = "integer"
TYPE_STRING: Final[str] = "string"
TYPE_BOOLEAN: Final[str] = "boolean"

SUPPORTED_TYPES: Final[FrozenSet[str]] = frozenset(
    {TYPE_NUMBER, TYPE_INTEGER, TYPE_STRING, TYPE_BOOLEAN})

# Safety limits while generating a single value or a whole call, expressed
# in generated tokens. They prevent an unbounded loop if a model keeps
# emitting digits or string characters forever.
MAX_VALUE_TOKENS: Final[int] = 64
MAX_CALL_TOKENS: Final[int] = 512

# Characters that may never appear unescaped inside a generated JSON string.
FORBIDDEN_STRING_CHARS: Final[FrozenSet[str]] = frozenset(
    {'"', "\\"})
