"""Pydantic models describing every structured value in the project.

All data that crosses a boundary (file contents, function schema, the
final result records) is represented by a pydantic model so that it is
validated on construction. Invalid input therefore fails fast with a
clear message instead of producing a malformed call later on.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.config import SUPPORTED_TYPES

# A concrete JSON value that a generated argument may take.
JsonValue = Union[int, float, str, bool]


class TypeSpec(BaseModel):
    """The declared type of a parameter or of a function's return value.

    Attributes:
        type: One of the supported JSON type names.
    """

    model_config = ConfigDict(extra="allow")

    type: str

    @field_validator("type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        """Ensure the declared type is one the decoder can enforce."""
        if value not in SUPPORTED_TYPES:
            supported = ", ".join(sorted(SUPPORTED_TYPES))
            raise ValueError(
                f"unsupported type '{value}' (supported: {supported})")
        return value


class FunctionDefinition(BaseModel):
    """A single callable function the model may choose.

    Attributes:
        name: Unique function name.
        description: Human-readable description used in the prompt.
        parameters: Ordered mapping of argument name to its type.
        returns: Optional declared return type.
    """

    name: str
    description: str = ""
    parameters: Dict[str, TypeSpec] = Field(default_factory=dict)
    returns: Optional[TypeSpec] = None

    @field_validator("name")
    @classmethod
    def _non_empty_name(cls, value: str) -> str:
        """Reject empty function names, which could not be selected."""
        if not value:
            raise ValueError("function name must not be empty")
        return value


class Prompt(BaseModel):
    """A single natural-language request to be turned into a call.

    Attributes:
        prompt: The raw user request.
    """

    prompt: str


class FunctionCall(BaseModel):
    """A resolved function call ready to be written to the output file.

    Attributes:
        prompt: The original request.
        name: The chosen function name.
        parameters: The extracted, type-correct arguments.
    """

    prompt: str
    name: str
    parameters: Dict[str, JsonValue]


class AppConfig(BaseModel):
    """Runtime configuration assembled from the command line.

    Attributes:
        functions_file: Path to the function-definition file.
        input_file: Path to the prompts file.
        output_file: Path where results are written.
        model_name: Identifier of the model to load.
    """

    functions_file: str
    input_file: str
    output_file: str
    model_name: str


def parse_function_definitions(
    raw: object,
) -> List[FunctionDefinition]:
    """Validate raw JSON into a list of :class:`FunctionDefinition`.

    Args:
        raw: The object decoded from the function-definition file.

    Returns:
        The validated function definitions, preserving file order.

    Raises:
        ValueError: If the structure is not a list of valid definitions.
    """
    if not isinstance(raw, list):
        raise ValueError("function definitions must be a JSON array")
    definitions: List[FunctionDefinition] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"function #{index} must be a JSON object")
        definitions.append(FunctionDefinition.model_validate(item))
    if not definitions:
        raise ValueError("at least one function definition is required")
    return definitions


def parse_prompts(raw: object) -> List[Prompt]:
    """Validate raw JSON into a list of :class:`Prompt`.

    Args:
        raw: The object decoded from the prompts file.

    Returns:
        The validated prompts, preserving file order.

    Raises:
        ValueError: If the structure is not a list of valid prompts.
    """
    if not isinstance(raw, list):
        raise ValueError("prompts must be a JSON array")
    prompts: List[Prompt] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"prompt #{index} must be a JSON object")
        prompts.append(Prompt.model_validate(item))
    return prompts
