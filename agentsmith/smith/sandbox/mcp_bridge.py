"""MCP client bridge.

Connects to ONE MCP server (stdio command or streamable-HTTP / SSE URL),
discovers its tools / resources / prompts, and exposes them as plain
Python call specs for the sandbox worker. The sandbox wraps this client;
tools run *outside* the sandbox (in the MCP server process).
"""
from __future__ import annotations

import keyword
import logging
import os
import re
import shlex
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

log = logging.getLogger("smith.mcp")

RESERVED = {"final_answer", "list_resources", "read_resource", "list_prompts", "get_prompt",
            "print", "open", "ToolError"}

_JSON_TO_PY = {"string": "str", "integer": "int", "number": "float", "boolean": "bool",
               "array": "list", "object": "dict", "null": "None"}


class ToolCallError(RuntimeError):
    """The MCP server reported an error for a tool call (message is for the LLM)."""


@dataclass
class ToolSpec:
    """A discovered MCP tool, described for the manual and the worker."""
    mcp_name: str
    py_name: str
    description: str
    params: List[str]
    required: List[str]
    schema: Dict[str, Any] = field(default_factory=dict)

    def signature(self) -> str:
        props = self.schema.get("properties", {}) or {}
        parts = []
        for p in self.params:
            ptype = _py_type(props.get(p, {}))
            if p in self.required:
                parts.append(f"{p}: {ptype}")
            else:
                default = props.get(p, {}).get("default", None)
                parts.append(f"{p}: {ptype} = {default!r}")
        return f"{self.py_name}({', '.join(parts)})"

    def worker_spec(self) -> dict:
        return {"name": self.py_name, "mcp_name": self.mcp_name, "params": self.params,
                "required": self.required, "doc": self.description}


def _py_type(schema: dict) -> str:
    if "anyOf" in schema:
        types_ = [_py_type(s) for s in schema["anyOf"]]
        non_null = [t for t in types_ if t != "None"]
        base = " | ".join(non_null) or "Any"
        return f"{base} | None" if "None" in types_ else base
    t = schema.get("type")
    if isinstance(t, list):
        return " | ".join(_JSON_TO_PY.get(x, "Any") for x in t)
    if t == "array" and isinstance(schema.get("items"), dict) and schema["items"].get("type"):
        return f"list[{_JSON_TO_PY.get(schema['items']['type'], 'Any')}]"
    return _JSON_TO_PY.get(t, "Any")


def to_identifier(name: str, taken: set) -> str:
    """Turn any MCP tool name into a unique valid Python identifier."""
    ident = re.sub(r"\W", "_", name)
    if not ident or ident[0].isdigit() or keyword.iskeyword(ident) or ident in RESERVED:
        ident = f"tool_{ident}"
    base, i = ident, 2
    while ident in taken:
        ident = f"{base}_{i}"
        i += 1
    taken.add(ident)
    return ident


class MCPBridge:
    """Async MCP client with a small, sandbox-friendly surface."""

    def __init__(self, stdio_command: Optional[str] = None, server_url: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None):
        if bool(stdio_command) == bool(server_url):
            raise ValueError("Provide exactly one of stdio_command or server_url")
        self.stdio_command = stdio_command
        self.server_url = server_url
        self.env = env or {}
        self.cwd = cwd
        self._stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None
        self.tools: List[ToolSpec] = []
        self.server_name = ""
        self.instructions = ""
        self.has_resources = False
        self.has_prompts = False

    # ------------------------------------------------------------------ connect
    async def connect(self) -> None:
        if self.stdio_command:
            argv = shlex.split(self.stdio_command)
            if argv and argv[0] in ("python", "python3"):
                argv[0] = sys.executable  # the project's interpreter
            params = StdioServerParameters(command=argv[0], args=argv[1:],
                                           env={**os.environ, **self.env}, cwd=self.cwd)
            read, write = await self._stack.enter_async_context(stdio_client(params))
        else:
            read, write = await self._open_http(self.server_url)
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        init = await self.session.initialize()
        self.server_name = getattr(init.serverInfo, "name", "") or ""
        self.instructions = init.instructions or ""
        caps = init.capabilities
        self.has_resources = bool(getattr(caps, "resources", None))
        self.has_prompts = bool(getattr(caps, "prompts", None))
        await self._discover_tools()

    async def _open_http(self, url: str):
        if url.rstrip("/").endswith("/sse"):
            from mcp.client.sse import sse_client
            read, write = await self._stack.enter_async_context(sse_client(url))
            return read, write
        try:
            from mcp.client.streamable_http import streamable_http_client as _client
        except ImportError:  # older SDKs
            from mcp.client.streamable_http import streamablehttp_client as _client
        read, write, _ = await self._stack.enter_async_context(_client(url))
        return read, write

    async def _discover_tools(self) -> None:
        tools, cursor, taken = [], None, set()
        while True:
            res = await self.session.list_tools(cursor) if cursor else await self.session.list_tools()
            for t in res.tools:
                schema = t.inputSchema or {}
                params = list((schema.get("properties") or {}).keys())
                required = list(schema.get("required") or [])
                params = [p for p in params if p in required] + [p for p in params if p not in required]
                tools.append(ToolSpec(
                    mcp_name=t.name, py_name=to_identifier(t.name, taken),
                    description=(t.description or "").strip(), params=params,
                    required=required, schema=schema,
                ))
            cursor = getattr(res, "nextCursor", None)
            if not cursor:
                break
        self.tools = tools

    async def close(self) -> None:
        try:
            await self._stack.aclose()
        except BaseException as e:  # noqa: BLE001 - never crash on shutdown
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            log.debug("MCP close error: %s", e)

    # ------------------------------------------------------------------ calls
    async def call(self, kind: str, name: str, args: Dict[str, Any]) -> str:
        """Dispatch one request coming from the sandbox. Raises on MCP errors."""
        if self.session is None:
            raise RuntimeError("MCP server not connected")
        if kind == "tool":
            res = await self.session.call_tool(name, args)
            text = _content_to_text(res.content)
            structured = getattr(res, "structuredContent", None)
            if not text and structured:
                if isinstance(structured, dict) and set(structured) == {"result"}:
                    text = "" if structured["result"] is None else str(structured["result"])
                else:
                    text = str(structured)
            if res.isError:
                text = re.sub(rf"^Error executing tool {re.escape(name)}: ", "", text or "")
                raise ToolCallError(text or f"tool '{name}' failed")
            return text
        if kind == "list_resources":
            res = await self.session.list_resources()
            lines = [f"{r.uri}  {r.name or ''}  {r.description or ''}".rstrip() for r in res.resources]
            try:
                tpl = await self.session.list_resource_templates()
                lines += [f"{t.uriTemplate}  (template) {t.description or ''}" for t in tpl.resourceTemplates]
            except Exception:  # noqa: BLE001 - templates are optional
                pass
            return "\n".join(lines) or "(no resources)"
        if kind == "read_resource":
            res = await self.session.read_resource(name)
            return "\n".join(getattr(c, "text", None) or f"<binary {getattr(c, 'mimeType', '')}>"
                             for c in res.contents)
        if kind == "list_prompts":
            res = await self.session.list_prompts()
            out = []
            for p in res.prompts:
                args_ = ", ".join(a.name + ("" if a.required else "?") for a in (p.arguments or []))
                out.append(f"{p.name}({args_})  {p.description or ''}".rstrip())
            return "\n".join(out) or "(no prompts)"
        if kind == "get_prompt":
            res = await self.session.get_prompt(name, {k: str(v) for k, v in args.items()})
            return "\n\n".join(f"[{m.role}] {_content_to_text([m.content])}" for m in res.messages)
        raise ValueError(f"unknown call kind '{kind}'")


def _content_to_text(content) -> str:
    parts = []
    for c in content or []:
        ctype = getattr(c, "type", "")
        if ctype == "text":
            parts.append(c.text)
        elif ctype == "resource":
            res = c.resource
            parts.append(getattr(res, "text", None) or f"<resource {res.uri}>")
        else:
            parts.append(f"<{ctype} content>")
    return "\n".join(parts)
