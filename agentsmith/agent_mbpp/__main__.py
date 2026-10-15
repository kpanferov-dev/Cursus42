"""MBPP agent CLI.

    uv run python -m agent_mbpp --task-file ../cache/mbpp_task.json \\
        --output ../cache/mbpp_solution.json \\
        --model-name "model/name" --provider-url "https://provider.api/v1"
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

from smith.agent.loop import AgentSettings, AgentState, CodeAgent
from smith.agent.prompts import MBPP_SYSTEM, mbpp_task_prompt
from smith.config import PROJECT_ROOT
from smith.llm import create_client
from smith.models import MBPPTaskInput, RunLimits, SandboxConfig, SolutionOutput
from smith.runner import base_parser, run_main
from smith.sandbox import MCPBridge, Sandbox

DEFAULT_SANDBOX = PROJECT_ROOT / "config" / "sandbox_mbpp.json"
MCP_SERVER = PROJECT_ROOT / "mcp_tools_mbpp.py"


def function_name(signature: str) -> Optional[str]:
    m = re.search(r"def\s+([A-Za-z_]\w*)\s*\(", signature)
    return m.group(1) if m else None


def make_validator(fname: Optional[str]):
    def validate(answer: str) -> Optional[str]:
        if not answer or not answer.strip():
            return "final_answer received an empty string. Pass the full source code of your solution."
        try:
            ast.parse(answer)
        except SyntaxError as e:
            return f"The submitted code has a SyntaxError (line {e.lineno}: {e.msg}). Pass valid source code."
        if fname and not re.search(rf"def\s+{re.escape(fname)}\s*\(", answer):
            return f"The submitted code does not define `{fname}`. Pass the source string, e.g. final_answer(code)."
        return None
    return validate


def candidate_from_code(code: str, fname: str) -> Optional[str]:
    """Recover a solution from a code cell written by the LLM (string literal or def)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(rf"def\s+{fname}\s*\(", node.value):
            return node.value.strip("\n")
    parts = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) or (isinstance(node, ast.FunctionDef) and node.name == fname):
            parts.append(ast.get_source_segment(code, node))
    if any(p and f"def {fname}" in p for p in parts):
        return "\n".join(p for p in parts if p)
    return None


def make_fallback(fname: Optional[str]):
    async def fallback(st: AgentState) -> Tuple[str, bool]:
        if not fname:
            return "", False
        best, best_ok = "", False
        for code, obs in zip(st.codes, st.observations):
            cand = candidate_from_code(code, fname) if code else None
            if cand:
                ok = "ALL TESTS PASSED" in obs
                if ok or not best_ok:
                    best, best_ok = cand, ok
        return best, best_ok
    return fallback


async def solve(args: argparse.Namespace) -> SolutionOutput:
    task = MBPPTaskInput.model_validate(json.loads(Path(args.task_file).read_text(encoding="utf-8")))
    config = SandboxConfig.from_json_file(args.sandbox_config or DEFAULT_SANDBOX)
    limits = RunLimits.mbpp()
    if args.max_iterations:
        limits.max_iterations = min(limits.max_iterations, args.max_iterations)

    llm = create_client(args.model_name, args.provider_url, args.provider, args.models_config, args.api_key_env,
                        use_fallbacks=not args.no_fallback)
    if args.mcp_server:
        bridge = MCPBridge(server_url=args.mcp_server)
    else:
        bridge = MCPBridge(stdio_command=args.mcp_stdio or f"python {MCP_SERVER}",
                           env={"MBPP_TASK_FILE": str(Path(args.task_file).resolve())}, cwd=str(PROJECT_ROOT))
    sandbox = Sandbox(config, bridge, mcp_extras=False)
    try:
        await sandbox.start()
        system_prompt = MBPP_SYSTEM.format(manual=sandbox.manual(compact=True))
        settings = AgentSettings(
            benchmark="mbpp", limits=limits, max_tokens_per_step=600, min_tokens_per_step=100,
            context_cap_tokens=limits.max_input_tokens, keep_full_steps=limits.max_iterations,
            max_observation_chars=config.max_output_chars, temperature=args.temperature, time_safety_s=8,
        )
        fname = function_name(task.function_definition)
        agent = CodeAgent(llm, sandbox, system_prompt, settings,
                          validator=make_validator(fname), fallback=make_fallback(fname))
        result = await agent.run(str(task.task_id), mbpp_task_prompt(task))
        if agent.interrupted is not None:
            print(f"agent interrupted: {agent.interrupted!r}", file=sys.stderr)
        return result
    finally:
        await sandbox.close()
        await llm.aclose()


def main(argv=None) -> None:
    parser = base_parser("agent_mbpp", "Agent Smith - MBPP solver")
    args = parser.parse_args(argv)
    sys.exit(run_main(args, "mbpp", solve))


if __name__ == "__main__":
    main()
