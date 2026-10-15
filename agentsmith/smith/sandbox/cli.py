"""``uv run sandbox`` - interactive sandbox REPL.

Usage::

    uv run sandbox                                   # default config, no MCP
    uv run sandbox sandbox_template.json             # custom config
    uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json
    uv run sandbox --mcp-server http://127.0.0.1:8000/mcp
    uv run sandbox --manual ...                      # print the generated manual

Every entry runs in the sandbox namespace under the same import, filesystem,
timeout and memory restrictions as the agent. ``exit`` or EOF (Ctrl+D) quits.
"""
from __future__ import annotations

import argparse
import asyncio
import codeop
import logging
import sys
from typing import Optional

from smith.models import SandboxConfig
from smith.sandbox.mcp_bridge import MCPBridge
from smith.sandbox.sandbox import Sandbox

EXIT_WORDS = {"exit", "exit()", "quit", "quit()"}


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="sandbox", description="Agent Smith interactive sandbox")
    p.add_argument("config", nargs="?", help="SandboxConfig JSON file")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--mcp-stdio", metavar="CMD", help="command that starts an MCP server over stdio")
    g.add_argument("--mcp-server", metavar="URL", help="URL of a streamable-HTTP (or /sse) MCP server")
    p.add_argument("--manual", action="store_true", help="print the sandbox manual and exit")
    p.add_argument("--env-file", help="optional .env file (exported to the MCP server)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def _read_entry(interactive: bool) -> Optional[str]:
    """Read one complete Python entry (multi-line aware). None on EOF."""
    lines = []
    while True:
        prompt = (">>> " if not lines else "... ") if interactive else ""
        try:
            line = input(prompt)
        except EOFError:
            return "\n".join(lines) if lines else None
        if not lines and line.strip() in EXIT_WORDS:
            return None
        lines.append(line)
        source = "\n".join(lines)
        if not source.strip():
            lines = []
            continue
        try:
            complete = codeop.compile_command(source, "<input>", "exec")
        except (SyntaxError, OverflowError, ValueError):
            return source  # let the sandbox report the error
        if complete is not None:  # None means "incomplete, keep reading"
            return source


async def _repl(args: argparse.Namespace) -> int:
    config = SandboxConfig.from_json_file(args.config) if args.config else SandboxConfig()
    bridge = None
    if args.mcp_stdio or args.mcp_server:
        bridge = MCPBridge(stdio_command=args.mcp_stdio, server_url=args.mcp_server)
    sandbox = Sandbox(config, bridge)
    try:
        await sandbox.start()
    except Exception as e:  # noqa: BLE001
        print(f"error: could not start the sandbox: {type(e).__name__}: {e}", file=sys.stderr)
        await sandbox.close()
        return 1
    try:
        if args.manual:
            print(sandbox.manual())
            return 0
        interactive = sys.stdin.isatty()
        if interactive:
            tools = [t.py_name for t in bridge.tools] if bridge else []
            print(f"Agent Smith sandbox - tools: {', '.join(tools) or '(none)'} + final_answer. "
                  "Type 'exit' or Ctrl+D to quit.")
        loop = asyncio.get_running_loop()
        while True:
            entry = await loop.run_in_executor(None, _read_entry, interactive)
            if entry is None:
                break
            try:
                res = await sandbox.execute(entry)
            except SystemExit as e:
                print(f"SystemExit({e.code}) raised by sandboxed code - leaving the sandbox.")
                break
            text = res.observation(max_chars=config.max_output_chars)
            if res.is_final:
                print(f"[final_answer] {res.final_answer}")
            elif text.strip() and not (res.status == "ok" and text.startswith("(no output")):
                print(text)
            sys.stdout.flush()
        return 0
    finally:
        await sandbox.close()


def main(argv=None) -> None:
    args = _parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, stream=sys.stderr)
    if args.env_file:
        from smith.config import load_env
        load_env(args.env_file)
    try:
        code = asyncio.run(_repl(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
