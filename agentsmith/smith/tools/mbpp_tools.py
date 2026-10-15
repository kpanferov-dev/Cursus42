"""MBPP tool implementation: run candidate code against assert-style tests.

The candidate code is executed in a short-lived child interpreter
(``python -I``) with CPU/memory/file-size limits and an audit hook that
blocks network, processes and file writes. Each assert is run separately
so the LLM learns *which* test failed and what the actual value was.
"""
from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import tempfile
from typing import List, Optional

from smith.models import MBPPTaskInput

_RUNNER = r'''
import ast, json, sys
data = json.loads(sys.stdin.read())

def _hook(event, args):
    if event.startswith(("socket.", "subprocess.", "os.system", "os.exec", "os.fork", "os.spawn",
                         "os.posix_spawn", "ctypes.", "os.kill", "os.remove", "os.rmdir", "shutil.")):
        raise PermissionError("blocked in test runner: " + event)
    if event == "open" and isinstance(args[0], str):
        mode = args[1] if len(args) > 1 and isinstance(args[1], str) else "r"
        if any(c in mode for c in "wax+"):
            raise PermissionError("file writes are blocked in the test runner")
sys.addaudithook(_hook)

ns = {"__name__": "__solution__"}
res = {"setup_error": None, "results": []}
try:
    exec(compile(data["code"], "<solution>", "exec"), ns)
    for imp in data["imports"]:
        exec(imp, ns)
except BaseException as e:
    res["setup_error"] = f"{type(e).__name__}: {e}"
    print(json.dumps(res)); sys.exit(0)

def _actual(test):
    try:
        node = ast.parse(test).body[0]
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
            left = eval(compile(ast.Expression(node.test.left), "<t>", "eval"), ns)
            right = eval(compile(ast.Expression(node.test.comparators[0]), "<t>", "eval"), ns)
            return f"got {left!r}, expected {right!r}"
    except BaseException as e:
        return f"{type(e).__name__}: {e}"
    return ""

for t in data["tests"]:
    try:
        exec(compile(t, "<test>", "exec"), ns)
        res["results"].append({"test": t, "ok": True})
    except AssertionError:
        res["results"].append({"test": t, "ok": False, "error": "AssertionError " + _actual(t)})
    except BaseException as e:
        res["results"].append({"test": t, "ok": False, "error": f"{type(e).__name__}: {e}"})
print(json.dumps(res))
'''


def _limits(mem_mb: int, cpu_s: int):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS, (mem_mb << 20, mem_mb << 20))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))
    return apply


class MBPPTools:
    def __init__(self, task: Optional[MBPPTaskInput] = None, timeout_s: int = 10, memory_mb: int = 1024):
        self.task = task
        self.timeout_s = timeout_s
        self.memory_mb = memory_mb

    def run_tests(self, code: str, tests: Optional[List[str]] = None) -> str:
        if not isinstance(code, str) or not code.strip():
            return "ERROR: `code` must be the full source of your solution as a string."
        if tests is None:
            if self.task is None:
                return "ERROR: no task loaded; pass `tests` explicitly (list of assert statements)."
            tests = list(self.task.test_list)
        imports = list(self.task.test_imports) if self.task else []
        if isinstance(tests, str):
            tests = [tests]
        payload = json.dumps({"code": code, "imports": imports, "tests": tests})
        with tempfile.TemporaryDirectory(prefix="mbpp_") as tmp:
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", "-c", _RUNNER], input=payload, capture_output=True, text=True,
                    timeout=self.timeout_s, cwd=tmp, env={"PATH": os.environ.get("PATH", "")},
                    preexec_fn=_limits(self.memory_mb, self.timeout_s),
                )
            except subprocess.TimeoutExpired:
                return f"TIMEOUT: tests did not finish within {self.timeout_s}s (infinite loop or too slow?)"
        try:
            res = json.loads(proc.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            err = (proc.stderr or "").strip()[-800:]
            return f"ERROR: test runner crashed (exit {proc.returncode}). {err or 'MemoryError?'}"
        if res["setup_error"]:
            return f"ERROR while defining your code: {res['setup_error']}"
        results = res["results"]
        ok = sum(r["ok"] for r in results)
        if ok == len(results):
            return f"ALL TESTS PASSED ({ok}/{len(results)})"
        lines = [f"FAILED {len(results) - ok}/{len(results)} tests:"]
        lines += [f"- {r['test']}  ->  {r['error']}"[:400] for r in results if not r["ok"]]
        return "\n".join(lines)

    def get_task(self) -> str:
        if self.task is None:
            return "No task loaded."
        t = self.task
        return (f"Task {t.task_id}: {t.task_definition}\nSignature: {t.function_definition}\n"
                "Tests:\n" + "\n".join(t.test_list))
