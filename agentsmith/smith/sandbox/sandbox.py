"""Parent-side sandbox: owns the worker process and the MCP bridge.

``Sandbox.execute(code)`` sends a cell to the worker, services MCP calls the
worker makes while running, enforces a hard wall-clock limit (tool time
excluded), and returns an :class:`ExecutionResult` whose ``observation()``
is what the LLM sees - including explicit notices for every abnormal
situation (timeout, truncation, crash, policy violation...).

``KeyboardInterrupt`` / ``SystemExit`` raised by sandboxed code (or by the
user pressing Ctrl+C) are re-raised to the caller, never swallowed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from smith.models import SandboxConfig
from smith.sandbox.manual import build_manual
from smith.sandbox.mcp_bridge import MCPBridge, ToolCallError

log = logging.getLogger("smith.sandbox")

WORKER_PATH = Path(__file__).with_name("worker.py")
HARD_KILL_GRACE_S = 3.0


class SandboxError(Exception):
    """The sandbox itself failed (not the user code)."""


@dataclass
class ExecutionResult:
    output: str = ""
    status: str = "ok"                 # ok | error | violation | timeout | memory | crash | final
    error: str = ""
    final_answer: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    duration_s: float = 0.0
    tool_calls: int = 0

    @property
    def is_final(self) -> bool:
        return self.final_answer is not None

    def observation(self, max_chars: int) -> str:
        """Render the text fed back to the LLM (always non-empty, never silent)."""
        body = self.output
        if self.error:
            body = (body + "\n" if body else "") + self.error
        body = body.rstrip()
        notes = list(self.notes)
        if len(body) > max_chars:
            head = int(max_chars * 0.4)
            tail = max_chars - head
            omitted = len(body) - head - tail
            body = (body[:head] + f"\n... [{omitted} characters omitted] ...\n" + body[-tail:])
            notes.append(f"[NOTICE] Output truncated: {omitted} of {len(self.output) + len(self.error)} "
                         "characters were omitted (beginning and end kept). Print less or narrow your query.")
        if not body:
            body = ("(no output - the code ran without printing anything; "
                    "use print() to see values)") if self.status == "ok" else "(no output)"
        return "\n".join(notes + [body]) if notes else body


class Sandbox:
    """Secure, persistent Python execution environment with MCP tools."""

    def __init__(self, config: Optional[SandboxConfig] = None, mcp: Optional[MCPBridge] = None,
                 mcp_extras: bool = True):
        self.config = config or SandboxConfig()
        self.mcp = mcp
        self.mcp_extras = mcp_extras and mcp is not None
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._exec_id = 0
        self._stderr_tail: List[str] = []
        self._stderr_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ life cycle
    async def __aenter__(self) -> "Sandbox":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def start(self) -> None:
        if self.mcp is not None and self.mcp.session is None:
            await self.mcp.connect()
        await self._spawn()

    async def _spawn(self) -> None:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8",
               "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
        self._proc = await asyncio.create_subprocess_exec(
            sys.executable, "-I", "-u", str(WORKER_PATH),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, env=env, start_new_session=True,
            limit=64 * 1024 * 1024,
        )
        self._stderr_tail = []
        self._stderr_task = asyncio.create_task(self._drain_stderr(self._proc))
        functions = [t.worker_spec() for t in (self.mcp.tools if self.mcp else [])]
        await self._write({"type": "init", "config": self.config.model_dump(),
                           "functions": functions, "mcp_extras": self.mcp_extras})
        msg = await self._read(timeout=30)
        if msg is None or msg.get("type") != "ready":
            raise SandboxError(f"sandbox worker failed to start: {''.join(self._stderr_tail)[-2000:]}")

    async def _drain_stderr(self, proc) -> None:
        try:
            while True:
                line = await proc.stderr.readline()
                if not line:
                    return
                self._stderr_tail.append(line.decode("utf-8", "replace"))
                self._stderr_tail = self._stderr_tail[-50:]
        except Exception:  # noqa: BLE001
            return

    async def close(self) -> None:
        await self._kill_worker(graceful=True)
        if self.mcp is not None:
            await self.mcp.close()

    async def _kill_worker(self, graceful: bool = False) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if graceful and proc.returncode is None:
                try:
                    proc.stdin.write(b'{"type": "shutdown"}\n')
                    await proc.stdin.drain()
                    await asyncio.wait_for(proc.wait(), 2)
                except Exception:  # noqa: BLE001
                    pass
            if proc.returncode is None:
                try:
                    os.killpg(proc.pid, 9)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass
        if self._stderr_task:
            self._stderr_task.cancel()

    async def restart(self) -> None:
        await self._kill_worker()
        await self._spawn()

    # ------------------------------------------------------------------ io
    async def _write(self, msg: dict) -> None:
        assert self._proc is not None
        self._proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self._proc.stdin.drain()

    async def _read(self, timeout: Optional[float]) -> Optional[dict]:
        assert self._proc is not None
        line = await asyncio.wait_for(self._proc.stdout.readline(), timeout)
        if not line:
            return None
        return json.loads(line)

    # ------------------------------------------------------------------ manual
    def manual(self, compact: bool = False) -> str:
        return build_manual(
            self.config, self.mcp.tools if self.mcp else [], compact=compact,
            mcp_extras=self.mcp_extras,
            server_instructions=(self.mcp.instructions if self.mcp and not compact else None),
        )

    # ------------------------------------------------------------------ execute
    async def execute(self, code: str) -> ExecutionResult:
        """Run ``code`` in the persistent namespace. See module docstring."""
        if self._proc is None or self._proc.returncode is not None:
            await self._spawn()
        self._exec_id += 1
        result = ExecutionResult()
        out: List[str] = []
        limit = float(self.config.max_execution_time_seconds) + HARD_KILL_GRACE_S
        exec_time = 0.0
        t_wall = time.monotonic()
        try:
            await self._write({"type": "exec", "id": self._exec_id, "code": code})
            while True:
                t0 = time.monotonic()
                try:
                    msg = await self._read(timeout=max(0.05, limit - exec_time))
                except asyncio.TimeoutError:
                    await self.restart()
                    result.status = "timeout"
                    result.notes.append(
                        f"[TIMEOUT] Execution exceeded {self.config.max_execution_time_seconds}s and the "
                        "sandbox process was killed. The output below is PARTIAL. All variables were lost "
                        "(the sandbox was restarted) - redefine what you need.")
                    break
                exec_time += time.monotonic() - t0
                if msg is None:  # worker died (e.g. hard memory kill)
                    tail = "".join(self._stderr_tail)[-500:]
                    await self.restart()
                    result.status = "crash"
                    result.notes.append(
                        "[CRASH] The sandbox process died (most likely the memory limit of "
                        f"{self.config.max_memory_mb} MB). Output below is partial; all variables were lost."
                        + (f"\nworker stderr: {tail}" if tail.strip() else ""))
                    break
                mtype = msg.get("type")
                if mtype == "out":
                    out.append(msg.get("text", ""))
                elif mtype == "call":
                    result.tool_calls += 1
                    await self._service_call(msg)
                elif mtype == "done":
                    self._apply_done(msg, result)
                    break
        except (KeyboardInterrupt, asyncio.CancelledError):
            await self._kill_worker()
            raise
        result.output = "".join(out)
        result.duration_s = time.monotonic() - t_wall
        if result.status == "sysexit":
            raise SystemExit(result.error or 0)
        if result.status == "kbint":
            raise KeyboardInterrupt("raised by sandboxed code")
        return result

    async def _service_call(self, msg: dict) -> None:
        reply = {"type": "call_result", "call_id": msg["call_id"]}
        try:
            if self.mcp is None:
                raise RuntimeError("no MCP server is connected")
            value = await self.mcp.call(msg["kind"], msg.get("name", ""), msg.get("args") or {})
            reply.update(ok=True, value=value)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:  # noqa: BLE001 - reported to the sandboxed code as ToolError
            reply.update(ok=False, error=str(e) if isinstance(e, ToolCallError) else f"{type(e).__name__}: {e}")
        await self._write(reply)

    def _apply_done(self, msg: dict, result: ExecutionResult) -> None:
        status = msg.get("status", "error")
        result.status = status
        if status == "final":
            result.final_answer = msg.get("final", "")
        elif status in ("error", "violation", "memory"):
            result.error = msg.get("error", "")
        elif status == "timeout":
            result.error = msg.get("error", "")
            result.notes.append(
                f"[TIMEOUT] Execution exceeded {self.config.max_execution_time_seconds}s and was interrupted; "
                "the output is PARTIAL. Variables defined before the interruption are kept.")
        elif status == "sysexit":
            result.error = str(msg.get("code") if msg.get("code") is not None else 0)
        if status == "violation":
            result.notes.append("[POLICY] The code was rejected by the sandbox policy and did NOT run.")
        if status == "memory":
            result.notes.append("[MEMORY] The memory limit was hit; the operation was aborted.")
        if msg.get("output_dropped"):
            result.notes.append("[NOTICE] The program printed too much; extra output was discarded.")
