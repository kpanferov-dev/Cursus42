"""MCP server exposing the SWE-bench tools.

Run:
    python mcp_tools_swebench.py                                   # stdio (default)
    python mcp_tools_swebench.py --transport streamable-http --port 8002

Environment:
    SWEBENCH_CONTAINER_ID   container to operate in (docker exec). If unset,
                            commands run on the local machine.
    SWEBENCH_REPO_ROOT      repository root (default: /testbed)
    SWEBENCH_EVAL_SCRIPT    path to the evaluation script used by run_tests()
    SWEBENCH_TEST_TIMEOUT   seconds for run_tests() (default: 400)
"""
from __future__ import annotations

import argparse
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

from smith.tools.executor import executor_from_env
from smith.tools.swe_tools import SWETools


def _eval_script() -> Optional[str]:
    path = os.environ.get("SWEBENCH_EVAL_SCRIPT")
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return None


TOOLS = SWETools(executor_from_env(), os.environ.get("SWEBENCH_REPO_ROOT", "/testbed"), _eval_script())
TEST_TIMEOUT = int(os.environ.get("SWEBENCH_TEST_TIMEOUT", "400"))

mcp = FastMCP(
    "swebench-tools",
    instructions=f"Tools operate on the repository at {TOOLS.root}. Relative paths are resolved from it.",
    log_level="WARNING",
)


@mcp.tool()
def read_file(filepath: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
    """Read a file with line numbers ('<n>: <line>'), from start_line to end_line (inclusive, 1-indexed).
    At most 300 lines per call; a notice explains how to read the rest."""
    return TOOLS.read_file(filepath, start_line, end_line)


@mcp.tool()
def edit_file(filepath: str, old_str: str, new_str: str) -> str:
    """Replace the exact text old_str (must occur exactly once, indentation included) by new_str.
    Use old_str='' to create a new file. Python edits that would introduce a SyntaxError are rejected;
    new pyflakes warnings are reported. Returns a numbered snippet of the edited region."""
    return TOOLS.edit_file(filepath, old_str, new_str)


@mcp.tool()
def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files (recursively) under directory whose name matches the glob pattern (e.g. '*.py', 'test_*.py')."""
    return TOOLS.list_files(directory, pattern)


@mcp.tool()
def search_code(pattern: str, file_pattern: str = "*.py") -> str:
    """grep -E the repository for pattern in files matching file_pattern ('*' for all files).
    Output lines: '/abs/path.py:<line> <content>'."""
    return TOOLS.search_code(pattern, file_pattern)


@mcp.tool()
def search_function_or_class_definition_in_code(name: str) -> str:
    """Find where a function/method/class named `name` is defined ('def name' / 'class name').
    Output lines: '/abs/path.py:<line> <content>'."""
    return TOOLS.search_function_or_class_definition_in_code(name)


@mcp.tool()
def find_references(name: str, filepath: Optional[str] = None, line: Optional[int] = None) -> str:
    """Find all usages of the symbol `name` (whole word) in Python files; filepath/line optionally
    identify the symbol occurrence you start from (its file is listed first). Output like search_code."""
    return TOOLS.find_references(name, filepath, line)


@mcp.tool()
def run_tests() -> str:
    """Run the task's evaluation script (the tests that must pass). Returns exit code, a pass/fail
    summary, the failing test lines and the tail of the test output."""
    return TOOLS.run_tests(TEST_TIMEOUT)


@mcp.tool()
def get_patch() -> str:
    """Return the unified git diff of all changes made to tracked files of the repository."""
    return TOOLS.get_patch()


@mcp.tool()
def run_command(command: str, workdir: str = "/testbed", timeout: int = 120) -> str:
    """Execute a bash command in workdir (python = the project's environment). Returns
    'exit_code', 'stdout' and 'stderr'. Long outputs are truncated with a notice."""
    return TOOLS.run_command(command, workdir, timeout)


@mcp.resource("swebench://eval_script")
def eval_script_resource() -> str:
    """The evaluation script run by run_tests()."""
    return TOOLS.eval_script or "(no eval script configured)"


@mcp.prompt()
def debugging_workflow(issue: str = "") -> str:
    """A step-by-step bug fixing methodology."""
    return ("1. Locate the code mentioned in the issue (search_code / search_function_or_class_definition_in_code).\n"
            "2. Read it (read_file) and reproduce the bug (run_command with a small python -c script).\n"
            "3. Make a minimal fix (edit_file).\n4. Verify (reproduction + run_tests()).\n"
            "5. final_answer(get_patch()).\n\nIssue:\n" + issue)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--transport", choices=["stdio", "streamable-http", "sse"], default="stdio")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8002)
    a = p.parse_args()
    mcp.settings.host, mcp.settings.port = a.host, a.port
    mcp.run(transport=a.transport)


if __name__ == "__main__":
    main()
