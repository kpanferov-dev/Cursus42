"""MCP server exposing the MBPP tools.

Run:
    python mcp_tools_mbpp.py                                   # stdio (default)
    python mcp_tools_mbpp.py --transport streamable-http --port 8001

The current task is read from ``MBPP_TASK_FILE`` (a task.json dumped by the
moulinette). Without it, ``run_tests`` requires an explicit ``tests`` list.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from smith.models import MBPPTaskInput
from smith.tools.mbpp_tools import MBPPTools


def _load_task() -> Optional[MBPPTaskInput]:
    path = os.environ.get("MBPP_TASK_FILE")
    if not path or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return MBPPTaskInput.model_validate(json.load(f))


TOOLS = MBPPTools(_load_task())
mcp = FastMCP("mbpp-tools", instructions="Run candidate MBPP solutions against assert tests.", log_level="WARNING")


@mcp.tool()
def run_tests(code: str, tests: Optional[List[str]] = None) -> str:
    """Run solution `code` (full source) against the task's public asserts (or `tests`). Returns 'ALL TESTS PASSED (n/n)' or the failures with actual values."""
    return TOOLS.run_tests(code, tests)


@mcp.resource("mbpp://task")
def task_resource() -> str:
    """The current MBPP task (definition, signature, public tests)."""
    return TOOLS.get_task()


@mcp.prompt()
def solve_task() -> str:
    """Prompt template asking to solve the current MBPP task."""
    return ("Solve this task with a single Python function. Verify it with run_tests(code) "
            "and submit the source with final_answer(code).\n\n" + TOOLS.get_task())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--transport", choices=["stdio", "streamable-http", "sse"], default="stdio")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8001)
    a = p.parse_args()
    mcp.settings.host, mcp.settings.port = a.host, a.port
    mcp.run(transport=a.transport)


if __name__ == "__main__":
    main()
