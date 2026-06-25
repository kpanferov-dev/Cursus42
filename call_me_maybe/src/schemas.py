"""Pydantic models for input and output validation.

These mirror the JSON files described in the project subject:

* ``functions_definition.json`` -- list of :class:`FunctionDefinition`
* ``function_calling_tests.json`` -- list of :class:`TestPrompt`
* ``function_calling_results.json`` -- list of :class:`FunctionCall`

We support the four scalar JSON types named in the subject
(``number``, ``integer``, ``string``, ``boolean``) plus ``object`` and
``array`` for nested arguments (bonus feature).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# All JSON types our constraint machine understands. ``object`` and
# ``array`` are bonus types -- the subject only requires the scalars.
JsonType = Literal["number", "integer", "string", "boolean", "object", "array"]


class ParamSpec(BaseModel):
    """Specification for a single function parameter.

    For ``object`` types, ``properties`` lists the nested keys.
    For ``array`` types, ``items`` describes the element type.
    """

    model_config = ConfigDict(extra="allow")

    type: JsonType
    properties: dict[str, "ParamSpec"] | None = None
    items: "ParamSpec | None" = None


# Pydantic v2 needs this to resolve the self-reference above.
ParamSpec.model_rebuild()


class FunctionDefinition(BaseModel):
    """A function the LLM is allowed to call."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: str = ""
    parameters: dict[str, ParamSpec] = Field(default_factory=dict)
    returns: dict[str, Any] = Field(default_factory=dict)


class TestPrompt(BaseModel):
    """A single natural-language prompt from the test file."""

    prompt: str


class FunctionCall(BaseModel):
    """One row of the output file."""

    prompt: str
    name: str
    parameters: dict[str, Any]
