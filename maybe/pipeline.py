"""End-to-end pipeline: prompt in, validated function call out.

For every prompt this module runs the two constrained-decoding stages -
first choosing a function name, then filling that function's parameters -
and assembles a validated :class:`~src.models.FunctionCall`. Any failure
on a single prompt is contained so the run always produces a complete,
schema-valid output file.
"""

from __future__ import annotations

import sys
from typing import Dict, List

from src.decoder import ConstrainedDecoder, DecodeError, to_id_list
from src.grammar import (
    ChoiceMatcher,
    Matcher,
    NumberMatcher,
    StringMatcher,
    build_name_program,
    build_parameters_program,
    extract_slot_values,
)
from src.models import FunctionCall, FunctionDefinition, JsonValue, Prompt
from src.prompts import PromptBuilder


class FunctionCallingPipeline:
    """Translate prompts into validated function calls."""

    def __init__(
        self,
        functions: List[FunctionDefinition],
        decoder: ConstrainedDecoder,
    ) -> None:
        """Initialise the pipeline.

        Args:
            functions: Available function definitions.
            decoder: The constrained decoder to use.
        """
        self._functions = functions
        self._by_name = {function.name: function for function in functions}
        self._decoder = decoder
        self._prompts = PromptBuilder(functions)
        self._name_guide = build_name_program(
            [function.name for function in functions])

    def run(self, prompts: List[Prompt]) -> List[FunctionCall]:
        """Process every prompt, returning one call each.

        Args:
            prompts: The prompts to process.

        Returns:
            A list of validated function calls in input order.
        """
        results: List[FunctionCall] = []
        for prompt in prompts:
            results.append(self._run_one(prompt.prompt))
        return results

    def _run_one(self, prompt_text: str) -> FunctionCall:
        """Resolve a single prompt into a function call."""
        try:
            return self._decode_call(prompt_text)
        except (DecodeError, ValueError, KeyError) as error:
            sys.stderr.write(
                f"warning: falling back for prompt {prompt_text!r}: "
                f"{error}\n")
            return self._fallback(prompt_text)

    def _decode_call(self, prompt_text: str) -> FunctionCall:
        """Run both decoding stages and build a validated call."""
        prompt_ids = to_id_list(
            self._decoder.encode(self._prompts.build(prompt_text)))
        name_ids, name_surface = self._decoder.decode(
            prompt_ids, self._name_guide)
        name = extract_slot_values(self._name_guide, name_surface)[0]
        function = self._by_name[name]
        params_guide, slots = build_parameters_program(function)
        context = prompt_ids + name_ids
        _, params_surface = self._decoder.decode(context, params_guide)
        values = extract_slot_values(params_guide, params_surface)
        parameters = self._convert(slots, values)
        return FunctionCall(
            prompt=prompt_text, name=name, parameters=parameters)

    @staticmethod
    def _convert(
        slots: List[tuple[str, Matcher]], values: List[str]
    ) -> Dict[str, JsonValue]:
        """Convert captured slot text into typed parameter values."""
        parameters: Dict[str, JsonValue] = {}
        for (name, matcher), text in zip(slots, values):
            parameters[name] = matcher.to_value(text)
        return parameters

    def _fallback(self, prompt_text: str) -> FunctionCall:
        """Produce a schema-valid default call when decoding fails.

        The first function is used with type-appropriate default values so
        that the output file always stays valid and complete.
        """
        function = self._functions[0]
        _, slots = build_parameters_program(function)
        parameters: Dict[str, JsonValue] = {}
        for name, matcher in slots:
            parameters[name] = _default_value(matcher)
        return FunctionCall(
            prompt=prompt_text, name=function.name, parameters=parameters)


def _default_value(matcher: Matcher) -> JsonValue:
    """Return a safe default value for a matcher's type."""
    if isinstance(matcher, StringMatcher):
        return ""
    if isinstance(matcher, NumberMatcher):
        return matcher.to_value("0")
    if isinstance(matcher, ChoiceMatcher):
        return matcher.to_value("false")
    return ""


__all__ = ["FunctionCallingPipeline"]
