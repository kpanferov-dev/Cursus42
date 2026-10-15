"""SWE-bench tool implementations (independent of the agent loop and of MCP).

Every public method returns a string for the LLM and raises ``ToolInputError``
for bad input (unknown file, ambiguous edit, ...). The MCP server
(``mcp_tools_swebench.py``) is a thin wrapper around this class, so the tools
can also be unit-tested / used directly::

    tools = SWETools(LocalExecutor(), repo_root="/path/to/repo")
    print(tools.search_code("def validate_email"))
"""
from __future__ import annotations

import ast
import posixpath
import re
import shlex
from typing import List, Optional, Tuple

from smith.tools.executor import Executor

START_TEST_OUTPUT = ">>>>> Start Test Output"
END_TEST_OUTPUT = ">>>>> End Test Output"

MAX_READ_LINES = 300
MAX_MATCHES = 80
MAX_LINE_CHARS = 220
MAX_CMD_CHARS = 5000
MAX_TEST_CHARS = 5000


class ToolInputError(ValueError):
    """Bad arguments: the message is shown to the LLM."""


def _clip_line(s: str) -> str:
    return s if len(s) <= MAX_LINE_CHARS else s[:MAX_LINE_CHARS] + " …[line truncated]"


def _clip_block(text: str, limit: int, keep: str = "tail") -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    if keep == "tail":
        return f"[TRUNCATED: first {omitted} chars omitted]\n" + text[-limit:]
    if keep == "head":
        return text[:limit] + f"\n[TRUNCATED: last {omitted} chars omitted]"
    half = limit // 2
    return text[:half] + f"\n[TRUNCATED: {omitted} chars omitted]\n" + text[-half:]


class SWETools:
    def __init__(self, executor: Executor, repo_root: str = "/testbed", eval_script: Optional[str] = None):
        self.ex = executor
        self.root = repo_root.rstrip("/") or "/"
        self.eval_script = eval_script

    # ------------------------------------------------------------------ helpers
    def _abs(self, path: str) -> str:
        if not path:
            raise ToolInputError("empty path")
        path = path.strip()
        if self.root != "/testbed" and (path == "/testbed" or path.startswith("/testbed/")):
            path = self.root + path[len("/testbed"):]  # local-repo mode: map the canonical root
        if not path.startswith("/"):
            path = posixpath.join(self.root, path)
        return posixpath.normpath(path)

    def _grep(self, args: List[str], path: Optional[str] = None) -> Tuple[List[str], str]:
        target = self._abs(path) if path else self.root
        cmd = ("grep -rnI --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=.tox "
               "--exclude-dir=node_modules --exclude-dir=*.egg-info "
               + " ".join(shlex.quote(a) for a in args) + " " + shlex.quote(target))
        r = self.ex.run(cmd, timeout=90)
        if r.exit_code > 1:
            return [], r.stderr.strip() or f"grep failed (exit {r.exit_code})"
        return [l for l in r.stdout.splitlines() if l], ""

    @staticmethod
    def _format_matches(lines: List[str], what: str) -> str:
        out = []
        for l in lines:
            m = re.match(r"^(.*?):(\d+):(.*)$", l)
            out.append(f"{m.group(1)}:{m.group(2)} {_clip_line(m.group(3))}" if m else _clip_line(l))
        total = len(out)
        if total == 0:
            return f"No matches found for {what}."
        if total > MAX_MATCHES:
            return ("\n".join(out[:MAX_MATCHES])
                    + f"\n[TRUNCATED: showing {MAX_MATCHES} of {total} matches - refine the pattern "
                      "or use file_pattern to narrow the search]")
        return "\n".join(out)

    # ------------------------------------------------------------------ file system
    def read_file(self, filepath: str, start_line: int = 1, end_line: Optional[int] = None) -> str:
        path = self._abs(filepath)
        if self.ex.is_dir(path):
            raise ToolInputError(f"{path} is a directory; use list_files()")
        try:
            content = self.ex.read_text(path)
        except FileNotFoundError:
            raise ToolInputError(f"File not found: {path}") from None
        lines = content.splitlines()
        n = len(lines)
        start = max(1, int(start_line or 1))
        end = n if end_line in (None, 0, -1) else min(n, int(end_line))
        if n == 0:
            return f"(empty file: {path})"
        if start > n:
            raise ToolInputError(f"start_line {start} is past the end of {path} ({n} lines)")
        if end < start:
            raise ToolInputError(f"end_line {end} < start_line {start}")
        notice = ""
        if end - start + 1 > MAX_READ_LINES:
            end = start + MAX_READ_LINES - 1
            notice = (f"\n[TRUNCATED: {path} has {n} lines; showing {start}-{end}. "
                      f"Call read_file('{filepath}', {end + 1}, {min(n, end + MAX_READ_LINES)}) for more]")
        body = "\n".join(f"{i}: {_clip_line(lines[i - 1])}" for i in range(start, end + 1))
        return body + notice

    def edit_file(self, filepath: str, old_str: str, new_str: str) -> str:
        path = self._abs(filepath)
        exists = self.ex.exists(path)
        if not exists:
            if old_str:
                raise ToolInputError(f"File not found: {path}. To create a file pass old_str=''.")
            self.ex.write_text(path, new_str)
            return f"Created {path} ({len(new_str.splitlines())} lines)." + self._lint_report(path, None, new_str)
        if old_str == "":
            raise ToolInputError(f"{path} already exists: old_str must be the exact text to replace")
        if old_str == new_str:
            raise ToolInputError("old_str and new_str are identical: nothing to change")
        content = self.ex.read_text(path)
        count = content.count(old_str)
        if count == 0:
            raise ToolInputError(self._no_match_hint(path, content, old_str))
        if count > 1:
            lines = [content[: m.start()].count("\n") + 1 for m in re.finditer(re.escape(old_str), content)]
            raise ToolInputError(
                f"old_str occurs {count} times in {path} (lines {lines[:10]}). "
                "Include more surrounding lines so that it is unique.")
        new_content = content.replace(old_str, new_str, 1)
        if path.endswith(".py"):
            err = _syntax_error(new_content)
            if err and not _syntax_error(content):
                raise ToolInputError(
                    f"Edit REJECTED (file unchanged): it would introduce a SyntaxError in {path}: {err}. "
                    "Check indentation and brackets of new_str.")
        self.ex.write_text(path, new_content)
        first = content[: content.index(old_str)].count("\n") + 1
        new_lines = new_content.splitlines()
        last = first + new_str.count("\n")
        lo, hi = max(1, first - 3), min(len(new_lines), last + 3)
        snippet = "\n".join(f"{i}: {new_lines[i - 1]}" for i in range(lo, hi + 1))
        return (f"Edited {path} (replaced 1 occurrence at line {first}). Snippet after the edit:\n{snippet}"
                + self._lint_report(path, content, new_content))

    def _no_match_hint(self, path: str, content: str, old_str: str) -> str:
        msg = f"old_str not found in {path} (it must match exactly, including indentation)."
        first = next((l.strip() for l in old_str.splitlines() if l.strip()), "")
        if first:
            cands = [i + 1 for i, l in enumerate(content.splitlines()) if first in l]
            if cands:
                msg += f" The first line of old_str appears (maybe with different indentation/context) at line(s) {cands[:8]}; read_file() those lines and copy them exactly."
        return msg

    def _lint_report(self, path: str, before: Optional[str], after: str) -> str:
        if not path.endswith(".py"):
            return ""
        new_msgs = _pyflakes_messages(after)
        if before is not None:
            old_keys = {_msg_key(m) for m in _pyflakes_messages(before)}
            new_msgs = [m for m in new_msgs if _msg_key(m) not in old_keys]
        new_msgs = [m for m in new_msgs if "imported but unused" not in m]
        if not new_msgs:
            return ""
        return ("\n[LINT WARNING] The edit introduced new pyflakes issues (edit was applied):\n"
                + "\n".join(f"  {m}" for m in new_msgs[:10]))

    def list_files(self, directory: str = ".", pattern: str = "*") -> str:
        d = self._abs(directory or ".")
        if not self.ex.is_dir(d):
            raise ToolInputError(f"Directory not found: {d}")
        test = "-path" if "/" in pattern else "-name"
        cmd = (f"find {shlex.quote(d)} \\( -name .git -o -name __pycache__ -o -name '*.egg-info' \\) -prune "
               f"-o -type f {test} {shlex.quote(pattern)} -print | sort | head -n 2001")
        r = self.ex.run(cmd, timeout=60)
        files = [l for l in r.stdout.splitlines() if l]
        if not files:
            return f"No files matching '{pattern}' under {d}."
        if len(files) > 200:
            more = "2000+" if len(files) > 2000 else str(len(files))
            return "\n".join(files[:200]) + f"\n[TRUNCATED: showing 200 of {more} files - use a narrower directory or pattern]"
        return "\n".join(files)

    # ------------------------------------------------------------------ search
    def search_code(self, pattern: str, file_pattern: str = "*.py", directory: Optional[str] = None) -> str:
        if not pattern:
            raise ToolInputError("empty pattern")
        inc = [f"--include={file_pattern}"] if file_pattern and file_pattern != "*" else []
        lines, err = self._grep(inc + ["-E", "-e", pattern], directory)
        note = ""
        if err:  # invalid regex -> fixed string search
            lines, err2 = self._grep(inc + ["-F", "-e", pattern], directory)
            if err2:
                raise ToolInputError(f"search failed: {err2}")
            note = "[NOTE] pattern is not a valid extended regex; searched it as a literal string.\n"
        return note + self._format_matches(lines, f"pattern {pattern!r}")

    def search_function_or_class_definition_in_code(self, name: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\.]*", name or ""):
            raise ToolInputError("name must be a Python identifier (optionally dotted: Class.method)")
        short = name.split(".")[-1]
        regex = rf"^[[:space:]]*(async[[:space:]]+def|def|class)[[:space:]]+{short}\b"
        lines, err = self._grep(["--include=*.py", "-E", "-e", regex])
        if err:
            raise ToolInputError(err)
        return self._format_matches(lines, f"definition of {name!r}")

    def find_references(self, name: str, filepath: Optional[str] = None, line: Optional[int] = None) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
            raise ToolInputError("name must be a single Python identifier")
        note = ""
        if filepath and line:
            try:
                src = self.ex.read_text(self._abs(filepath)).splitlines()
                if not (1 <= int(line) <= len(src)) or not re.search(rf"\b{name}\b", src[int(line) - 1]):
                    note = f"[NOTE] '{name}' does not appear at {filepath}:{line}; showing all references by name.\n"
            except FileNotFoundError:
                note = f"[NOTE] {filepath} not found; showing all references by name.\n"
        lines, err = self._grep(["--include=*.py", "-w", "-F", "-e", name])
        if err:
            raise ToolInputError(err)
        if filepath:  # references in the same file first
            same = self._abs(filepath) + ":"
            lines.sort(key=lambda l: (not l.startswith(same),))
        return note + self._format_matches(lines, f"references to {name!r}")

    # ------------------------------------------------------------------ execution
    def run_command(self, command: str, workdir: str = "/testbed", timeout: int = 120) -> str:
        if not command or not command.strip():
            raise ToolInputError("empty command")
        timeout = max(1, min(int(timeout or 120), 600))
        wd = self._abs(workdir or self.root)
        r = self.ex.run(command, workdir=wd, timeout=timeout)
        head = f"exit_code: {r.exit_code}" + (f" (TIMED OUT after {timeout}s - output is partial)" if r.timed_out else "")
        return (f"{head}\nstdout:\n{_clip_block(r.stdout, MAX_CMD_CHARS, 'both')}"
                f"\nstderr:\n{_clip_block(r.stderr, MAX_CMD_CHARS // 2, 'tail')}")

    def get_patch(self) -> str:
        r = self.ex.run("git -c core.fileMode=false diff", workdir=self.root, timeout=60)
        if r.exit_code != 0:
            raise ToolInputError(f"git diff failed: {r.stderr.strip()}")
        return r.stdout

    def run_tests(self, timeout: int = 600) -> str:
        if not self.eval_script:
            raise ToolInputError("No evaluation script configured (set SWEBENCH_EVAL_SCRIPT)")
        self.ex.write_text("/tmp/smith_eval.sh", self.eval_script)
        # 2>&1: eval scripts print their markers via `set -x` (stderr) while test runners
        # write results to stdout; one merged stream keeps them in their real order.
        r = self.ex.run("bash /tmp/smith_eval.sh 2>&1", workdir=self.root, timeout=timeout)
        output = r.stdout + ("\n" + r.stderr if r.stderr.strip() else "")
        if r.timed_out:
            self._restore_test_files()
        return summarize_test_output(output, r.exit_code, r.timed_out, timeout)

    def _restore_test_files(self) -> None:
        """After a killed eval run, undo the test-patch it may have applied."""
        cmds = re.findall(r"^git checkout [0-9a-f]{7,40} .+$", self.eval_script or "", flags=re.M)
        if cmds:
            self.ex.run(cmds[-1], workdir=self.root, timeout=60)


def summarize_test_output(output: str, exit_code: int, timed_out: bool, timeout: int) -> str:
    section = output
    if START_TEST_OUTPUT in output:
        section = output.split(START_TEST_OUTPUT, 1)[1]
        section = section.split(END_TEST_OUTPUT, 1)[0]
    lines = section.splitlines()
    passed = sum(1 for l in lines if re.search(r"(PASSED|\.\.\. ok$|\[OK\]$| ok$)", l))
    failed = [l for l in lines if re.search(r"(FAILED|\.\.\. FAIL$|\.\.\. ERROR$|^ERROR[: ]|\[FAIL\]$|^FAIL:|Error$)", l)]
    header = [f"exit_code: {exit_code}" + (f" (TIMED OUT after {timeout}s)" if timed_out else "")]
    runner_lines = [l.strip() for l in lines if re.search(
        r"(\d+ (passed|failed|error)|^Ran \d+ tests?|^OK\b|^FAILED \(|tests finished:)", l.strip())]
    if runner_lines:
        header.append("test runner summary: " + " | ".join(runner_lines[-3:]))
    else:
        header.append(f"summary: ~{passed} passed, ~{len(failed)} failed/error lines detected")
    if failed:
        header.append("failing lines:\n" + "\n".join("  " + _clip_line(l) for l in failed[:25]))
    body = _clip_block(section.strip(), MAX_TEST_CHARS, "tail")
    return "\n".join(header) + "\n--- test output (tail) ---\n" + body


def _syntax_error(src: str) -> Optional[str]:
    try:
        ast.parse(src)
        return None
    except SyntaxError as e:
        return f"line {e.lineno}: {e.msg}"


def _pyflakes_messages(src: str) -> List[str]:
    try:
        from pyflakes import api, reporter
    except ImportError:
        return []
    import io
    out, err = io.StringIO(), io.StringIO()
    try:
        api.check(src, "<file>", reporter.Reporter(out, err))
    except Exception:  # noqa: BLE001 - lint is best effort
        return []
    return [l.replace("<file>:", "line ", 1) for l in out.getvalue().splitlines() if l.strip()]


def _msg_key(msg: str) -> str:
    """Line-number independent key, so moved code does not count as new."""
    return re.sub(r"^line \d+:\d*:?\s*", "", msg)
