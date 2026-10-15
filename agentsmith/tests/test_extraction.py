from smith.agent.extraction import extract_code


def test_fenced():
    e = extract_code("Thought: x\n```python\nprint(1)\n```<end_code>")
    assert e.code == "print(1)" and e.fmt == "fenced" and not e.notes


def test_multiple_blocks_and_ignored_bash():
    e = extract_code("```py\na = 1\n```\n```bash\nls\n```\n```python\nprint(a)\n```")
    assert e.code == "a = 1\n\nprint(a)"
    assert any("concatenated" in n for n in e.notes) and any("bash" in n for n in e.notes)


def test_unclosed_fence():
    e = extract_code("Thought\n```python\nprint(2)\n")
    assert e.code == "print(2)" and e.fmt == "unclosed_fence" and e.notes


def test_xml_invoke():
    e = extract_code('<invoke name="read_file"><parameter name="filepath">/testbed/a.py</parameter>'
                     '<parameter name="start_line">3</parameter></invoke>')
    assert "read_file(filepath='/testbed/a.py', start_line=3)" in e.code


def test_json_tool_call_and_name_map():
    e = extract_code('<tool_call>{"name": "get-patch", "arguments": {}}</tool_call>', {"get-patch": "get_patch"})
    assert "get_patch()" in e.code


def test_react_final_answer():
    e = extract_code('Thought: done\nAction: final_answer\nAction Input: {"answer": "def f(): pass"}')
    assert e.code == "final_answer('def f(): pass')"


def test_bare_code():
    e = extract_code("print(run_tests(code))")
    assert e.fmt == "bare" and e.notes


def test_none():
    e = extract_code("I will now think about the problem.")
    assert e.code is None and "No valid code block" in e.notes[0]
