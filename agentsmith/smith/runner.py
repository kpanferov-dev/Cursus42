"""Shared command-line plumbing for ``agent_mbpp`` and ``agent_swebench``.

Guarantees: a ``solution.json`` is ALWAYS written (even on crash or Ctrl+C),
and the process never dies with an unhandled traceback.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Awaitable, Callable, Optional

from smith.config import load_env
from smith.models import SolutionOutput

log = logging.getLogger("smith")


def base_parser(prog: str, description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=prog, description=description)
    p.add_argument("--task-file", required=True, help="task.json dumped by the moulinette")
    p.add_argument("--output", required=True, help="where to write solution.json")
    p.add_argument("--model-name", required=True, help="model identifier for the provider")
    p.add_argument("--provider-url", default=None, help="OpenAI-compatible base URL")
    p.add_argument("--provider", default=None, help="provider name from config/models.json")
    p.add_argument("--api-key-env", default=None, help="env var holding the API key(s) (override)")
    p.add_argument("--models-config", default=None, help="alternative models.json")
    p.add_argument("--env-file", default=None, help=".env file with API keys")
    p.add_argument("--sandbox-config", default=None, help="SandboxConfig JSON")
    p.add_argument("--max-iterations", type=int, default=None, help="lower the iteration limit")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--mcp-stdio", default=None, help="override the MCP server command (stdio)")
    g.add_argument("--mcp-server", default=None, help="use an MCP server over streamable HTTP")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--no-fallback", action="store_true",
                   help="disable the provider fallbacks of models.json (used by benchmarks)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO, stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S",
    )
    for noisy in ("httpx", "mcp", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def write_solution(path: str, sol: SolutionOutput) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(sol.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(out)


def error_solution(task_id: str, benchmark: str, error: str, started: float) -> SolutionOutput:
    return SolutionOutput(task_id=task_id, benchmark=benchmark, success=False, solution="",
                          iterations=0, total_requests=0, total_input_tokens=0, total_output_tokens=0,
                          total_time_seconds=round(time.monotonic() - started, 3), error=error)


def read_task_id(task_file: str) -> str:
    try:
        data = json.loads(Path(task_file).read_text(encoding="utf-8"))
        return str(data.get("task_id") or data.get("instance_id") or "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


def run_main(args: argparse.Namespace, benchmark: str,
             coro_factory: Callable[[argparse.Namespace], Awaitable[SolutionOutput]]) -> int:
    """Run the async agent, translate signals, always write the output file."""
    setup_logging(args.verbose)
    started = time.monotonic()
    task_id = read_task_id(args.task_file)

    def _sigterm(signum, frame):
        raise KeyboardInterrupt(f"signal {signum}")

    signal.signal(signal.SIGTERM, _sigterm)
    solution: Optional[SolutionOutput] = None
    code = 0
    try:
        load_env(args.env_file)
        solution = asyncio.run(coro_factory(args))
    except KeyboardInterrupt:
        log.error("interrupted")
        solution = error_solution(task_id, benchmark, "interrupted (KeyboardInterrupt)", started)
        code = 130
    except SystemExit as e:
        solution = error_solution(task_id, benchmark, f"SystemExit({e.code})", started)
        code = 1
    except Exception as e:  # noqa: BLE001 - never crash without an output file
        from smith.llm.base import LLMError
        expected = isinstance(e, (LLMError, FileNotFoundError, ValueError))  # config / input problems
        log.error("fatal error: %s%s", e, "" if expected and not args.verbose else "\n" + traceback.format_exc())
        solution = error_solution(task_id, benchmark, f"{type(e).__name__}: {e}", started)
        code = 1
    finally:
        if solution is not None:
            try:
                write_solution(args.output, solution)
                log.info("solution written to %s (success=%s, iterations=%d, tokens in/out=%d/%d, %.1fs)",
                         args.output, solution.success, solution.iterations, solution.total_input_tokens,
                         solution.total_output_tokens, solution.total_time_seconds)
            except OSError as e:
                log.error("could not write %s: %s", args.output, e)
                code = code or 1
    return code
