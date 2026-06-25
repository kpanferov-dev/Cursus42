"""Entry point: ``uv run python -m src``.

CLI:

    --functions_definition  Path to the function-definitions JSON.
    --input                 Path to the prompts JSON.
    --output                Path to write the results.
    --model                 HuggingFace model id (bonus: pluggable).
    --visualize             Print a token-by-token trace (bonus).
    --max_new_tokens        Hard cap per prompt.

All errors are surfaced as ``[error] <message>`` to stderr with a
non-zero exit code; the program never raises a stack trace at the
user.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generator import generate_call
from .io_utils import (
    InputError,
    load_function_definitions,
    load_test_prompts,
    write_output,
)
from .tokenizer import Tokenizer
from .vocabulary import load_vocabulary

DEFAULT_FUNCTIONS = Path("data/input/functions_definition.json")
DEFAULT_INPUT = Path("data/input/function_calling_tests.json")
DEFAULT_OUTPUT = Path("data/output/function_calling_results.json")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the CLI per the subject."""
    p = argparse.ArgumentParser(
        prog="call_me_maybe",
        description="Function calling via constrained decoding.",
    )
    p.add_argument(
        "--functions_definition",
        type=Path,
        default=DEFAULT_FUNCTIONS,
        help="Path to the functions-definition JSON file.",
    )
    p.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the prompts JSON file.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the function-calls JSON file.",
    )
    p.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3-0.6B",
        help="HuggingFace model id (must be supported by llm_sdk).",
    )
    p.add_argument(
        "--visualize",
        action="store_true",
        help="Print a token-by-token generation trace (bonus).",
    )
    p.add_argument(
        "--max_new_tokens",
        type=int,
        default=256,
        help="Maximum tokens to generate per prompt.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Top-level orchestration; returns a process exit code."""
    args = _parse_args(argv)

    try:
        functions = load_function_definitions(args.functions_definition)
        prompts = load_test_prompts(args.input)
    except InputError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    if not functions:
        print(
            "[error] No functions defined; nothing to call.",
            file=sys.stderr,
        )
        return 2
    if not prompts:
        # Nothing to do; still produce an empty output file.
        try:
            write_output(args.output, [])
        except OSError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            return 2
        print(f"No prompts. Wrote empty list to {args.output}")
        return 0

    try:
        # llm_sdk is a project-local package; mypy can't see it.
        from llm_sdk import Small_LLM_Model
    except ImportError as exc:
        print(f"[error] Could not import llm_sdk: {exc}", file=sys.stderr)
        return 3

    try:
        model = Small_LLM_Model(args.model)
        vocab = load_vocabulary(model.get_path_to_vocab_file())
        tokenizer = Tokenizer(vocab)  # our own, bonus
    except Exception as exc:  # pragma: no cover -- SDK init failure
        print(
            f"[error] Failed to initialise model '{args.model}': {exc}",
            file=sys.stderr,
        )
        return 3

    results: list[dict[str, object]] = []
    for i, test in enumerate(prompts, start=1):
        try:
            call = generate_call(
                model=model,
                vocab=vocab,
                tokenizer=tokenizer,
                functions=functions,
                prompt=test.prompt,
                max_new_tokens=args.max_new_tokens,
                visualize=args.visualize,
            )
            results.append(call.model_dump())
        except Exception as exc:  # noqa: BLE001 -- defence in depth
            print(
                f"[warn] Prompt {i}/{len(prompts)} ({test.prompt!r}) failed: "
                f"{exc}",
                file=sys.stderr,
            )
            results.append(
                {"prompt": test.prompt, "name": "", "parameters": {}}
            )
        print(
            f"  [{i}/{len(prompts)}] {test.prompt!r} -> "
            f"{results[-1]['name']!r}"
        )

    try:
        write_output(args.output, results)
    except OSError as exc:
        print(f"[error] Could not write output: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote {len(results)} entries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
