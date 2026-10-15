"""Sandbox worker process.

Runs as a separate, long-lived Python process (``python -I worker.py``)
started by :class:`smith.sandbox.sandbox.Sandbox`. The namespace persists
between executions so the agent can keep variables across steps.

Protocol (JSON lines):
    parent -> worker   {"type": "init", "config": {...}, "functions": [...]}
                       {"type": "exec", "id": n, "code": "..."}
                       {"type": "call_result", "call_id": k, "ok": bool, "value": str, "error": str}
                       {"type": "shutdown"}
    worker -> parent   {"type": "ready", "info": {...}}
                       {"type": "out", "text": "..."}                    (streamed stdout/stderr)
                       {"type": "call", "call_id": k, "kind": ..., "name": ..., "args": {...}}
                       {"type": "done", "id": n, "status": ..., ...}

The protocol uses private file descriptors: fd 1 is redirected to stderr so
that nothing written by C extensions can corrupt the channel.

This file must not import the ``smith`` package (it runs isolated); it loads
``policy.py`` from its own directory.
"""
import ast
import builtins
import importlib
import importlib.util
import io
import json
import linecache
import os
import resource
import signal
import sys
import traceback
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("_smith_sandbox_policy", os.path.join(_HERE, "policy.py"))
policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy)

# ---------------------------------------------------------------------------
# Protocol channel
# ---------------------------------------------------------------------------
_PROTO_OUT = os.fdopen(os.dup(1), "wb", buffering=0)
os.dup2(2, 1)  # anything written to fd 1 now goes to stderr
_PROTO_IN = os.fdopen(0, "rb", buffering=0)
_IN_BUF = io.BufferedReader(_PROTO_IN, buffer_size=1 << 16)


def _send(msg: dict) -> None:
    data = (json.dumps(msg, default=str) + "\n").encode("utf-8", "replace")
    _PROTO_OUT.write(data)


def _recv() -> dict:
    line = _IN_BUF.readline()
    if not line:
        raise SystemExit(0)  # parent went away
    return json.loads(line.decode("utf-8"))


# ---------------------------------------------------------------------------
# Control-flow exceptions (BaseException so ``except Exception`` in user code
# does not swallow them)
# ---------------------------------------------------------------------------
class FinalAnswerSignal(BaseException):
    def __init__(self, value):
        super().__init__("final_answer called")
        self.value = value


class SandboxTimeout(BaseException):
    pass


class ToolError(Exception):
    """Raised inside the sandbox when an MCP tool reports an error."""


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
CONFIG = {}
ALLOWED_DIRS = []
PY_READ_ROOTS = []
_ACTIVE = False          # True while user code runs: audit hooks enforce policy
_CALL_ID = 0
_CELL = 0
_OUT_LIMIT = 200_000     # hard cap on streamed chars per execution
_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Output capture
# ---------------------------------------------------------------------------
class _StreamWriter(io.TextIOBase):
    """Streams text to the parent (so partial output survives a hard kill)."""

    def __init__(self):
        self._buf = []
        self._size = 0
        self.total = 0
        self.dropped = False

    def writable(self):
        return True

    def write(self, s):
        if not isinstance(s, str):
            s = str(s)
        if self.total >= _OUT_LIMIT:
            self.dropped = True
            return len(s)
        s = s[: _OUT_LIMIT - self.total]
        self.total += len(s)
        self._buf.append(s)
        self._size += len(s)
        if self._size >= 4096 or "\n" in s:
            self.flush()
        return len(s)

    def flush(self):
        if self._buf:
            _send({"type": "out", "text": "".join(self._buf)})
            self._buf, self._size = [], 0

    def reset(self):
        self.flush()
        self.total = 0
        self.dropped = False


_STREAM = _StreamWriter()
sys.stdout = _STREAM
sys.stderr = _STREAM
sys.stdin = io.StringIO("")


# ---------------------------------------------------------------------------
# Filesystem policy
# ---------------------------------------------------------------------------
def _real(path) -> str:
    return os.path.realpath(os.path.abspath(os.fsdecode(path)))


def _under(path: str, roots) -> bool:
    for root in roots:
        if path == root or path.startswith(root.rstrip("/") + "/"):
            return True
    return False


def _check_path(path, write: bool) -> None:
    if isinstance(path, int):
        return
    real = _real(path)
    if _under(real, ALLOWED_DIRS):
        return
    if not write and _under(real, PY_READ_ROOTS) and real.endswith((".py", ".pyc", ".so", ".pth", ".json", ".txt")):
        return  # internal lazy imports of allowed stdlib modules
    raise PermissionError(
        f"[sandbox] access to '{os.fsdecode(path)}' denied: outside allowed directories {ALLOWED_DIRS}"
    )


def _mode_writes(mode, flags) -> bool:
    if isinstance(mode, str) and any(c in mode for c in "wax+"):
        return True
    if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        return True
    return False


# ---------------------------------------------------------------------------
# Audit hook: runtime enforcement independent of how the call was reached
# ---------------------------------------------------------------------------
_BLOCK_PREFIXES = (
    "socket.", "subprocess.", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
    "os.fork", "os.forkpty", "os.kill", "os.killpg", "os.setuid", "os.putenv", "os.unsetenv",
    "pty.", "ctypes.", "sys.addaudithook", "sys._getframe", "sys.settrace", "sys.setprofile",
    "urllib.", "http.", "ftplib.", "smtplib.", "telnetlib.", "webbrowser.", "winreg.",
    "_posixsubprocess.", "os.startfile", "resource.setrlimit", "signal.",
)
_PATH_EVENTS = {
    "os.remove": (0,), "os.rmdir": (0,), "os.rename": (0, 1), "os.replace": (0, 1),
    "os.mkdir": (0,), "os.listdir": (0,), "os.scandir": (0,), "os.chdir": (0,),
    "os.chmod": (0,), "os.chown": (0,), "os.link": (0, 1), "os.symlink": (0, 1),
    "os.truncate": (0,), "os.utime": (0,), "shutil.rmtree": (0,), "shutil.copyfile": (0, 1),
    "shutil.move": (0, 1), "os.walk": (0,), "glob.glob": (0,), "os.listxattr": (0,),
}
_WRITE_PATH_EVENTS = {"os.remove", "os.rmdir", "os.rename", "os.replace", "os.mkdir", "os.chmod",
                      "os.chown", "os.link", "os.symlink", "os.truncate", "os.utime",
                      "shutil.rmtree", "shutil.copyfile", "shutil.move"}
_BLOCKED_IMPORTS = {"ctypes", "_ctypes", "socket", "_socket", "ssl", "_ssl", "subprocess",
                    "_posixsubprocess", "multiprocessing", "pty", "urllib.request", "http.client"}


def _audit(event, args):
    if not _ACTIVE:
        return
    if event == "open":
        path = args[0]
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else None
        if path is not None:
            _check_path(path, _mode_writes(mode, flags))
        return
    if event == "import":
        name = args[0]
        if name in _BLOCKED_IMPORTS or name.split(".")[0] in {"ctypes", "_ctypes"}:
            raise ImportError(f"[sandbox] import of '{name}' is blocked")
        return
    if event in _PATH_EVENTS:
        for i in _PATH_EVENTS[event]:
            if i < len(args) and isinstance(args[i], (str, bytes, os.PathLike)):
                _check_path(args[i], event in _WRITE_PATH_EVENTS)
        return
    if event.startswith(_BLOCK_PREFIXES):
        if event.startswith("socket.") or event.startswith(("urllib.", "http.", "ftplib.", "smtplib.")):
            raise PermissionError(f"[sandbox] network access is disabled (blocked '{event}')")
        raise PermissionError(f"[sandbox] operation '{event}' is not permitted")
    if event == "builtins.input":
        raise PermissionError("[sandbox] input() is not available")


# ---------------------------------------------------------------------------
# Module proxies
# ---------------------------------------------------------------------------
class _ModuleProxy:
    """Read-only view of an allowlisted module.

    Hides private attributes (``random._os``), non-allowlisted sub-modules
    (``typing.sys``) and a few string-evaluating helpers.
    """
    __slots__ = ("_smith_mod", "_smith_name")

    def __init__(self, mod, name):
        object.__setattr__(self, "_smith_mod", mod)
        object.__setattr__(self, "_smith_name", name)

    def __getattr__(self, attr):
        name = object.__getattribute__(self, "_smith_name")
        mod = object.__getattribute__(self, "_smith_mod")
        if attr.startswith("_"):
            raise AttributeError(f"[sandbox] private attribute '{name}.{attr}' is not accessible")
        if (name.split(".")[0], attr) in policy.DENIED_MODULE_ATTRS:
            raise AttributeError(f"[sandbox] '{name}.{attr}' is disabled in the sandbox")
        value = getattr(mod, attr)
        if isinstance(value, types.ModuleType):
            sub = value.__name__
            if not policy.import_allowed(sub, CONFIG["authorized_imports"]):
                raise AttributeError(f"[sandbox] sub-module '{sub}' is not in the import allowlist")
            return _ModuleProxy(value, sub)
        return value

    def __setattr__(self, attr, value):
        raise AttributeError("[sandbox] modules are read-only")

    def __delattr__(self, attr):
        raise AttributeError("[sandbox] modules are read-only")

    def __dir__(self):
        return [a for a in dir(object.__getattribute__(self, "_smith_mod")) if not a.startswith("_")]

    def __repr__(self):
        return f"<sandboxed module '{object.__getattribute__(self, '_smith_name')}'>"


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level:
        raise ImportError("[sandbox] relative imports are not allowed")
    if not policy.import_allowed(name, CONFIG["authorized_imports"]):
        raise ImportError(
            f"[sandbox] import of '{name}' is not allowed. Authorized imports: "
            + ", ".join(CONFIG["authorized_imports"])
        )
    mod = importlib.import_module(name)
    if fromlist:
        return _ModuleProxy(mod, name)
    top = name.split(".")[0]
    return _ModuleProxy(sys.modules[top], top)


def _safe_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True):
    if not isinstance(file, (str, bytes, os.PathLike)):
        raise PermissionError("[sandbox] open() only accepts paths")
    _check_path(file, _mode_writes(mode, None))
    return builtins.open(file, mode, buffering, encoding, errors, newline, closefd)


_MISSING = object()


def _check_format(fmt):
    if isinstance(fmt, str):
        bad = policy.format_string_violation(fmt)
        if bad:
            raise AttributeError(f"[sandbox] format string reads forbidden attribute '{bad}'")


def _fmt_guard(obj, name):
    """Runtime side of policy.FormatGuard: checked str.format / str.format_map."""
    if isinstance(obj, str):
        method = getattr(obj, name)

        def bound(*args, **kwargs):
            _check_format(obj)
            return method(*args, **kwargs)
        return bound
    if isinstance(obj, type) and issubclass(obj, str):  # str.format(fmt, ...)
        method = getattr(obj, name)

        def unbound(fmt, *args, **kwargs):
            _check_format(fmt)
            return method(fmt, *args, **kwargs)
        return unbound
    return getattr(obj, name)


def _safe_getattr(obj, name, default=_MISSING):
    if not isinstance(name, str):
        raise TypeError("attribute name must be a string")
    if not policy.attr_allowed(name):
        raise AttributeError(f"[sandbox] access to attribute '{name}' is forbidden")
    if name in policy.FORMAT_METHODS and (isinstance(obj, str) or (isinstance(obj, type) and issubclass(obj, str))):
        return _fmt_guard(obj, name)
    if default is _MISSING:
        return getattr(obj, name)
    return getattr(obj, name, default)


def _safe_hasattr(obj, name):
    return policy.attr_allowed(name) and hasattr(obj, name)


def _safe_setattr(obj, name, value):
    if isinstance(obj, (_ModuleProxy, type)) or not policy.attr_allowed(name):
        raise AttributeError(f"[sandbox] setting attribute '{name}' is forbidden here")
    setattr(obj, name, value)


def _safe_delattr(obj, name):
    if isinstance(obj, (_ModuleProxy, type)) or not policy.attr_allowed(name):
        raise AttributeError(f"[sandbox] deleting attribute '{name}' is forbidden here")
    delattr(obj, name)


def _blocked(name):
    def _fn(*a, **k):
        raise PermissionError(f"[sandbox] builtin '{name}' is disabled in the sandbox")
    _fn.__name__ = name
    return _fn


_SAFE_BUILTIN_NAMES = [
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes", "callable", "chr",
    "classmethod", "complex", "dict", "dir", "divmod", "enumerate", "filter", "float",
    "format", "frozenset", "hash", "hex", "id", "int", "isinstance", "issubclass", "iter",
    "len", "list", "map", "max", "min", "next", "object", "oct", "ord", "pow", "print",
    "property", "range", "repr", "reversed", "round", "set", "slice", "sorted",
    "staticmethod", "str", "sum", "super", "tuple", "type", "zip", "memoryview",
    "True", "False", "None", "NotImplemented", "Ellipsis", "__build_class__",
]
_BLOCKED_BUILTINS = ["eval", "exec", "compile", "globals", "locals", "vars", "input",
                     "breakpoint", "help", "exit", "quit", "copyright", "credits", "license"]


def _build_builtins() -> dict:
    safe = {}
    for n in _SAFE_BUILTIN_NAMES:
        safe[n] = getattr(builtins, n)
    for n in dir(builtins):  # every exception class
        obj = getattr(builtins, n)
        if isinstance(obj, type) and issubclass(obj, BaseException):
            safe[n] = obj
    for n in _BLOCKED_BUILTINS:
        safe[n] = _blocked(n)
    safe.update({
        "__import__": _safe_import, "open": _safe_open, "getattr": _safe_getattr,
        "hasattr": _safe_hasattr, "setattr": _safe_setattr, "delattr": _safe_delattr,
        "__name__": "__main__", "ToolError": ToolError,
        policy.FMT_GUARD_NAME: _fmt_guard,
    })
    return safe


# ---------------------------------------------------------------------------
# Functions bridged to the parent (MCP tools, resources, prompts)
# ---------------------------------------------------------------------------
def _pause_timer():
    remaining, _ = signal.setitimer(signal.ITIMER_REAL, 0)
    return remaining


def _resume_timer(remaining):
    if remaining > 0:
        signal.setitimer(signal.ITIMER_REAL, remaining)


def _call_parent(kind, name, args):
    global _CALL_ID
    _CALL_ID += 1
    call_id = _CALL_ID
    _STREAM.flush()
    remaining = _pause_timer()  # MCP time does not count against the sandbox timeout
    try:
        _send({"type": "call", "call_id": call_id, "kind": kind, "name": name, "args": args})
        while True:
            msg = _recv()
            if msg.get("type") == "call_result" and msg.get("call_id") == call_id:
                break
            if msg.get("type") == "shutdown":
                raise SystemExit(0)
    finally:
        _resume_timer(remaining)
    if not msg.get("ok"):
        raise ToolError(msg.get("error") or f"{kind} '{name}' failed")
    return msg.get("value")


def _make_tool(spec):
    pyname, params = spec["name"], spec.get("params", [])
    required = set(spec.get("required", []))

    def tool(*args, **kwargs):
        if len(args) > len(params):
            raise TypeError(f"{pyname}() takes at most {len(params)} positional arguments ({len(args)} given)")
        call_args = dict(zip(params, args))
        for k, v in kwargs.items():
            if k not in params:
                raise TypeError(f"{pyname}() got an unexpected keyword argument '{k}'. Parameters: {params}")
            if k in call_args:
                raise TypeError(f"{pyname}() got multiple values for argument '{k}'")
            call_args[k] = v
        missing = [p for p in params if p in required and p not in call_args]
        if missing:
            raise TypeError(f"{pyname}() missing required argument(s): {missing}")
        return _call_parent("tool", spec["mcp_name"], call_args)

    tool.__name__ = pyname
    tool.__doc__ = spec.get("doc", "")
    return tool


_PENDING_FINAL = None  # set by final_answer(); survives `except BaseException` in user code


def final_answer(answer):
    """Submit the final answer and stop the agent loop."""
    global _PENDING_FINAL
    if callable(answer):
        raise TypeError("final_answer() expects a string (e.g. the source code), not a function object")
    value = answer if isinstance(answer, str) else str(answer)
    if _PENDING_FINAL is None:  # the first call wins
        _PENDING_FINAL = value
    raise FinalAnswerSignal(value)


def _bridge_helpers(enabled: bool) -> dict:
    if not enabled:
        return {}

    def list_resources():
        """List MCP resources (uri, name, description)."""
        return _call_parent("list_resources", "", {})

    def read_resource(uri):
        """Read an MCP resource by URI."""
        return _call_parent("read_resource", str(uri), {})

    def list_prompts():
        """List MCP prompt templates."""
        return _call_parent("list_prompts", "", {})

    def get_prompt(name, arguments=None):
        """Render an MCP prompt template."""
        return _call_parent("get_prompt", str(name), dict(arguments or {}))

    return {"list_resources": list_resources, "read_resource": read_resource,
            "list_prompts": list_prompts, "get_prompt": get_prompt}


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
NAMESPACE = {}


def _vm_size_bytes() -> int:
    try:
        with builtins.open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmSize:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass
    return 0


def _init(msg):
    global CONFIG, ALLOWED_DIRS, PY_READ_ROOTS, _TIMEOUT
    CONFIG = msg["config"]
    _TIMEOUT = int(CONFIG.get("max_execution_time_seconds", 30))
    ALLOWED_DIRS = []
    for d in CONFIG.get("allowed_directories", []):
        if d.startswith("/tmp/"):
            os.makedirs(d, exist_ok=True)
        ALLOWED_DIRS.append(_real(d))
    PY_READ_ROOTS = sorted({_real(p) for p in (sys.prefix, sys.base_prefix, sys.exec_prefix)
                            if p} | {_real(p) for p in sys.path if p and os.path.isdir(p)})
    # Pre-import allowlisted modules before any restriction applies.
    for pat in CONFIG.get("authorized_imports", []):
        base = pat.split("*")[0].rstrip(".")
        if base and policy.import_allowed(base, CONFIG["authorized_imports"]):
            try:
                importlib.import_module(base)
            except Exception:
                pass
    for d in ALLOWED_DIRS:
        if os.path.isdir(d):
            os.chdir(d)
            break
    else:
        os.chdir("/")

    NAMESPACE.clear()
    NAMESPACE["__builtins__"] = _build_builtins()
    NAMESPACE["__name__"] = "__main__"
    NAMESPACE["final_answer"] = final_answer
    names = []
    for spec in msg.get("functions", []):
        NAMESPACE[spec["name"]] = _make_tool(spec)
        names.append(spec["name"])
    NAMESPACE.update(_bridge_helpers(msg.get("mcp_extras", False)))

    # OS-level limits
    mem_mb = int(CONFIG.get("max_memory_mb", 512))
    limit = _vm_size_bytes() + mem_mb * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ValueError, OSError):
        pass
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024, 64 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ValueError, OSError):
        pass

    def _on_alarm(signum, frame):
        raise SandboxTimeout()

    signal.signal(signal.SIGALRM, _on_alarm)
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # the parent owns Ctrl+C
    sys.addaudithook(_audit)
    _send({"type": "ready", "info": {"functions": names, "memory_limit_mb": mem_mb,
                                     "allowed_directories": ALLOWED_DIRS}})


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def _format_exc(exc: BaseException) -> str:
    te = traceback.TracebackException.from_exception(exc)
    te.stack = traceback.StackSummary.from_list(
        [f for f in te.stack if f.filename != __file__ and "importlib" not in f.filename]
    )
    return "".join(te.format()).rstrip()


def _run(code: str):
    """Execute one cell. Returns a dict describing the outcome.

    If final_answer() was called but its signal was swallowed by user code
    (``except BaseException: pass``), the cell still counts as final.
    """
    global _PENDING_FINAL
    _PENDING_FINAL = None
    result = _run_cell(code)
    if _PENDING_FINAL is not None and result.get("status") not in ("final", "sysexit", "kbint"):
        result = {"status": "final", "final": _PENDING_FINAL}
    _PENDING_FINAL = None
    return result


def _run_cell(code: str):
    """Parse, check and execute one cell."""
    global _ACTIVE, _CELL
    _CELL += 1
    filename = f"<cell-{_CELL}>"
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as e:
        return {"status": "error", "error": "".join(traceback.format_exception_only(type(e), e)).rstrip()}
    violation = policy.check_code(tree)
    if violation:
        return {"status": "violation", "error": violation}
    tree = policy.guard_formats(tree)  # after the check: user code cannot name the guard

    last_expr = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last_expr = ast.Expression(tree.body.pop().value)
    linecache.cache[filename] = (len(code), None, code.splitlines(True), filename)
    body = compile(tree, filename, "exec")
    tail = compile(last_expr, filename, "eval") if last_expr else None

    _STREAM.reset()
    _ACTIVE = True
    signal.setitimer(signal.ITIMER_REAL, _TIMEOUT)
    try:
        exec(body, NAMESPACE)
        if tail is not None:
            value = eval(tail, NAMESPACE)
            if value is not None:
                print(repr(value))
        return {"status": "ok"}
    except FinalAnswerSignal as fa:
        return {"status": "final", "final": fa.value}
    except SandboxTimeout:
        return {"status": "timeout", "error": f"TimeoutError: execution exceeded {_TIMEOUT}s"}
    except MemoryError:
        return {"status": "memory",
                "error": f"MemoryError: sandbox memory limit ({CONFIG.get('max_memory_mb')} MB) exceeded"}
    except SystemExit as e:
        return {"status": "sysexit", "code": e.code if isinstance(e.code, (int, str)) else None}
    except KeyboardInterrupt:
        return {"status": "kbint"}
    except RecursionError as e:
        return {"status": "error", "error": "RecursionError: " + str(e)}
    except BaseException as e:  # noqa: BLE001 - report every error to the LLM
        return {"status": "error", "error": _format_exc(e)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        _ACTIVE = False
        _STREAM.flush()


def main():
    while True:
        try:
            msg = _recv()
        except SystemExit:
            return
        kind = msg.get("type")
        if kind == "init":
            _init(msg)
        elif kind == "exec":
            result = _run(msg["code"])
            result.update({"type": "done", "id": msg.get("id"), "output_dropped": _STREAM.dropped})
            _send(result)
        elif kind == "shutdown":
            return


if __name__ == "__main__":
    main()
