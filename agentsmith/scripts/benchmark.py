"""Model x task benchmark runner + BENCHMARK_REPORT.md tables generator.

Run the matrix (dump -> agent -> validate for every model/task pair):

    uv run python scripts/benchmark.py run \\
        --moulinette-path ../moulinette \\
        --tasks sympy__sympy-14711 sympy__sympy-13480 pydata__xarray-4629 \\
        --models openrouter:qwen/qwen3-coder:free groq:moonshotai/kimi-k2-instruct \\
                 gemini:gemini-2.5-flash mistral:devstral-small-latest cerebras:qwen-3-coder-480b \\
        --tag baseline

Ablation (same tasks/model, one change):   ... --tag hints --agent-args "--use-hints"

Build the tables from every run found in benchmarks/runs:

    uv run python scripts/benchmark.py report > benchmarks/tables.md

Metrics are computed from the solution.json files only (real execution data).
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "benchmarks" / "runs"
TASKS = ROOT / "benchmarks" / "tasks"


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)


# ----------------------------------------------------------------------------- run
def cmd_run(a: argparse.Namespace) -> None:
    moul = Path(a.moulinette_path).resolve()
    TASKS.mkdir(parents=True, exist_ok=True)
    for task in a.tasks:
        tfile = TASKS / f"{task}.json"
        if not tfile.exists():
            subprocess.run(["uv", "run", "moulinette_eval", "dump", a.benchmark, "--task-id", task,
                            "--output", str(tfile)], cwd=moul, check=True)
        for spec in a.models:
            provider, model = spec.split(":", 1)
            out = RUNS / a.tag / slug(f"{provider}_{model}") / task
            out.mkdir(parents=True, exist_ok=True)
            sol = out / "solution.json"
            module = "agent_swebench" if a.benchmark == "swebench" else "agent_mbpp"
            argv = [sys.executable, "-m", module, "--task-file", str(tfile), "--output", str(sol),
                    "--model-name", model, "--provider", provider, "--no-fallback"] + shlex.split(a.agent_args or "")
            if a.env_file:
                argv += ["--env-file", a.env_file]
            print(f"[{a.tag}] {spec} x {task} ...", flush=True)
            t0 = time.time()
            with open(out / "stdout.log", "w") as so, open(out / "stderr.log", "w") as se:
                subprocess.run(argv, cwd=ROOT, stdout=so, stderr=se)
            v = subprocess.run(["uv", "run", "moulinette_eval", "validate", a.benchmark, str(tfile), str(sol)],
                               cwd=moul, capture_output=True, text=True)
            (out / "validate.log").write_text(v.stdout + v.stderr)
            meta = {"provider": provider, "model": model, "task": task, "tag": a.tag,
                    "passed": v.returncode == 0, "wall_s": round(time.time() - t0, 1)}
            (out / "result.json").write_text(json.dumps(meta, indent=2))
            print(f"   -> {'PASS' if meta['passed'] else 'FAIL'} ({meta['wall_s']}s)", flush=True)


# ----------------------------------------------------------------------------- metrics
def patch_files(patch: str) -> List[str]:
    return re.findall(r"^diff --git a/(\S+) b/", patch or "", flags=re.M)


def first_touch_step(sol: dict) -> Optional[int]:
    files = patch_files(sol.get("solution", ""))
    for st in sol.get("steps", []):
        blob = st.get("sandbox_input", "") + "\n" + st.get("sandbox_output", "")
        if files and any(f in blob for f in files):
            return st["step"]
    return None


def _failed_count(text: str) -> Optional[int]:
    if "test runner summary" not in text and "summary:" not in text:
        return None
    m = re.search(r"(\d+) failed", text)
    if m:
        return int(m.group(1))
    return 0 if re.search(r"\d+ passed|^OK\b|\[OK\]", text, flags=re.M) else None


def failure_progress(sol: dict):
    """(step where failures first decrease vs the first run, step where tests first fully pass)."""
    baseline, decrease, first_pass = None, None, None
    for st in sol.get("steps", []):
        n = _failed_count(st.get("sandbox_output", ""))
        if n is None:
            continue
        if baseline is None:
            baseline = n
        elif decrease is None and n < baseline:
            decrease = st["step"]
        if n == 0 and first_pass is None:
            first_pass = st["step"]
    return decrease, first_pass


def load_runs() -> List[dict]:
    rows = []
    for res in sorted(RUNS.glob("*/*/*/result.json")):
        meta = json.loads(res.read_text())
        sol_path = res.parent / "solution.json"
        sol = json.loads(sol_path.read_text()) if sol_path.exists() else {}
        steps = sol.get("steps", [])
        decrease, first_pass = failure_progress(sol)
        rows.append({
            **meta, "iterations": sol.get("iterations", 0),
            "in_tok": sol.get("total_input_tokens", 0), "out_tok": sol.get("total_output_tokens", 0),
            "time_s": sol.get("total_time_seconds", 0.0), "requests": sol.get("total_requests", 0),
            "retries": sum(s.get("retries", 0) for s in steps),
            "latencies": [s.get("request_time_ms", 0) for s in steps],
            "llm_error": "LLM error" in (sol.get("error") or ""),
            "first_touch": first_touch_step(sol), "fail_decrease": decrease, "first_pass": first_pass,
            "discipline": (sol.get("iterations", 0) - first_pass) if first_pass else None,
        })
    return rows


def cmd_report(a: argparse.Namespace) -> None:
    rows = load_runs()
    if not rows:
        print("No runs found in benchmarks/runs - run `scripts/benchmark.py run` first.")
        return
    fmt = lambda v: "-" if v is None else str(v)  # noqa: E731
    print("## Results (model x task)\n")
    print("| tag | model | task | result | iterations | input tok | output tok | time (s) |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['tag']} | {r['provider']}:{r['model']} | {r['task']} | {'PASS' if r['passed'] else 'FAIL'} | "
              f"{r['iterations']} | {r['in_tok']} | {r['out_tok']} | {r['time_s']:.0f} |")

    print("\n## Provider reliability\n")
    print("| model | runs | solved | avg latency / request (ms) | retries | runs aborted by LLM errors |")
    print("|---|---|---|---|---|---|")
    groups: Dict[str, List[dict]] = {}
    for r in rows:
        groups.setdefault(f"{r['provider']}:{r['model']}", []).append(r)
    for name, rs in groups.items():
        lat = [x for r in rs for x in r["latencies"]]
        print(f"| {name} | {len(rs)} | {sum(r['passed'] for r in rs)}/{len(rs)} | "
              f"{statistics.mean(lat):.0f} | {sum(r['retries'] for r in rs)} | {sum(r['llm_error'] for r in rs)} |"
              if lat else f"| {name} | {len(rs)} | 0/{len(rs)} | - | - | {sum(r['llm_error'] for r in rs)} |")

    print("\n## Intermediary metrics\n")
    print("| tag | model | task | first step touching a patched file | failures first decrease | "
          "tests first pass | iterations after first pass |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['tag']} | {r['provider']}:{r['model']} | {r['task']} | {fmt(r['first_touch'])} | "
              f"{fmt(r['fail_decrease'])} | {fmt(r['first_pass'])} | {fmt(r['discipline'])} |")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--moulinette-path", required=True)
    r.add_argument("--benchmark", default="swebench", choices=["swebench", "mbpp"])
    r.add_argument("--tasks", nargs="+", required=True)
    r.add_argument("--models", nargs="+", required=True, help="provider:model entries")
    r.add_argument("--tag", default="baseline")
    r.add_argument("--agent-args", default="")
    r.add_argument("--env-file", default=None)
    sub.add_parser("report")
    a = p.parse_args()
    cmd_run(a) if a.cmd == "run" else cmd_report(a)


if __name__ == "__main__":
    main()
