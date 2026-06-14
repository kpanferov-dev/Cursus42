"""Command-line interface for the function-calling tool.

Run with::

    uv run python -m src [--functions_definition FILE] [--input FILE]
                         [--output FILE] [--model NAME]

It loads the function definitions and prompts, builds the constrained
decoder around the model exposed by ``llm_sdk``, processes every prompt
and writes the results. Every foreseeable error is reported clearly and
turns into a non-zero exit code instead of a crash.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, cast

from src import config
from src.decoder import ConstrainedDecoder, SupportsLLM
from src.io_utils import InputError, dump_json, load_json
from src.models import (
    AppConfig,
    FunctionCall,
    parse_function_definitions,
    parse_prompts,
)
from src.pipeline import FunctionCallingPipeline
from src.vocab import Vocabulary


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Translate natural-language prompts into function "
                    "calls using constrained decoding.")
    parser.add_argument("--functions_definition",
                        default=config.DEFAULT_FUNCTIONS_FILE,
                        help="path to the function-definition JSON file")
    parser.add_argument("--input", default=config.DEFAULT_INPUT_FILE,
                        help="path to the prompts JSON file")
    parser.add_argument("--output", default=config.DEFAULT_OUTPUT_FILE,
                        help="path to write the results JSON file")
    parser.add_argument("--model", default=config.DEFAULT_MODEL,
                        help="model identifier to load through llm_sdk")
    return parser


def load_model(model_name: str) -> ConstrainedDecoder:
    """Instantiate the SDK model and wrap it in a decoder.

    Args:
        model_name: The model identifier to load.

    Returns:
        A ready-to-use :class:`~src.decoder.ConstrainedDecoder`.

    Raises:
        InputError: If the SDK or model cannot be loaded.
    """
    try:
        from llm_sdk import Small_LLM_Model
    except ImportError as error:
        raise InputError(
            "could not import llm_sdk; copy the provided package next to "
            "the src directory") from error
    try:
        model: SupportsLLM = _instantiate(Small_LLM_Model, model_name)
        vocabulary = Vocabulary.from_file(model.get_path_to_vocab_file())
    except InputError:
        raise
    except Exception as error:  # noqa: BLE001 - surface any SDK failure
        raise InputError(f"failed to initialise the model: {error}") from error
    return ConstrainedDecoder(model, vocabulary)


def _instantiate(model_class: type, model_name: str) -> SupportsLLM:
    """Construct the SDK model, tolerating a couple of signatures."""
    try:
        instance = model_class(model_name)
    except TypeError:
        instance = model_class()
    return cast(SupportsLLM, instance)


def run(arguments: AppConfig) -> int:
    """Execute the pipeline described by ``arguments``.

    Args:
        arguments: The validated runtime configuration.

    Returns:
        ``0`` on success, ``1`` on a handled error.
    """
    try:
        functions = parse_function_definitions(
            load_json(arguments.functions_file))
        prompts = parse_prompts(load_json(arguments.input_file))
        decoder = load_model(arguments.model_name)
    except (InputError, ValueError) as error:
        sys.stderr.write(f"error: {error}\n")
        return 1
    pipeline = FunctionCallingPipeline(functions, decoder)
    results: List[FunctionCall] = pipeline.run(prompts)
    payload = [result.model_dump() for result in results]
    try:
        dump_json(arguments.output_file, payload)
    except InputError as error:
        sys.stderr.write(f"error: {error}\n")
        return 1
    sys.stderr.write(
        f"wrote {len(results)} function call(s) to "
        f"{arguments.output_file}\n")
    return 0


def main(argv: List[str] | None = None) -> int:
    """Parse arguments and run the program.

    Args:
        argv: Optional explicit argument list (used in tests).

    Returns:
        The process exit code.
    """
    namespace = build_arg_parser().parse_args(argv)
    arguments = AppConfig(
        functions_file=namespace.functions_definition,
        input_file=namespace.input,
        output_file=namespace.output,
        model_name=namespace.model,
    )
    return run(arguments)
