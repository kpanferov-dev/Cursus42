"""Prompt construction for the function-calling task.

Constrained decoding guarantees the *shape* of the answer, but a clear
prompt still helps a small model pick the right function and arguments.
This module renders the available functions and the user request into a
Qwen-style chat prompt that ends exactly where the JSON object should
begin.
"""

from __future__ import annotations

from typing import List

from src.models import FunctionDefinition

_SYSTEM_INSTRUCTIONS = (
    "You translate a user request into a single function call. "
    "Choose exactly one function from the list and provide its arguments "
    "with the correct types. Respond only with a JSON object of the form "
    '{"name": <function>, "parameters": {<arguments>}}.'
)


class PromptBuilder:
    """Render chat prompts describing the available functions."""

    def __init__(self, functions: List[FunctionDefinition]) -> None:
        """Initialise with the available functions.

        Args:
            functions: The function definitions to expose to the model.
        """
        self._functions = functions
        self._catalogue = self._render_catalogue(functions)

    def build(self, user_prompt: str) -> str:
        """Return the full chat prompt for a single user request.

        Args:
            user_prompt: The natural-language request.

        Returns:
            The prompt text to encode and feed to the model.
        """
        return (
            "<|im_start|>system\n"
            f"{_SYSTEM_INSTRUCTIONS}\n\n"
            "Available functions:\n"
            f"{self._catalogue}\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"{user_prompt}\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

    @staticmethod
    def _render_catalogue(functions: List[FunctionDefinition]) -> str:
        """Render a compact textual description of every function."""
        lines: List[str] = []
        for function in functions:
            params = ", ".join(
                f"{name}: {spec.type}"
                for name, spec in function.parameters.items())
            description = function.description or "no description"
            lines.append(
                f"- {function.name}({params}) -> {description}")
        return "\n".join(lines)
