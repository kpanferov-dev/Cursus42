"""SWE-bench agent CLI.

    uv run python -m agent_swebench --task-file ../cache/swebench_task.json \\
        --output ../cache/swebench_solution.json \\
        --model-name "model/name" --provider-url "https://provider.api/v1"

Architecture: the sandbox runs on the host; the MCP tools bridge into the
task's Docker container through ``docker exec``. The container is removed
when the program ends, whatever happens.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
import time
from pathlib import Path
from typing import Tuple

from smith.agent.loop import AgentSettings, AgentState, CodeAgent
from smith.agent.prompts import SWE_SYSTEM, swe_task_prompt
from smith.config import PROJECT_ROOT
from smith.docker_env import SWEContainer
from smith.llm import create_client
from smith.models import RunLimits, SandboxConfig, SolutionOutput, SWEBenchTaskInput
from smith.runner import base_parser, run_main
from smith.sandbox import MCPBridge, Sandbox

log = logging.getLogger("smith.swebench")

DEFAULT_SANDBOX = PROJECT_ROOT / "config" / "sandbox_swebench.json"
MCP_SERVER = PROJECT_ROOT / "mcp_tools_swebench.py"


def validate_patch(answer: str):
    if not answer or not answer.strip():
        return ("final_answer received an EMPTY patch: no tracked file was modified. "
                "Fix the bug with edit_file() first, then call final_answer(get_patch()).")
    if "diff --git" not in answer:
        return "final_answer expects the git diff returned by get_patch(). Call final_answer(get_patch())."
    return None


def make_fallback(bridge: MCPBridge):
    async def fallback(st: AgentState) -> Tuple[str, bool]:
        """Submit whatever is in the working tree when the loop ran out of budget."""
        patch = await bridge.call("tool", "get_patch", {})
        return (patch, False) if patch.strip() else ("", False)
    return fallback


async def solve(args: argparse.Namespace) -> SolutionOutput:
    task = SWEBenchTaskInput.model_validate(json.loads(Path(args.task_file).read_text(encoding="utf-8")))
    config = SandboxConfig.from_json_file(args.sandbox_config or DEFAULT_SANDBOX)
    limits = RunLimits.swebench()
    if args.max_iterations:
        limits.max_iterations = min(limits.max_iterations, args.max_iterations)
    llm = create_client(args.model_name, args.provider_url, args.provider, args.models_config, args.api_key_env,
                        use_fallbacks=not args.no_fallback)

    container = None if args.local_repo else SWEContainer(task.docker_image, task.instance_id,
                                                           network=args.container_network)
    tmpdir = tempfile.TemporaryDirectory(prefix="smith_swe_")
    sandbox = None
    try:
        t0 = time.monotonic()
        eval_path = Path(tmpdir.name) / "eval.sh"
        eval_path.write_text(task.eval_script, encoding="utf-8")
        if container is not None:
            env = {"SWEBENCH_CONTAINER_ID": container.start(), "SWEBENCH_REPO_ROOT": "/testbed"}
        else:  # development mode: tools run on a local checkout, no Docker
            env = {"SWEBENCH_CONTAINER_ID": "", "SWEBENCH_REPO_ROOT": str(Path(args.local_repo).resolve())}
        env["SWEBENCH_EVAL_SCRIPT"] = str(eval_path)
        log.info("environment ready in %.1fs", time.monotonic() - t0)
        if args.mcp_server:
            bridge = MCPBridge(server_url=args.mcp_server)
        else:
            bridge = MCPBridge(stdio_command=args.mcp_stdio or f"python {MCP_SERVER}", env=env,
                               cwd=str(PROJECT_ROOT))
        sandbox = Sandbox(config, bridge, mcp_extras=True)
        await sandbox.start()
        system_prompt = SWE_SYSTEM.format(manual=sandbox.manual(), max_iterations=limits.max_iterations)
        settings = AgentSettings(
            benchmark="swebench", limits=limits, max_tokens_per_step=900, min_tokens_per_step=150,
            context_cap_tokens=min(9_500, limits.max_input_tokens // limits.max_iterations),
            keep_full_steps=3, max_observation_chars=config.max_output_chars,
            temperature=args.temperature, time_safety_s=20,
        )
        agent = CodeAgent(llm, sandbox, system_prompt, settings, validator=validate_patch,
                          fallback=make_fallback(bridge))
        result = await agent.run(task.instance_id, swe_task_prompt(task, include_hints=args.use_hints))
        if agent.interrupted is not None:
            print(f"agent interrupted: {agent.interrupted!r}", file=sys.stderr)
        return result
    finally:
        if sandbox is not None:
            await sandbox.close()
        if container is not None:
            container.cleanup()
        tmpdir.cleanup()
        await llm.aclose()


def main(argv=None) -> None:
    parser = base_parser("agent_swebench", "Agent Smith - SWE-bench solver")
    parser.add_argument("--use-hints", action="store_true", help="include hints_text in the prompt")
    parser.add_argument("--container-network", action="store_true",
                        help="give the container network access (disabled by default)")
    parser.add_argument("--local-repo", default=None,
                        help="development only: run the tools on a local checkout instead of Docker")
    args = parser.parse_args(argv)
    sys.exit(run_main(args, "swebench", solve))


if __name__ == "__main__":
    main()
