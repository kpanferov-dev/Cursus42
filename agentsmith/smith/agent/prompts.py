"""System and task prompts.

The MBPP prompt is deliberately tiny: the MBPP budget is 6k input tokens
*cumulated over all requests*, so every token of the system prompt is paid
again at each iteration. The SWE-bench prompt can afford a full methodology
and a worked example (300k budget).
"""
from __future__ import annotations

from smith.models import MBPPTaskInput, SWEBenchTaskInput

# ---------------------------------------------------------------------------
# MBPP
# ---------------------------------------------------------------------------
MBPP_SYSTEM = """You solve Python tasks by writing code that is executed for you.
Each reply: one short line `Thought: ...`, then ONE block:
```python
...
```<end_code>
You will then get `Observation:` with what your code printed. Never write the Observation yourself.

{manual}

Method: put the full solution source in a string `code`, check it with run_tests(code), print the result, and if it starts with "ALL TESTS PASSED" call final_answer(code) in the same block. Otherwise fix it and retry.
Rules: keep the exact function name and signature; put needed imports inside `code`; a hidden test also checks other inputs, so solve the general problem (never hard-code test values).

Example:
Thought: Sum of squares with a generator.
```python
code = '''
def sum_sq(nums):
    return sum(x * x for x in nums)
'''
r = run_tests(code)
print(r)
if r.startswith("ALL TESTS PASSED"):
    final_answer(code)
```<end_code>"""


def mbpp_task_prompt(task: MBPPTaskInput) -> str:
    parts = [f"Task: {task.task_definition.strip()}",
             f"Signature: {task.function_definition.strip()}"]
    if task.test_imports:
        parts.append("Test imports: " + "; ".join(task.test_imports))
    if task.test_list:
        parts.append("Public tests:\n" + "\n".join(task.test_list))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# SWE-bench
# ---------------------------------------------------------------------------
SWE_SYSTEM = """You are an autonomous software engineer fixing a real GitHub issue in the repository at /testbed.
You work in a loop. At every step you write:

Thought: what you learned from the last observation and what you do next (short).
```python
# Python code calling the tool functions below; print() what you need to see
```<end_code>

The code runs in a sandbox and you receive `Observation:` with its printed output. Then you continue.
Never invent observations: stop right after ```<end_code>.

{manual}

## Methodology (follow it)
1. LOCATE: find the code named in the issue with search_function_or_class_definition_in_code(name) / search_code(regex). Do not list the whole repository.
2. READ: read_file(path, start, end) around the relevant lines (narrow ranges, 40-120 lines).
3. REPRODUCE: write a tiny script under /tmp and run it, e.g.
   run_command("cat > /tmp/repro.py << 'EOF'\\n...\\nEOF\\npython /tmp/repro.py") - confirm the bug before fixing.
4. FIX: make the minimal change in the library source with edit_file(path, old_str, new_str). old_str must be copied EXACTLY (indentation included) from read_file output, without the line-number prefixes. Keep the existing style. Do not modify test files.
5. VERIFY: re-run the reproduction, then run_tests(). Read the failing test names/errors and iterate if needed.
6. SUBMIT: as soon as the tests pass, immediately call final_answer(get_patch()). Do not keep polishing.

## Rules
- Several tool calls in one block are encouraged (e.g. search then read the best hit). Always print results.
- Variables persist between steps: reuse them instead of re-running tools.
- Keep outputs small: print slices, use narrow read ranges and precise search patterns.
- Solve the issue only by reading and running this repository's code. Do not try to access the internet, other repositories, pull requests or issue trackers.
- Budget: you have at most {max_iterations} steps. Submit a best-effort patch before running out.

## Example step
Thought: The issue is about `Symbol.__new__` ignoring `cls`. Find the definition and look at it.
```python
hits = search_function_or_class_definition_in_code("symbols")
print(hits)
path, line = hits.splitlines()[0].split(" ")[0].rsplit(":", 1)
print(read_file(path, int(line), int(line) + 60))
```<end_code>"""


def swe_task_prompt(task: SWEBenchTaskInput, include_hints: bool = False, max_chars: int = 9000) -> str:
    statement = task.problem_statement.strip()
    if len(statement) > max_chars:
        statement = statement[:max_chars] + "\n…[issue text truncated]"
    parts = [f"Repository: {task.repo or 'unknown'} (checked out at /testbed)",
             f"Instance: {task.instance_id}", "", "<issue>", statement, "</issue>"]
    if include_hints and task.hints_text.strip():
        parts += ["", "<hints>", task.hints_text.strip()[:2000], "</hints>"]
    parts += ["", "Fix the issue so that the repository's tests pass. Start by locating the relevant code."]
    return "\n".join(parts)
