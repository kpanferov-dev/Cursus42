"""Sandbox manual generation.

The manual is built dynamically from the connected MCP server's tool
schemas, so plugging in an unknown server automatically documents its
tools for the LLM.
"""
from __future__ import annotations

import inspect
from typing import List, Optional

from smith.models import SandboxConfig
from smith.sandbox.mcp_bridge import ToolSpec


def _first_sentence(text: str) -> str:
    text = " ".join(text.split())
    for sep in (". ", "\n"):
        if sep in text:
            return text.split(sep)[0].rstrip(".") + "."
    return text


def tools_section(tools: List[ToolSpec], compact: bool = False) -> str:
    if not tools:
        return "(no MCP tools connected)"
    lines = []
    for t in tools:
        lines.append(f"- {t.signature()} -> str")
        if t.description:
            if compact:
                lines.append(f"    {_first_sentence(t.description)}")
            else:
                for dl in inspect.cleandoc(t.description).splitlines():
                    if dl.strip():
                        lines.append(f"    {dl.rstrip()}")
        if t.py_name != t.mcp_name:
            lines.append(f"    (MCP name: '{t.mcp_name}')")
    return "\n".join(lines)


def build_manual(
    config: SandboxConfig,
    tools: List[ToolSpec],
    *,
    compact: bool = False,
    mcp_extras: bool = False,
    server_instructions: Optional[str] = None,
) -> str:
    """Return the sandbox manual injected into the system prompt."""
    imports = sorted({p.split(".*")[0] for p in config.authorized_imports})
    if compact:
        return (
            "SANDBOX: Python 3.10; variables persist between steps; print() to see results.\n"
            f"Allowed imports: {', '.join(imports)}. No files/network/os. "
            f"Timeout {config.max_execution_time_seconds}s per step.\n"
            "Functions available:\n"
            f"{tools_section(tools, compact=True)}\n"
            "- final_answer(answer: str) -> ends the task with `answer`."
        )
    parts = [
        "## Sandbox manual",
        "Your code runs in a restricted Python 3.10 interpreter:",
        "- Variables, functions and imports persist between steps.",
        "- Only print() output (and the value of a final bare expression) is shown to you.",
        f"- Allowed imports: {', '.join(imports)}. Everything else (os, sys, subprocess, socket, ...) is blocked.",
        f"- File access only below: {', '.join(config.allowed_directories)}. No network.",
        f"- Each execution is limited to {config.max_execution_time_seconds}s and {config.max_memory_mb} MB; "
        f"output longer than {config.max_output_chars} chars is truncated.",
        "- Tool functions are ordinary Python functions returning strings; a failing tool raises ToolError.",
        "",
        "### Tool functions (from the connected MCP server)",
        tools_section(tools, compact=False),
        "",
        "### Built-in",
        "- final_answer(answer: str) -> submit the final answer and stop.",
    ]
    if mcp_extras:
        parts += [
            "- list_resources() / read_resource(uri) -> MCP resources exposed by the server.",
            "- list_prompts() / get_prompt(name, arguments: dict) -> MCP prompt templates.",
        ]
    if server_instructions:
        parts += ["", "### Server instructions", server_instructions.strip()]
    return "\n".join(parts)
