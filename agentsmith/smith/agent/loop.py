"""The agent loop: Thought -> Code -> Observation, until final_answer().

Responsibilities
----------------
* build the prompt under the remaining token budget (``Memory.render``)
* call the LLM with stop sequences (so it cannot hallucinate observations)
* extract code (any supported format) and run it in the sandbox
* feed back an explicit observation (never silent)
* enforce the hard limits: iterations, cumulative input/output tokens, wall time
* record per-step metrics and produce the ``SolutionOutput``
* on KeyboardInterrupt / SystemExit coming from the sandbox or the user:
  stop cleanly and return what was obtained (the caller writes it and exits)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional, Tuple

from smith.agent.extraction import END_CODE, extract_code
from smith.agent.memory import Memory, TokenEstimator, clip
from smith.llm.base import LLMClient, LLMError, RequestTooLargeError
from smith.models import RunLimits, SolutionOutput, StepMetrics
from smith.sandbox.sandbox import ExecutionResult, Sandbox

log = logging.getLogger("smith.agent")

# Smallest per-request prompt we accept after "request too large" errors; below this the
# agent cannot show the system prompt plus a useful amount of history.
MIN_CONTEXT_CAP = 2_500

# validator(answer) -> None if acceptable, else a message for the LLM
Validator = Callable[[str], Optional[str]]
# fallback() -> (solution, success) used when the loop ends without final_answer
Fallback = Callable[["AgentState"], Awaitable[Tuple[str, bool]]]


@dataclass
class AgentSettings:
    benchmark: str
    limits: RunLimits
    max_tokens_per_step: int = 1024
    min_tokens_per_step: int = 120
    context_cap_tokens: int = 10_000     # max prompt size for a single request
    keep_full_steps: int = 3
    max_observation_chars: int = 5000
    temperature: float = 0.0
    time_safety_s: float = 10.0          # keep this margin before the hard time limit
    stop_sequences: List[str] = field(default_factory=lambda: [END_CODE, "\nObservation:", "Observation:\n"])


@dataclass
class AgentState:
    steps: List[StepMetrics] = field(default_factory=list)
    codes: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    final_answer: Optional[str] = None
    error: Optional[str] = None


class CodeAgent:
    def __init__(self, llm: LLMClient, sandbox: Sandbox, system_prompt: str, settings: AgentSettings,
                 validator: Optional[Validator] = None, fallback: Optional[Fallback] = None):
        self.llm = llm
        self.sandbox = sandbox
        self.system_prompt = system_prompt
        self.s = settings
        self.validator = validator
        self.fallback = fallback
        self.estimator = TokenEstimator()
        self.interrupted: Optional[BaseException] = None
        self.name_map = {t.mcp_name: t.py_name for t in (sandbox.mcp.tools if sandbox.mcp else [])}

    # ------------------------------------------------------------------ helpers
    def _footer(self, it: int, st: AgentState) -> str:
        lim = self.s.limits
        left = lim.max_iterations - it + 1
        out_left = lim.max_output_tokens - st.output_tokens
        if left <= 1:
            return "[BUDGET] This is your LAST step: call final_answer(...) now with your best answer."
        if left <= 3 or out_left < 3 * self.s.min_tokens_per_step:
            return f"[BUDGET] Only {left} step(s) left. Wrap up and call final_answer(...) soon."
        return ""

    async def _run_code(self, code: str, deadline: float) -> ExecutionResult:
        remaining = deadline - time.monotonic()
        if remaining <= 1:
            return ExecutionResult(status="error", error="[TIME] No time left to execute code.")
        async def guarded():
            # asyncio tasks re-raise SystemExit/KeyboardInterrupt straight out of the event
            # loop; capture them as values and re-raise here, inside the agent loop.
            try:
                return await self.sandbox.execute(code)
            except (SystemExit, KeyboardInterrupt) as e:
                return e

        try:
            res = await asyncio.wait_for(guarded(), timeout=remaining)
        except asyncio.TimeoutError:
            await self.sandbox.restart()
            return ExecutionResult(status="timeout", notes=["[TIMEOUT] Task time budget exhausted during execution."])
        if isinstance(res, BaseException):
            raise res
        return res

    # ------------------------------------------------------------------ main loop
    async def run(self, task_id: str, task_prompt: str) -> SolutionOutput:
        t_start = time.monotonic()
        deadline = t_start + self.s.limits.max_time_seconds - self.s.time_safety_s
        if hasattr(self.llm, "deadline"):
            self.llm.deadline = deadline
        st = AgentState()
        memory = Memory(self.system_prompt, task_prompt, keep_full=self.s.keep_full_steps)
        stop_reason = "max_iterations"
        context_cap = self.s.context_cap_tokens   # may shrink after RequestTooLargeError
        try:
            for it in range(1, self.s.limits.max_iterations + 1):
                if time.monotonic() >= deadline:
                    stop_reason = "time budget exhausted"
                    break
                in_left = self.s.limits.max_input_tokens - st.input_tokens
                out_left = self.s.limits.max_output_tokens - st.output_tokens
                if out_left < self.s.min_tokens_per_step:
                    stop_reason = "output token budget exhausted"
                    break
                max_tokens = min(self.s.max_tokens_per_step, out_left)
                try:
                    resp = None
                    while resp is None:
                        cap = context_cap
                        provider_cap = getattr(self.llm, "max_request_tokens", None)
                        if provider_cap:   # known provider limit on prompt + max_tokens
                            cap = min(cap, provider_cap - max_tokens)
                        messages = memory.render(min(cap, in_left), self.estimator, self._footer(it, st))
                        if messages is None:
                            break
                        try:
                            resp = await self.llm.complete(messages, max_tokens=max_tokens,
                                                           stop=self.s.stop_sequences, temperature=self.s.temperature)
                        except RequestTooLargeError as e:
                            # The provider caps the size of a single request (e.g. Groq free tier:
                            # prompt + max_tokens <= tokens-per-minute). Nothing was generated, so
                            # shrink the prompt for this and all later steps and resend.
                            st.requests += 1
                            new_cap = (e.limit - max_tokens - 300) if e.limit else int(context_cap * 0.6)
                            new_cap = min(new_cap, int(context_cap * 0.85))
                            if new_cap < MIN_CONTEXT_CAP:
                                raise
                            log.warning("step %d: request too large for the provider; prompt cap %d -> %d tokens",
                                        it, context_cap, new_cap)
                            context_cap = new_cap
                    if messages is None:
                        stop_reason = "input token budget exhausted"
                        break
                except LLMError as e:
                    st.error = f"LLM error: {e}"
                    st.requests += 1
                    stop_reason = "llm error"
                    log.error("step %d: %s", it, e)
                    break
                st.requests += resp.requests
                st.input_tokens += resp.input_tokens
                st.output_tokens += resp.output_tokens
                if not resp.usage_estimated:
                    self.estimator.calibrate(messages, resp.input_tokens)

                llm_text = resp.text or ""
                ext = extract_code(llm_text, self.name_map)
                result: Optional[ExecutionResult] = None
                if ext.code is None:
                    observation = "\n".join(ext.notes)
                    if resp.finish_reason == "length":
                        observation += "\n[NOTICE] Your reply hit the max_tokens limit; be more concise."
                else:
                    result = await self._run_code(ext.code, deadline)
                    observation = "\n".join(ext.notes + [result.observation(self.s.max_observation_chars)])
                    if result.is_final:
                        # Keep what the cell printed before final_answer (e.g. run_tests results):
                        # the LLM needs it if the answer is rejected, and evaluators read it in
                        # sandbox_output to check that the submission was really tested.
                        printed = [result.observation(self.s.max_observation_chars)] if result.output.strip() else []
                        problem = self.validator(result.final_answer) if self.validator else None
                        if problem:
                            observation = "\n".join(ext.notes + printed + [f"[REJECTED final_answer] {problem}"])
                        else:
                            st.final_answer = result.final_answer
                            observation = "\n".join(ext.notes + printed + ["final_answer accepted."])

                st.steps.append(StepMetrics(
                    step=it, input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
                    request_time_ms=round(resp.request_time_ms, 1), api_url=resp.api_url,
                    model_name=resp.model_name, llm_output=llm_text, sandbox_input=ext.code or "",
                    sandbox_output=observation, retries=resp.retries,
                ))
                st.codes.append(ext.code or "")
                st.observations.append(observation)
                log.info("step %d | in=%d out=%d | total in=%d out=%d | %s", it, resp.input_tokens,
                         resp.output_tokens, st.input_tokens, st.output_tokens,
                         clip(observation.replace("\n", " "), 160))
                if st.final_answer is not None:
                    stop_reason = "final_answer"
                    break
                assistant_msg = llm_text.split(END_CODE)[0].rstrip()
                if ext.code is not None and "```" in assistant_msg and not assistant_msg.endswith("```"):
                    assistant_msg += "\n```"
                memory.add(assistant_msg + END_CODE if ext.code else assistant_msg, observation)
        except (KeyboardInterrupt, SystemExit) as e:
            # Propagated from the sandbox (or Ctrl+C): stop the loop cleanly.
            self.interrupted = e
            stop_reason = f"interrupted ({type(e).__name__})"
            st.error = f"Agent interrupted by {type(e).__name__}"
        log.info("loop finished: %s", stop_reason)

        success = st.final_answer is not None
        solution = st.final_answer or ""
        if not success and self.fallback is not None and self.interrupted is None:
            try:
                solution, success = await self.fallback(st)
                if st.error is None:
                    st.error = f"No final_answer ({stop_reason}); fallback solution submitted"
            except Exception as e:  # noqa: BLE001
                st.error = (st.error or "") + f" | fallback failed: {e}"
        elif not success and st.error is None:
            st.error = f"No final_answer ({stop_reason})"

        return SolutionOutput(
            task_id=task_id, benchmark=self.s.benchmark, success=bool(success and solution),
            solution=solution, iterations=len(st.steps), total_requests=st.requests,
            total_input_tokens=st.input_tokens, total_output_tokens=st.output_tokens,
            total_time_seconds=round(time.monotonic() - t_start, 3), steps=st.steps,
            system_prompt=self.system_prompt, error=st.error if not st.final_answer else None,
        )
