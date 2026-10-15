"""Tools are tested independently of the agent loop and of MCP."""
import subprocess

import pytest

from smith.models import MBPPTaskInput
from smith.tools import LocalExecutor, MBPPTools, SWETools, ToolInputError


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mail.py").write_text(
        "import re\n\n\ndef is_valid(mail):\n    return bool(re.match(r'^[a-z]+@[a-z]+$', mail))\n\n\n"
        "class Mailer:\n    def send(self, m):\n        return is_valid(m)\n")
    subprocess.run("git init -q && git add -A && git -c user.email=a@b -c user.name=a commit -qm i",
                   shell=True, cwd=tmp_path, check=True)
    eval_script = (f"cd {tmp_path}\necho '>>>>> Start Test Output'\n"
                   "python3 -c \"from pkg.mail import is_valid; assert is_valid('a+b@x')\" && echo 'test_plus PASSED' "
                   "|| echo 'test_plus FAILED'\necho '>>>>> End Test Output'\n")
    return SWETools(LocalExecutor(), str(tmp_path), eval_script), tmp_path


def test_read_file_format(repo):
    t, root = repo
    out = t.read_file("pkg/mail.py", 4, 5)
    assert out.splitlines()[0] == "4: def is_valid(mail):"
    with pytest.raises(ToolInputError):
        t.read_file("missing.py")


def test_search_formats(repo):
    t, root = repo
    out = t.search_code("is_valid")
    assert f"{root}/pkg/mail.py:4 def is_valid(mail):" in out
    assert "Mailer" in t.search_function_or_class_definition_in_code("Mailer")
    refs = t.find_references("is_valid", "pkg/mail.py", 4)
    assert refs.count("is_valid") == 2


def test_list_files(repo):
    t, root = repo
    assert f"{root}/pkg/mail.py" in t.list_files(".", "*.py")


def test_edit_file_rules(repo):
    t, root = repo
    with pytest.raises(ToolInputError, match="not found"):
        t.edit_file("pkg/mail.py", "nope", "x")
    with pytest.raises(ToolInputError, match="SyntaxError"):
        t.edit_file("pkg/mail.py", "return bool(", "return bool((")
    out = t.edit_file("pkg/mail.py", "[a-z]+@", "[a-z+]+@")
    assert "Edited" in out
    out = t.edit_file("pkg/mail.py", "return is_valid(m)", "return is_valid(m) and undefined_x")
    assert "LINT WARNING" in out and "undefined_x" in out
    assert "a-z+" in t.get_patch()


def test_run_tests_and_command(repo):
    t, root = repo
    assert "FAILED" in t.run_tests()
    t.edit_file("pkg/mail.py", "[a-z]+@", "[a-z+]+@")
    assert "PASSED" in t.run_tests()
    out = t.run_command("echo hi && echo err >&2 && exit 3", workdir=str(root))
    assert "exit_code: 3" in out and "hi" in out and "err" in out
    assert "TIMED OUT" in t.run_command("sleep 5", workdir=str(root), timeout=1)


def test_mbpp_run_tests():
    task = MBPPTaskInput(task_id=1, task_definition="add", function_definition="def add(a, b):",
                         test_list=["assert add(1, 2) == 3", "assert add(2, 2) == 4"])
    tools = MBPPTools(task, timeout_s=3)
    assert tools.run_tests("def add(a, b):\n    return a + b") == "ALL TESTS PASSED (2/2)"
    out = tools.run_tests("def add(a, b):\n    return a - b")
    assert "FAILED 2/2" in out and "got -1, expected 3" in out
    assert "TIMEOUT" in tools.run_tests("def add(a, b):\n    while True: pass")
    assert "ERROR" in tools.run_tests("def add(a, b) return")


def test_run_tests_sees_stdout_between_xtrace_markers(tmp_path):
    """Real SWE-bench eval scripts print their markers with `set -x` (to stderr) while the
    test runner writes results to stdout. Both streams must be read in order, or the
    results fall outside the marker section (seen on sympy__sympy-14711)."""
    script = ("set -x\n"
              ": '>>>>> Start Test Output'\n"
              "python3 -c \"print('test_Vector', 'ok'); print('tests finished: %d passed' % (40 + 2))\"\n"
              ": '>>>>> End Test Output'\n")
    out = SWETools(LocalExecutor(), str(tmp_path), script).run_tests()
    assert "tests finished: 42 passed" in out
    assert "~0 passed" not in out
