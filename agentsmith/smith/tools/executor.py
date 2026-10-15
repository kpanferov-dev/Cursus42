"""Command executors used by the tools.

* :class:`LocalExecutor`  - runs commands on this machine (tests / local repos)
* :class:`DockerExecutor` - runs commands inside a SWE-bench container via
  ``docker exec`` (the tools bridge into Docker; the sandbox stays on the host)

Both enforce a timeout *inside* the execution environment (``timeout -s KILL``)
so that a killed client never leaves runaway processes behind.
"""
from __future__ import annotations

import os
import shlex
import signal
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

CONDA_ACTIVATE = ("if [ -f /opt/miniconda3/bin/activate ]; then "
                  "source /opt/miniconda3/bin/activate testbed >/dev/null 2>&1; fi; ")


@dataclass
class CmdResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class Executor(ABC):
    @abstractmethod
    def run(self, command: str, workdir: Optional[str] = None, timeout: float = 120,
            stdin: Optional[bytes] = None) -> CmdResult: ...

    def read_text(self, path: str) -> str:
        r = self.run(f"cat -- {shlex.quote(path)}", timeout=60)
        if r.exit_code != 0:
            raise FileNotFoundError(r.stderr.strip() or f"cannot read {path}")
        return r.stdout

    def write_text(self, path: str, content: str) -> None:
        d = os.path.dirname(path) or "."
        r = self.run(f"mkdir -p {shlex.quote(d)} && cat > {shlex.quote(path)}", timeout=60,
                     stdin=content.encode("utf-8"))
        if r.exit_code != 0:
            raise OSError(r.stderr.strip() or f"cannot write {path}")

    def exists(self, path: str) -> bool:
        return self.run(f"test -e {shlex.quote(path)}", timeout=30).exit_code == 0

    def is_dir(self, path: str) -> bool:
        return self.run(f"test -d {shlex.quote(path)}", timeout=30).exit_code == 0


def _decode(b: bytes) -> str:
    return (b or b"").decode("utf-8", "replace")


class LocalExecutor(Executor):
    """Runs ``bash -c`` locally, in its own process group (killed on timeout)."""

    def run(self, command, workdir=None, timeout=120, stdin=None) -> CmdResult:
        try:
            proc = subprocess.Popen(
                ["bash", "-c", command], cwd=workdir or None,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except (FileNotFoundError, NotADirectoryError) as e:
            return CmdResult(127, "", str(e))
        try:
            out, err = proc.communicate(input=stdin, timeout=timeout)
            return CmdResult(proc.returncode, _decode(out), _decode(err))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = proc.communicate()
            return CmdResult(-9, _decode(out), _decode(err), timed_out=True)


class DockerExecutor(Executor):
    """Runs commands in a running container through the docker CLI."""

    def __init__(self, container_id: str, activate_conda: bool = True):
        self.container_id = container_id
        self.prefix = CONDA_ACTIVATE if activate_conda else ""

    def run(self, command, workdir=None, timeout=120, stdin=None) -> CmdResult:
        inner = self.prefix + command
        argv = ["docker", "exec", "-i"]
        if workdir:
            argv += ["-w", workdir]
        argv += [self.container_id, "timeout", "-s", "KILL", str(int(max(1, timeout))),
                 "bash", "-c", inner]
        try:
            proc = subprocess.run(argv, input=stdin, capture_output=True, timeout=timeout + 30)
        except subprocess.TimeoutExpired as e:
            return CmdResult(-9, _decode(e.stdout), _decode(e.stderr), timed_out=True)
        except FileNotFoundError:
            return CmdResult(127, "", "docker CLI not found")
        timed_out = proc.returncode in (124, 137)
        return CmdResult(proc.returncode, _decode(proc.stdout), _decode(proc.stderr), timed_out=timed_out)


def executor_from_env() -> Executor:
    """Docker executor if ``SWEBENCH_CONTAINER_ID`` is set, local otherwise."""
    cid = os.environ.get("SWEBENCH_CONTAINER_ID", "").strip()
    return DockerExecutor(cid) if cid else LocalExecutor()
