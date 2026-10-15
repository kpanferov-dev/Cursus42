"""Static (AST) policy applied to LLM code before execution.

This is the *first* of several defence layers (see README "Sandbox design"):

1. AST policy (this file)      - reject escape idioms before running anything
2. Restricted builtins          - no eval/exec/compile/globals/open (open is wrapped)
3. Import allowlist + proxies   - modules are exposed through read-only proxies that
                                  hide private attributes and non-allowlisted sub-modules
4. Runtime audit hooks (PEP 578)- block sockets, processes, ctypes, and file access
                                  outside the allowed directories, whatever the route
5. OS limits                    - separate process, RLIMIT_AS memory cap, timeouts

This module is intentionally dependency-free: the worker process imports it
directly (by path) without importing the rest of the ``smith`` package.
"""
from __future__ import annotations

import _string
import ast
import fnmatch
import string
from typing import Iterable, List, Optional

# Name of the runtime guard that str.format / str.format_map accesses are routed
# through (see FormatGuard). User code may not reference it.
FMT_GUARD_NAME = "_smith_fmt_guard"
FORMAT_METHODS = frozenset({"format", "format_map"})

# Dunder attributes that are harmless and commonly used in ordinary code.
SAFE_DUNDER_ATTRS = frozenset({
    "__init__", "__name__", "__qualname__", "__doc__", "__class__", "__module__",
    "__len__", "__repr__", "__str__", "__format__", "__hash__", "__bool__",
    "__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__",
    "__iter__", "__next__", "__reversed__", "__contains__",
    "__getitem__", "__setitem__", "__delitem__", "__missing__",
    "__add__", "__radd__", "__iadd__", "__sub__", "__rsub__", "__isub__",
    "__mul__", "__rmul__", "__imul__", "__truediv__", "__rtruediv__",
    "__floordiv__", "__rfloordiv__", "__mod__", "__rmod__", "__pow__", "__rpow__",
    "__neg__", "__pos__", "__abs__", "__invert__", "__and__", "__or__", "__xor__",
    "__lshift__", "__rshift__", "__int__", "__float__", "__index__", "__round__",
    "__enter__", "__exit__", "__call__", "__new__", "__post_init__",
})

# Non-dunder attributes that lead to frames / globals / code objects.
BLOCKED_ATTRS = frozenset({
    "gi_frame", "gi_code", "gi_yieldfrom", "cr_frame", "cr_code", "cr_await",
    "ag_frame", "ag_code", "ag_await", "f_globals", "f_locals", "f_builtins",
    "f_back", "f_code", "f_trace", "tb_frame", "tb_next", "co_code", "co_consts",
    "func_globals", "func_code",
})

# Bare names that must never be referenced.
BLOCKED_NAMES = frozenset({
    "__builtins__", "__import__", "__build_class__", "__loader__", "__spec__",
    "__globals__", "__dict__", "__subclasses__", "__code__", FMT_GUARD_NAME,
})

# Suspicious string literals (format-string / getattr tricks).
BLOCKED_SUBSTRINGS = (
    "__globals__", "__subclasses__", "__builtins__", "__code__", "__import__",
    "__getattribute__", "__base__", "__mro__", "__closure__", "f_globals",
    "gi_frame", "__self__", "__func__",
)

# Callables of allowlisted modules that can defeat attribute filtering
# (they evaluate strings or fetch attributes by name).
DENIED_MODULE_ATTRS = frozenset({
    ("operator", "attrgetter"), ("operator", "methodcaller"),
    ("string", "Formatter"),
    ("typing", "get_type_hints"), ("typing", "ForwardRef"),
    ("functools", "singledispatch"), ("functools", "singledispatchmethod"),
})

# Modules that can never be imported, even if a config authorizes them.
NEVER_IMPORT = frozenset({"ctypes", "_ctypes", "gc", "sys", "builtins", "importlib", "inspect"})


class SandboxViolation(Exception):
    """Raised when code breaks the sandbox policy."""


def attr_allowed(name: str) -> bool:
    """Attribute policy shared by the AST check and the safe getattr builtin."""
    if name in BLOCKED_ATTRS:
        return False
    if name.startswith("__") and name.endswith("__"):
        return name in SAFE_DUNDER_ATTRS
    if name.startswith("__"):  # name-mangled private attribute
        return False
    return True


def import_allowed(module: str, patterns: Iterable[str]) -> bool:
    """``module`` is allowed if it matches an entry exactly or a glob (``math.*``)."""
    top = module.split(".")[0]
    if top in NEVER_IMPORT or module in NEVER_IMPORT:
        return False
    for pat in patterns:
        if module == pat or fnmatch.fnmatchcase(module, pat):
            return True
    return False


class _Checker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: List[str] = []

    def _err(self, node: ast.AST, msg: str) -> None:
        self.errors.append(f"line {getattr(node, 'lineno', '?')}: {msg}")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if not attr_allowed(node.attr):
            self._err(node, f"access to attribute '{node.attr}' is forbidden in the sandbox")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in BLOCKED_NAMES:
            self._err(node, f"use of name '{node.id}' is forbidden in the sandbox")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            self._err(node, "relative imports are not allowed")
        for alias in node.names:
            if alias.name == "*":
                self._err(node, "'from x import *' is not allowed")
            elif not attr_allowed(alias.name) or alias.name.startswith("_"):
                self._err(node, f"importing private name '{alias.name}' is forbidden")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and any(s in node.value for s in BLOCKED_SUBSTRINGS):
            self._err(node, "string literal references a forbidden dunder/frame attribute")

    def visit_Global(self, node: ast.Global) -> None:
        for n in node.names:
            if n in BLOCKED_NAMES:
                self._err(node, f"use of name '{n}' is forbidden")


def format_string_violation(fmt: str, _depth: int = 0) -> Optional[str]:
    """Return the first forbidden attribute a format string would read, or None.

    ``'{0.__globals__}'.format(f)`` reads attributes by name at runtime, so the
    AST check cannot see it when the string is built dynamically
    (``'{0.__glo' + 'bals__}'``). Every ``.attr`` in every replacement field
    (nested specs included) must pass :func:`attr_allowed`.
    """
    if _depth > 3:
        return None
    try:
        parsed = list(string.Formatter().parse(fmt))
    except ValueError:
        return None  # malformed: str.format itself will raise
    for _literal, field, spec, _conv in parsed:
        if field:
            try:
                _first, rest = _string.formatter_field_name_split(field)
                for is_attr, key in rest:
                    if is_attr and not attr_allowed(key):
                        return key
            except ValueError:
                return None
        if spec and "{" in spec:
            bad = format_string_violation(spec, _depth + 1)
            if bad:
                return bad
    return None


class FormatGuard(ast.NodeTransformer):
    """Rewrite every ``X.format`` / ``X.format_map`` read into ``_smith_fmt_guard(X, 'format')``.

    The guard returns a wrapper that checks the format string with
    :func:`format_string_violation` before formatting. Applied *after*
    :func:`check_code`, so user code can never reference the guard itself.
    """

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        if node.attr in FORMAT_METHODS and isinstance(node.ctx, ast.Load):
            call = ast.Call(func=ast.Name(id=FMT_GUARD_NAME, ctx=ast.Load()),
                            args=[node.value, ast.Constant(value=node.attr)], keywords=[])
            return ast.copy_location(call, node)
        return node


def guard_formats(tree: ast.Module) -> ast.Module:
    return ast.fix_missing_locations(FormatGuard().visit(tree))


def check_code(tree: ast.AST) -> Optional[str]:
    """Return a human readable violation report, or None if the code is acceptable."""
    checker = _Checker()
    checker.visit(tree)
    if checker.errors:
        return "SandboxViolation: code rejected before execution:\n  - " + "\n  - ".join(checker.errors[:10])
    return None
