"""Sandbox security & behaviour tests (mirrors what exam_sandbox.sh checks)."""
import pytest

from smith.models import SandboxConfig
from smith.sandbox import Sandbox


def cfg(**kw):
    base = dict(max_execution_time_seconds=3, max_memory_mb=256, allowed_directories=["/tmp/agent"])
    base.update(kw)
    return SandboxConfig(**base)


@pytest.fixture
async def sb():
    s = Sandbox(cfg())
    await s.start()
    yield s
    await s.close()


async def test_basic_and_persistence(sb):
    r = await sb.execute("x = 21\nprint('hello')")
    assert r.status == "ok" and "hello" in r.output
    r = await sb.execute("x * 2")
    assert r.output.strip() == "42"


async def test_allowed_import(sb):
    r = await sb.execute("import math, collections.abc\nfrom itertools import permutations\nprint(math.pi > 3)")
    assert r.status == "ok" and "True" in r.output


@pytest.mark.parametrize("code", ["import os", "import subprocess", "import sys", "from os import path",
                                  "import socket", "import ctypes", "import importlib"])
async def test_import_block(sb, code):
    r = await sb.execute(code)
    assert r.status == "error" and "ImportError" in r.error


@pytest.mark.parametrize("code", ["eval('1+1')", "exec('x=1')", "compile('1','a','eval')", "globals()",
                                  "input()", "__import__('os')", "breakpoint()"])
async def test_builtin_block(sb, code):
    r = await sb.execute(code)
    assert r.status in ("error", "violation")


@pytest.mark.parametrize("code", [
    "().__class__.__base__.__subclasses__()",
    "print.__self__",
    "(lambda: 0).__globals__",
    "def g():\n    yield 1\ng().gi_frame.f_globals",
    "getattr((), '__class__').__bases__",
    "'{0.__globals__}'.format(len)",
])
async def test_escape_attempts(sb, code):
    r = await sb.execute(code)
    assert r.status in ("error", "violation"), r.output


@pytest.mark.parametrize("code", ["import random\nrandom._os", "import typing\ntyping.sys",
                                  "import operator\noperator.attrgetter('x')",
                                  "import typing\ntyping.get_type_hints"])
async def test_module_proxy(sb, code):
    r = await sb.execute(code)
    assert r.status == "error" and "sandbox" in r.error


async def test_path_restrict(sb):
    r = await sb.execute("open('/etc/passwd').read()")
    assert r.status == "error" and "PermissionError" in r.error
    r = await sb.execute("open('/tmp/agent/../../etc/hosts').read()")
    assert r.status == "error" and "PermissionError" in r.error
    r = await sb.execute("with open('/tmp/agent/f.txt', 'w') as f:\n    f.write('ok')\nprint(open('/tmp/agent/f.txt').read())")
    assert r.status == "ok" and "ok" in r.output


async def test_network_block_even_if_socket_authorized():
    s = Sandbox(cfg(authorized_imports=["socket"]))
    await s.start()
    try:
        r = await s.execute("import socket\ns = socket.socket()\ns.connect(('1.1.1.1', 80))")
        assert r.status == "error" and "network" in r.error.lower()
        r = await s.execute("import socket\nsocket.getaddrinfo('example.com', 80)")
        assert r.status == "error"
    finally:
        await s.close()


async def test_audit_blocks_os_even_if_authorized():
    s = Sandbox(cfg(authorized_imports=["os"]))
    await s.start()
    try:
        r = await s.execute("import os\nos.system('echo pwned')")
        assert r.status == "error" and "not permitted" in r.error
        r = await s.execute("import os\nos.listdir('/etc')")
        assert r.status == "error" and "PermissionError" in r.error
    finally:
        await s.close()


async def test_timeout_partial_output(sb):
    r = await sb.execute("print('start')\nwhile True:\n    pass")
    assert r.status == "timeout"
    assert "start" in r.output
    assert "PARTIAL" in r.observation(1000)
    r = await sb.execute("print('alive')")  # sandbox still usable
    assert "alive" in r.output


async def test_timeout_hard_kill():
    s = Sandbox(cfg(max_execution_time_seconds=1))
    await s.start()
    try:
        r = await s.execute("while True:\n    try:\n        pass\n    except BaseException:\n        pass")
        assert r.status == "timeout"
        r = await s.execute("print(1)")
        assert r.output.strip() == "1"
    finally:
        await s.close()


async def test_memory_limit(sb):
    r = await sb.execute("x = bytearray(600 * 1024 * 1024)")
    assert r.status in ("memory", "crash")
    r = await sb.execute("y = bytearray(50 * 1024 * 1024)\nprint(len(y))")
    assert r.status == "ok"


async def test_final_answer(sb):
    r = await sb.execute("try:\n    final_answer('42')\nexcept Exception:\n    print('swallowed')")
    assert r.is_final and r.final_answer == "42"


async def test_system_exit_propagates(sb):
    with pytest.raises(SystemExit):
        await sb.execute("raise SystemExit(3)")


async def test_keyboard_interrupt_propagates(sb):
    with pytest.raises(KeyboardInterrupt):
        await sb.execute("raise KeyboardInterrupt")


async def test_truncation_notice(sb):
    r = await sb.execute("print('a' * 20000)")
    obs = r.observation(1000)
    assert "truncated" in obs.lower() and len(obs) < 1500


async def test_syntax_error_reported(sb):
    r = await sb.execute("def f(:\n  pass")
    assert r.status == "error" and "SyntaxError" in r.error


async def test_classes_and_dunders_still_work(sb):
    code = ("class P:\n    def __init__(self, v):\n        self._v = v\n    def __lt__(self, o):\n"
            "        return self._v < o._v\n    def __repr__(self):\n        return f'P({self._v})'\n"
            "class Q(P):\n    def __init__(self, v):\n        super().__init__(v * 2)\n"
            "print(sorted([Q(3), P(1)]), type(P(1)).__name__)")
    r = await sb.execute(code)
    assert r.status == "ok" and "[P(1), P(6)] P" in r.output


# --- format-string attribute traversal (dynamic strings bypass the AST check) ---
@pytest.mark.parametrize("code", [
    "u='_'*2\nprint(('{0.'+u+'class'+u+'.'+u+'base'+u+'}').format(1))",
    "u='_'*2\ndef f(): pass\nprint(('{0.'+u+'globals'+u+'}').format(f))",
    "u='_'*2\nprint(('{x.'+u+'class'+u+'.'+u+'mro'+u+'}').format_map({'x': 1}))",
    "u='_'*2\nprint(str.format('{0.'+u+'class'+u+'.'+u+'base'+u+'}', 1))",
    "u='_'*2\nfmt=getattr('{0.'+u+'class'+u+'.'+u+'base'+u+'}', 'format')\nprint(fmt(1))",
    "u='_'*2\nprint(('{0:{1.'+u+'class'+u+'.'+u+'base'+u+'}}').format(1, 2))",
])
async def test_format_string_attribute_leak_blocked(sb, code):
    r = await sb.execute(code)
    assert r.status == "error" and "forbidden attribute" in r.error
    assert "object" not in r.output


async def test_format_still_works(sb):
    r = await sb.execute("print('{0} {1:>3} {x[0]} {0.real}'.format(1, 2, x=[3]), '{a}'.format_map({'a': 4}), f'{5:02d}')")
    assert r.status == "ok" and "1   2 3 1 4 05" in r.output


async def test_guard_name_not_reachable(sb):
    r = await sb.execute("_smith_fmt_guard = lambda o, n: 0")
    assert r.status == "violation"


# --- final_answer cannot be cancelled by user code ---
async def test_final_answer_survives_except_baseexception(sb):
    r = await sb.execute("try:\n    final_answer('kept')\nexcept BaseException:\n    print('swallowed')")
    assert r.is_final and r.final_answer == "kept"


async def test_final_answer_first_call_wins(sb):
    r = await sb.execute("for v in ('a', 'b'):\n    try:\n        final_answer(v)\n    except BaseException:\n        pass")
    assert r.is_final and r.final_answer == "a"
    r = await sb.execute("print('next cell is normal')")
    assert r.status == "ok" and not r.is_final
