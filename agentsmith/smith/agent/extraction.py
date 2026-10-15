"""Extract executable Python from an LLM response.

Supported formats (first match wins):
  1. Fenced python blocks          ```python ... ```  (all blocks are concatenated)
  2. Unclosed fenced block         ```python ...  <EOF>          -> malformed, interpreted
  3. <code> ... </code> tags
  4. Anthropic-style XML           <invoke name="t"><parameter name="p">v</parameter></invoke>
  5. JSON / Hermes tool calls      <tool_call>{"name": ..., "arguments": {...}}</tool_call>
  6. ReAct                         Action: t / Action Input: {...}
  7. Bare code                     the whole response parses as Python with a call -> malformed, interpreted

Non-Python formats are converted into equivalent Python calls
(``result = read_file(filepath="x")`` + ``print(result)``) so the sandbox
stays format-agnostic. Every non-standard interpretation adds a note that
is shown to the LLM.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

END_CODE = "<end_code>"

_FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+\-]*)[ \t]*\r?\n(.*?)```", re.DOTALL)
_UNCLOSED = re.compile(r"```[ \t]*(python3?|py)?[ \t]*\r?\n(.*)$", re.DOTALL | re.IGNORECASE)
_CODE_TAG = re.compile(r"<code>(.*?)(?:</code>|$)", re.DOTALL)
_INVOKE = re.compile(r"<invoke\s+name=[\"']([^\"']+)[\"']\s*>(.*?)</invoke>", re.DOTALL)
_PARAM = re.compile(r"<parameter\s+name=[\"']([^\"']+)[\"']\s*>(.*?)</parameter>", re.DOTALL)
_TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", re.DOTALL)
_REACT = re.compile(r"Action\s*:\s*([A-Za-z_][\w\-]*)\s*\n\s*Action\s*Input\s*:\s*(.*?)(?:\n\s*(?:Observation|Thought)\s*:|$)",
                    re.DOTALL)
_PY_LANGS = {"python", "py", "python3", "py3", "ipython", ""}


@dataclass
class Extraction:
    code: Optional[str]
    fmt: str
    notes: List[str] = field(default_factory=list)


def _parses(src: str) -> bool:
    try:
        ast.parse(src)
        return True
    except SyntaxError:
        return False


def _clean(code: str) -> str:
    code = code.replace(END_CODE, "")
    code = re.sub(r"\n?```\s*$", "", code.rstrip())
    return code.strip("\n")


def _coerce(value: str):
    v = value.strip()
    try:
        return json.loads(v)
    except (json.JSONDecodeError, ValueError):
        return value if "\n" in value else v


def _call(name: str, args: Dict, name_map: Dict[str, str]) -> str:
    py = name_map.get(name, re.sub(r"\W", "_", name))
    if py == "final_answer":
        val = next(iter(args.values()), "") if len(args) == 1 else args.get("answer", "")
        return f"final_answer({val!r})"
    kw = ", ".join(f"{k}={v!r}" for k, v in args.items())
    return f"result = {py}({kw})\nprint(result)"


def extract_code(text: str, name_map: Optional[Dict[str, str]] = None) -> Extraction:
    """Return the code to execute (or None) plus notes for the LLM."""
    name_map = name_map or {}
    text = text or ""
    body = text.split(END_CODE)[0] if END_CODE in text else text

    # 1. fenced blocks
    blocks, ignored = [], []
    for lang, code in _FENCE.findall(body):
        lang_l = lang.lower()
        if lang_l in _PY_LANGS and (lang_l or _parses(code)):
            blocks.append(code)
        elif lang_l:
            ignored.append(lang_l)
    if blocks:
        notes = []
        if len(blocks) > 1:
            notes.append(f"[NOTE] {len(blocks)} code blocks found; they were concatenated and run in order.")
        if ignored:
            notes.append(f"[NOTE] Non-python block(s) ignored ({', '.join(sorted(set(ignored)))}). "
                         "Run shell commands through the provided tools from Python.")
        return Extraction(_clean("\n\n".join(b.strip("\n") for b in blocks)), "fenced", notes)

    # 2. unclosed fence (response cut by a stop sequence or max_tokens)
    m = _UNCLOSED.search(body)
    if m and m.group(2).strip():
        return Extraction(_clean(m.group(2)), "unclosed_fence", [
            "[NOTE] Your code block was not closed with ```; everything after the opening fence "
            "was interpreted as Python. Always close blocks with ```<end_code>."])

    # 3. <code> tags
    m = _CODE_TAG.search(body)
    if m and m.group(1).strip():
        return Extraction(_clean(m.group(1)), "code_tag",
                          ["[NOTE] Found <code> tags instead of a ```python block; interpreted their content as Python."])

    # 4. XML invoke
    invokes = _INVOKE.findall(text)
    if invokes:
        calls = [_call(n, {k: _coerce(v) for k, v in _PARAM.findall(inner)}, name_map) for n, inner in invokes]
        code = "\n".join(calls)
        return Extraction(code, "xml_invoke", [
            f"[NOTE] XML tool call(s) converted to Python:\n{code}\nPrefer writing ```python blocks directly."])

    # 5. JSON tool_call
    tcs = _TOOL_CALL.findall(text)
    if tcs:
        calls, bad = [], 0
        for raw in tcs:
            try:
                obj = json.loads(raw)
                args = obj.get("arguments", obj.get("parameters", {}))
                if isinstance(args, str):
                    args = json.loads(args)
                calls.append(_call(obj["name"], args, name_map))
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
                bad += 1
        if calls:
            code = "\n".join(calls)
            notes = [f"[NOTE] JSON tool call(s) converted to Python:\n{code}"]
            if bad:
                notes.append(f"[NOTE] {bad} malformed <tool_call> block(s) could not be parsed and were skipped.")
            return Extraction(code, "json_tool_call", notes)

    # 6. ReAct
    m = _REACT.search(text)
    if m:
        name, raw = m.group(1), m.group(2).strip()
        try:
            args = json.loads(raw) if raw else {}
            if not isinstance(args, dict):
                args = {"answer": args} if name == "final_answer" else {"input": args}
        except json.JSONDecodeError:
            args = {"answer": raw} if name == "final_answer" else {}
        code = _call(name, args, name_map)
        return Extraction(code, "react", [f"[NOTE] ReAct 'Action' converted to Python:\n{code}"])

    # 7. bare code
    stripped = body.strip()
    if stripped and _parses(stripped):
        tree = ast.parse(stripped)
        has_call = any(isinstance(n, ast.Call) for n in ast.walk(tree))
        if has_call and not stripped.lower().startswith(("thought", "i ", "let", "the ")):
            return Extraction(_clean(stripped), "bare", [
                "[NOTE] No code fence found; the whole response parsed as Python and was executed. "
                "Use ```python ... ```<end_code> next time."])

    return Extraction(None, "none", [
        "[ERROR] No valid code block found in your response, nothing was executed. "
        "Reply with 'Thought: ...' followed by a ```python ... ```<end_code> block. "
        "To finish, call final_answer(...) inside a code block."])
