*This project has been created as part of the 42 curriculum by kpanfero and huwang

# Agent Smith

## Description

Agent Smith is an **agentic framework that solves coding tasks autonomously**. It uses an LLM
that reasons, writes Python code and runs it in a **sandbox**. The code calls tools served by
**MCP (Model Context Protocol)** servers. The agent reads the result and iterates until it calls
`final_answer(...)`.

It is applied to two benchmarks:

| Benchmark | Goal | Submitted `solution` |
|---|---|---|
| **MBPP** | write a small Python function | the function source |
| **SWE-bench Verified** | fix a real GitHub issue inside a Docker image | `git diff` patch |

The agent loop, the sandbox, the MCP bridge and the provider layer are our own code. No
agent-orchestration library is used (no smolagents, langgraph, llama-index, crewai or autogen),
and no sandboxing library either (standard library only).

## Instructions

### Requirements
* Python **3.10**, [uv](https://docs.astral.sh/uv/)
* Docker (SWE-bench only)
* At least one free-tier API key for an OpenAI-compatible provider

### Install
```bash
cd student
uv sync                    # add --extra dev for pytest
cp .env.example .env       # then fill in your keys
```
Keys are **only** read from environment variables or a `.env` file, never from the code.
Several keys per provider are supported and rotated automatically:
`OPENROUTER_API_KEY`, `OPENROUTER_API_KEY_2`, … or `OPENROUTER_API_KEYS=k1,k2`.

### Sandbox REPL
```bash
uv run sandbox                                                     # default config
uv run sandbox sandbox_template.json                               # custom config
uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json
uv run sandbox --mcp-server http://127.0.0.1:8001/mcp              # streamable HTTP
uv run sandbox --mcp-stdio "python mcp_tools_swebench.py" sandbox_template.json
uv run sandbox --mcp-stdio "python mcp_tools_swebench.py" --manual # print the generated manual
```
Each entry runs under the same restrictions as the agent. `exit` or Ctrl+D quits.
The MCP servers can also be started on their own over HTTP:
`python mcp_tools_mbpp.py --transport streamable-http --port 8001` (the endpoint is `/mcp`).

### MBPP
```bash
cd moulinette && uv run moulinette_eval dump mbpp --output ../cache/mbpp_task.json
cd ../student && uv run python -m agent_mbpp --task-file ../cache/mbpp_task.json \
   --output ../cache/mbpp_solution.json \
   --model-name "qwen/qwen3-coder:free" --provider-url "https://openrouter.ai/api/v1"
cd ../moulinette && uv run moulinette_eval validate mbpp ../cache/mbpp_task.json ../cache/mbpp_solution.json
```

### SWE-bench
```bash
cd moulinette && uv run moulinette_eval dump swebench --output ../cache/swebench_task.json
cd ../student && uv run python -m agent_swebench --task-file ../cache/swebench_task.json \
   --output ../cache/swebench_solution.json \
   --model-name "qwen/qwen3-coder:free" --provider-url "https://openrouter.ai/api/v1"
cd ../moulinette && uv run moulinette_eval validate swebench ../cache/swebench_task.json ../cache/swebench_solution.json
```
Common options:
* `--env-file PATH` loads a `.env` file.
* `--provider NAME` picks a provider from `config/models.json`, as an alternative to `--provider-url`.
* `--api-key-env VAR` sets the name of the key variable.
* `--sandbox-config FILE` loads a custom sandbox configuration.
* `--max-iterations N` lowers the iteration limit.
* `--mcp-stdio CMD` or `--mcp-server URL` plugs in another MCP server.
* `-v` turns on verbose logs.

SWE-bench only:
* `--use-hints` adds `hints_text` to the prompt (off by default).
* `--container-network` gives the container network access (off by default).
* `--local-repo PATH` runs the tools on a local checkout instead of Docker. It is for development only.

A `solution.json` is **always** written, even after a crash or Ctrl+C.

### Tests
```bash
uv run --extra dev pytest -q      # sandbox security, tools, extraction, agent loop (offline)
```

## System architecture

```
                 ┌───────────────────────── agent process ──────────────────────────┐
  task.json ───▶ │ agent_mbpp / agent_swebench (CLI, limits, container life-cycle)  │
                 │        │                                                         │
                 │        ▼                                                         │
                 │  CodeAgent (smith/agent/loop.py)                                 │
                 │   Memory ─▶ LLMClient ─────────── HTTPS ──────────▶ LLM provider │
                 │   (budget)  (smith/llm: key rotation, retries, usage)            │
                 │        │ response                                                │
                 │        ▼                                                         │
                 │  extract_code (python / XML / JSON / ReAct → python)             │
                 │        │ code                                                    │
                 │        ▼                                                         │
                 │  Sandbox (parent side) ◀──── JSON lines ────▶ worker process     │
                 │        │  services tool calls                  (python -I,       │
                 │        ▼                                        restricted)      │
                 │  MCPBridge (MCP client) ── stdio / streamable HTTP ──┐           │
                 └──────────────────────────────────────────────────────│───────────┘
                                                                        ▼
                               mcp_tools_mbpp.py / mcp_tools_swebench.py (MCP servers)
                                         │ smith/tools (usable without the agent)
                                         ▼
                               local subprocess  /  docker exec into the SWE-bench container
```

```
smith/
  models.py        contract models (StepMetrics, SolutionOutput, task inputs), SandboxConfig, RunLimits
  config.py        .env loading, multi-key discovery, provider resolution (config/models.json)
  llm/             LLMClient ABC, OpenAI-compatible client, KeyRing (rotation), retries
  agent/           loop.py, memory.py (token budget), extraction.py, prompts.py
  sandbox/         sandbox.py (parent), worker.py (child), policy.py (AST rules),
                   mcp_bridge.py, manual.py, cli.py (REPL)
  tools/           executor.py (local/docker), swe_tools.py, mbpp_tools.py
  docker_env.py    SWE-bench container start / cleanup
  runner.py        shared CLI plumbing (always writes solution.json)
mcp_tools_mbpp.py, mcp_tools_swebench.py   MCP servers (thin wrappers over smith/tools)
config/            models.json, sandbox_mbpp.json, sandbox_swebench.json
scripts/benchmark.py                       model × task matrix + report tables
```

To switch providers, add an entry to `config/models.json`. A provider that is not
OpenAI-compatible needs a new `LLMClient` subclass registered in `smith/llm/__init__.py`.

## Agent loop

Each iteration is one **Thought → Code → Observation** cycle.

1. **Budget check.** Token limits are cumulative and every request re-sends the history. Before each
   call, the agent computes the remaining input and output budgets and the remaining time.
   `Memory.render()` builds the largest prompt that fits:
   * it keeps the last *k* steps verbatim;
   * it condenses older steps;
   * it then drops the oldest steps, with a marker left in their place.

   Token estimates are calibrated on the real `usage` numbers the provider returns. If even the
   minimal prompt does not fit, the loop stops before going over the limit.
2. **LLM call** with the stop sequences `<end_code>` and `Observation:`. The model therefore cannot
   write fake observations. `max_tokens` is capped by the remaining output budget.
   * 429 or quota errors move to the next key, honouring `Retry-After`.
   * 401 or 403 disable the key.
   * 5xx errors and timeouts use exponential backoff.

   Retries are counted per step.
3. **Extraction** reads fenced Python blocks first, then unclosed fences, `<code>` tags,
   Anthropic XML `<invoke>`, Hermes `<tool_call>` JSON, ReAct `Action:`/`Action Input:`, and
   finally bare code. Non-Python formats are converted to Python calls. Every unusual
   interpretation, or a missing code block, is **reported to the LLM**.
4. **Execution** in the sandbox. The observation is the printed output plus explicit notices for
   timeout (partial output), truncation, policy violations, crashes and memory errors. Lint and
   syntax feedback comes from `edit_file`.
5. **`final_answer(x)`** is checked by a validator before it is accepted:
   * MBPP: the answer must parse and define the expected function.
   * SWE-bench: the answer must be a non-empty `git diff`.

   A rejected answer is explained to the LLM, and the loop continues.
6. **Iteration discipline.** The prompt says to submit as soon as the tests pass. The last steps
   carry a `[BUDGET]` warning.
7. **End of the loop.** If the loop ends without a final answer, a fallback submits the best
   available result, with `success=false`:
   * MBPP: the last candidate function, preferring one that passed `run_tests`.
   * SWE-bench: the current `get_patch()`.

Every step records `llm_output`, `sandbox_input`, `sandbox_output`, tokens, latency, retries,
model and API URL. `SolutionOutput.system_prompt` holds the full prompt.

**Prompts.** The MBPP prompt is about 400 tokens because the budget is 6k input tokens for the
whole task. It contains one worked example that tests and submits in a single step, so most tasks
take 1–2 iterations. The SWE-bench prompt teaches the methodology we use by hand:
locate → read → reproduce → minimal fix → verify → submit. It includes a worked example of a
multi-tool step.

**Time accounting (SWE-bench).** `total_time_seconds` starts when the agent loop starts. Pulling
and starting the Docker container happen before that and are logged separately on stderr.

## Sandbox design

The untrusted code runs in a **separate, long-lived worker process** (`python -I worker.py`). Its
namespace persists between steps, and it talks to the parent over private pipes (JSON lines).
Using a separate process makes it possible to:
* kill runaway code for real;
* apply OS limits without affecting the agent;
* stream partial output.

The defences are layered, and each layer is enough on its own for the common escapes:

| Layer | What it does |
|---|---|
| AST policy (`policy.py`) | rejects dunder-attribute access except a harmless allowlist (`__init__`, `__class__`, `__eq__`, …), frame/code attributes (`gi_frame`, `f_globals`, `tb_frame`, …), `__builtins__`/`__import__` names, relative and star imports, suspicious format strings. After the check, every `X.format` / `X.format_map` read is rewritten to go through a runtime guard that rejects format strings reading forbidden attributes, so a string built at runtime (`'{0.__glo' + 'bals__}'`) cannot leak them either |
| Restricted builtins | `eval`, `exec`, `compile`, `globals`, `locals`, `vars`, `input`, `breakpoint`, `exit`… raise; `open`, `getattr`, `setattr`, `__import__` are replaced by checked versions |
| Import allowlist | `authorized_imports` with globs (`math.*`); modules are returned as **read-only proxies** that hide private attributes (`random._os`), non-allowlisted sub-modules (`typing.sys`) and string-evaluating helpers (`typing.get_type_hints`, `operator.attrgetter`, `string.Formatter`) |
| Audit hooks (PEP 578) | enforced whatever the route: sockets / DNS (**no network**), `subprocess`, `os.system`/`exec`/`fork`, `ctypes`, `signal`, `setrlimit`, and file access (open, listdir, remove, rename…) **outside `allowed_directories`** (paths resolved with `realpath`, so `..` and symlinks do not escape) |
| OS limits | `RLIMIT_AS` = baseline + `max_memory_mb` (→ `MemoryError`); a soft timer (`SIGALRM`) stops code at `max_execution_time_seconds` and keeps the state; the parent **hard-kills** the process 3 s later if the code swallows the interrupt, then restarts it and says the state was lost; `RLIMIT_FSIZE` limits writes |

* The time spent inside MCP tool calls is **excluded** from the sandbox timeout. The worker pauses
  its timer, and the parent only counts worker time.
* `final_answer` is a sandbox built-in, not an MCP tool. It raises a `BaseException` subclass, so
  `except Exception` in user code cannot swallow it. The worker also records the first submitted
  answer before raising, so even `except BaseException: pass` cannot cancel the submission.
* `SystemExit` and `KeyboardInterrupt` raised by sandboxed code are re-raised in the parent. The
  agent loop catches them, stops cleanly and writes the output. Ctrl+C in the terminal kills the
  worker's process group.
* The sandbox is configured with `SandboxConfig` (Pydantic), loaded from JSON: see
  `sandbox_template.json` and `config/`. `max_output_chars` is an extra field that caps
  observations; a truncation notice is added when output is cut.

**MCP integration.** `MCPBridge` connects over stdio (`--mcp-stdio`), streamable HTTP or SSE
(`--mcp-server`). It discovers tools with pagination and turns names that are not valid Python
identifiers into valid ones. Every tool is injected into the sandbox as a Python function with
argument checking. Tools return strings; a tool error raises `ToolError` inside the sandbox.
Resources and prompts are exposed as `list_resources()`, `read_resource(uri)`, `list_prompts()`
and `get_prompt(name, arguments)`. The **manual** in the system prompt is generated from the
connected server's schemas: names, typed signatures with defaults, descriptions and server
instructions. An unknown MCP server is therefore documented automatically.

## Tool implementation details

The tools live in `smith/tools/` and **work without the agent or MCP**: `SWETools(executor, repo_root)`.
The MCP servers are thin wrappers around them. For SWE-bench, the sandbox stays on the host and
the tools go into the container through `docker exec`. That is option (b) of the subject. Each
command runs under `timeout -s KILL` inside the container, with the `testbed` conda env activated.
The container is started with `--network none`, so solutions cannot be fetched from the internet.
It is removed with `docker rm -f` in a `finally` block, which also runs on SIGTERM or Ctrl+C.

| Tool | Behaviour |
|---|---|
| `read_file(filepath, start_line, end_line)` | `<n>: <line>` format, at most 300 lines per call, with a notice that says how to read the next part |
| `edit_file(filepath, old_str, new_str)` | exact, unique match. It lists the lines where the match occurs when ambiguous, and gives a "did you mean line N" hint when there is no match. Python edits that would **introduce a SyntaxError are rejected** (the file is left unchanged). **New pyflakes warnings** are reported. `old_str=''` creates a file. It returns a numbered snippet of the edited region. |
| `list_files(directory, pattern)` | recursive glob, prunes `.git`/`__pycache__`, capped at 200 entries with a notice |
| `search_code(pattern, file_pattern)` | `grep -rnE`, output `/abs/path:<line> <content>`; an invalid regex falls back to a literal search with a note; capped at 80 matches |
| `search_function_or_class_definition_in_code(name)` | `def`/`async def`/`class` regex, same format |
| `find_references(name, filepath, line)` | whole-word search in `*.py`, same format; hits in the starting file come first; a note if the symbol is not at `filepath:line` |
| `run_tests()` | runs the task's eval script. It returns the exit code, the test runner summary, the failing lines and the tail of the output. After a timeout it restores the test files. |
| `get_patch()` | `git -c core.fileMode=false diff` |
| `run_command(command, workdir, timeout)` | `exit_code`, `stdout`, `stderr` (truncated with notices) |
| MBPP `run_tests(code, tests=None)` | runs each assert separately in a limited child interpreter (rlimits and audit hook). A failure reports `got X, expected Y`. |

## Benchmark results and analysis

See **[BENCHMARK_REPORT.md](BENCHMARK_REPORT.md)**. The raw `solution.json` files are in
`benchmarks/runs/<tag>/<model>/<task>/`, and `scripts/benchmark.py` runs the matrix and
regenerates the tables from those files.

## Resources

* smolagents, *Code agents* concept: https://huggingface.co/docs/smolagents/conceptual_guides/intro_agents
* *Executable Code Actions Elicit Better LLM Agents* (CodeAct), Wang et al., 2024
* *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering*, Yang et al., 2024
* mini-SWE-agent (a minimal bash-only SWE agent): https://github.com/SWE-agent/mini-swe-agent
* SWE-bench and SWE-bench Verified: https://www.swebench.com
* MBPP: *Program Synthesis with Large Language Models*, Austin et al., 2021
* Model Context Protocol specification and Python SDK: https://modelcontextprotocol.io
* PEP 578, Python runtime audit hooks: https://peps.python.org/pep-0578/
* Python `resource`, `signal` and `ast` module documentation

### AI usage

An AI assistant (Claude) was used as a coding partner:
* **Code:** occasional help on boilerplate and small functions"
* **Review and fixes:** reviewing the project against the subject, testing the sandbox, and fixing four bugs (each with a regression test).
* **Set-up and benchmarks:** explaining the 42 environment, and drafting `BENCHMARK_REPORT.md` from our own benchmark results.
* **Learning:** explaining the architecture before the defense.

We ran all agents, tests and benchmarks ourselves, checked every result, and chose the final model.

