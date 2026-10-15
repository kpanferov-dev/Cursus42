# Model Benchmark Report

All numbers below come from the `solution.json` files committed in `benchmarks/runs/<tag>/<model>/<task>/`
and were generated with `uv run python scripts/benchmark.py report` (full tables: `benchmarks/tables.md`).
Each model x task cell is a **single run** (free-tier quotas do not allow repetitions), so small
differences should not be over-interpreted.

## 1. Setup

**Models / providers** (free tiers only, no billing on any account):

| Model | Provider | Reasoning model? | Why it was included |
|---|---|---|---|
| `qwen/qwen3.8-27b` | Groq | no | fastest model in our pre-screening probe, writes code blocks without reasoning tokens |
| `openai/gpt-oss-120b` | Groq | yes (light) | large open model; tests the effect of reasoning tokens on the 10k output budget |
| `gemini-3.1-flash-lite` | Google AI Studio | no | own quota (no shared pool), very low latency in the probe |
| `gemini-3-flash-preview` | Google AI Studio | preview | stronger Gemini variant, to compare with the lite model |
| `poolside/laguna-s-2.1:free` | OpenRouter | no | code-specialised model; best OpenRouter free model on MBPP |

Model selection: we first probed every free model of each provider with one tiny request
("write `add(a, b)` in a python block") and kept models that answered with a code block. Pure
reasoning models (e.g. `cohere/north-mini-code:free`) were discarded: on MBPP they spent the whole
600-token step budget on hidden reasoning and returned an empty answer.

**Tasks** (SWE-bench Verified, all `"<15 min fix"`): `sympy__sympy-14711`, `sympy__sympy-13480`,
`pydata__xarray-4629`. These are the tasks recommended by the subject as first targets. They cover two
repositories and two test runners (sympy's `bin/test` and pytest), so a bug in test-output parsing or in
the tools shows up on at least one of them.

**Agent configuration:** limits 30 iterations / 300k input tokens / 10k output tokens / 900 s;
temperature 0; sandbox `config/sandbox_swebench.json`; hints disabled; container started with
`--network none`. Commit: `<fill in: git log --oneline -1>`.

## 2. Results (model x task, tag `baseline`)

| Model | Task | Result | Iterations | Input tok | Output tok | Time (s) |
|---|---|---|---|---|---|---|
| groq: qwen3.8-27b | xarray-4629 | **PASS** | 13 | 44 647 | 551 | 324 |
| groq: qwen3.8-27b | sympy-13480 | **PASS** | 6 | 19 733 | 376 | 111 |
| groq: qwen3.8-27b | sympy-14711 | **PASS** | 8 | 27 602 | 578 | 178 |
| gemini-3.1-flash-lite | xarray-4629 | **PASS** | 9 | 38 233 | 787 | 24 |
| gemini-3.1-flash-lite | sympy-13480 | **PASS** | 5 | 17 550 | 3 954 | 82 |
| gemini-3.1-flash-lite | sympy-14711 | **PASS** | 22 | 109 916 | 6 188 | 92 |
| groq: gpt-oss-120b | xarray-4629 | **PASS** | 13 | 43 138 | 2 840 | 255 |
| groq: gpt-oss-120b | sympy-13480 | **PASS** | 7 | 18 581 | 678 | 59 |
| groq: gpt-oss-120b | sympy-14711 | FAIL | 14 | 39 509 | 10 000 | 292 |
| openrouter: laguna-s-2.1 | xarray-4629 | FAIL | 0 | 0 | 0 | 189 |
| openrouter: laguna-s-2.1 | sympy-13480 | FAIL | 12 | 46 118 | 4 497 | 450 |
| openrouter: laguna-s-2.1 | sympy-14711 | **PASS** | 27 | 160 151 | 10 000 | 638 |
| gemini-3-flash-preview | xarray-4629 | FAIL | 0 | 0 | 0 | 190 |
| gemini-3-flash-preview | sympy-13480 | FAIL | 0 | 0 | 0 | 191 |
| gemini-3-flash-preview | sympy-14711 | FAIL | 21 | 116 556 | 5 707 | 473 |

**Solve rate:** qwen3.8-27b 3/3, gemini-3.1-flash-lite 3/3, gpt-oss-120b 2/3, laguna-s-2.1 1/3,
gemini-3-flash-preview 0/3.

## 3. Provider reliability

| Model | Runs | Solved | Avg latency / request (ms) | Retries | Runs aborted by LLM errors |
|---|---|---|---|---|---|
| groq: qwen3.8-27b | 3 | 3/3 | 532 | 20 | 0 |
| gemini-3.1-flash-lite | 3 | 3/3 | 4 622 | 0 | 0 |
| groq: gpt-oss-120b | 3 | 2/3 | 1 620 | 28 | 0 |
| openrouter: laguna-s-2.1 | 3 | 1/3 | 9 758 | 46 | 2 |
| gemini-3-flash-preview | 3 | 0/3 | 4 754 | 11 | 3 |

* **Groq** answers fastest, but its free tier has a tokens-per-minute cap. SWE-bench steps send 3–5k
  tokens each, so most steps after the first hit HTTP 429 and wait ~30 s. All retries succeeded (0 aborted
  runs), but wall time is dominated by waiting, not by the model.
* **Google AI Studio (flash-lite)** had 0 retries and 100 % availability: the most reliable provider.
  The preview model's free quota, however, ran out almost immediately: 3/3 runs were aborted by quota errors,
  two of them before the first step. Its 0/3 measures availability, not capability.
* **OpenRouter free models** use a pool shared by all users. We saw "rate-limited upstream" 429s on most
  requests (46 retries, 2 aborted runs, ~10 s average latency). Adding more OpenRouter keys does not help,
  because the limit is on the upstream provider, not on our key.

## 4. Intermediary metrics

| Model | Task | First step touching a patched file | Tests first pass (step) | Iterations after first pass |
|---|---|---|---|---|
| groq: qwen3.8-27b | xarray-4629 | 1 | 12 | 1 |
| groq: qwen3.8-27b | sympy-13480 | 1 | 5 | 1 |
| groq: qwen3.8-27b | sympy-14711 | 1 | 7 | 1 |
| gemini-3.1-flash-lite | xarray-4629 | 2 | 8 | 1 |
| gemini-3.1-flash-lite | sympy-13480 | 1 | - | - |
| gemini-3.1-flash-lite | sympy-14711 | 4 | 21 | 1 |
| groq: gpt-oss-120b | xarray-4629 | 7 | 12 | 1 |
| groq: gpt-oss-120b | sympy-13480 | 2 | 6 | 1 |
| openrouter: laguna-s-2.1 | sympy-14711 | 1 | - | - |

* **Exploration efficiency:** qwen reaches the file that ends up in the patch at step 1 on all three
  tasks (its first `search_code` call is enough). gpt-oss-120b needs up to 7 steps on xarray.
* **Submission discipline:** every model that saw the tests pass submitted in the very next step
  (1 iteration after first pass, the minimum possible since `final_answer` follows the test run).
* "-" for "tests first pass" with a PASS result (flash-lite on 13480) means the model submitted
  without running the evaluation script; the patch was correct, but the submission was less disciplined.
* The "failures first decrease" metric is empty for every run: the evaluation script only tests the
  touched module, so the agent sees either "all failing" or "all passing", with no partial progress.

## 5. Ablation study: iteration budget (30 → 10)

Same model (`groq: qwen3.8-27b`), same tasks, only `--max-iterations 10` changed (tag `maxiter10`).

| Task | 30 iterations (baseline) | 10 iterations (ablation) |
|---|---|---|
| sympy-13480 | PASS, 6 it. | PASS, 6 it. |
| sympy-14711 | PASS, 8 it. | PASS, 10 it. (budget fully used) |
| xarray-4629 | PASS, 13 it. | **FAIL**, 9 it., stopped before a fix was found |

Interpretation: easy, local fixes (13480) are unaffected. Tasks that need more exploration
(xarray needs ~12 steps to reach passing tests) fail when the budget is cut. Because the agent's
budget warning appears in the last steps, it rushes. On 14711, qwen used all 10 iterations instead of 8.
The full 30-iteration budget is therefore kept; it costs nothing when the task is easy because the agent
stops as soon as the tests pass.

A second change was also measured on the way (not a planned ablation, but a real before/after):
`run_tests` used to capture stdout and stderr separately. sympy's test results went to stdout while
the SWE-bench markers (`set -x`) went to stderr, so the agent saw "~0 passed, ~0 failed" and
submitted blindly. Merging the streams (`2>&1`) fixed it, and later runs show real
`tests finished: N passed` summaries.

## 6. Conclusions

* **Final pipeline:** `groq: qwen/qwen3.8-27b` as primary model: 3/3 solved, fewest output tokens
  (< 600 per task), patched file found at step 1, perfect submission discipline.
  **Fallback:** `gemini-3.1-flash-lite`: also 3/3, and the most reliable provider (0 retries). It uses
  more iterations on 14711 (22) and more output tokens.
* **Disregarded:**
  * `gemini-3-flash-preview`: free quota too small to finish a task (0/3, 3 aborted runs);
  * `poolside/laguna-s-2.1:free`: decent model, but the shared OpenRouter pool makes it too slow and
    unreliable for a 900 s limit (2/3 runs failed after long rate-limit waits);
  * `openai/gpt-oss-120b`: good solver, but its reasoning tokens exhausted the 10k output budget on
    14711. Risky for longer tasks.
* **General lesson:** under strict cumulative token limits and free tiers, **provider reliability and
  absence of hidden reasoning matter as much as raw model strength**.
