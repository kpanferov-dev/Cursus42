"""Agent-loop tests with a scripted LLM (no network, no API key)."""
from typing import List

from smith.agent.loop import AgentSettings, CodeAgent
from smith.agent.memory import Memory, TokenEstimator
from smith.llm.base import LLMClient, LLMResponse, RequestTooLargeError
from smith.llm.keys import KeyRing
from smith.models import RunLimits, SandboxConfig
from smith.sandbox import Sandbox


class ScriptedLLM(LLMClient):
    def __init__(self, replies: List[str], in_tokens: int = 300):
        super().__init__()
        self.replies = list(replies)
        self.in_tokens = in_tokens

    model_name = "scripted"
    api_url = "local://scripted"

    async def complete(self, messages, *, max_tokens, stop=None, temperature=0.0):
        text = self.replies.pop(0) if self.replies else "no code here"
        return LLMResponse(text=text, input_tokens=self.in_tokens, output_tokens=40, request_time_ms=1.0,
                           retries=0, requests=1, api_url=self.api_url, model_name=self.model_name)


def settings(**kw):
    s = AgentSettings(benchmark="mbpp", limits=RunLimits.mbpp(), context_cap_tokens=6000)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


async def run_agent(replies, **kw):
    sb = Sandbox(SandboxConfig(max_execution_time_seconds=3))
    await sb.start()
    try:
        agent = CodeAgent(ScriptedLLM(replies, kw.pop("in_tokens", 300)), sb, "SYSTEM", settings(**kw))
        return await agent.run("1", "TASK")
    finally:
        await sb.close()


async def test_final_answer_flow():
    sol = await run_agent(["Thought\n```python\nx = 6*7\nprint(x)\n```", "```python\nfinal_answer(str(x))\n```"])
    assert sol.success and sol.solution == "42" and sol.iterations == 2
    assert sol.steps[0].sandbox_output.strip() == "42"
    assert sol.total_input_tokens == 600


async def test_no_code_feedback_and_iteration_limit():
    sol = await run_agent(["just talking"] * 20, limits=RunLimits(max_iterations=3, max_input_tokens=6000,
                                                                  max_output_tokens=1500, max_time_seconds=60))
    assert not sol.success and sol.iterations == 3
    assert "No valid code block" in sol.steps[0].sandbox_output


async def test_input_budget_respected():
    sol = await run_agent(["```python\nprint('a' * 900)\n```"] * 10, in_tokens=1500)
    assert sol.total_input_tokens <= 6000


async def test_system_exit_stops_loop_cleanly():
    sol = await run_agent(["```python\nraise SystemExit(1)\n```", "```python\nfinal_answer('x')\n```"])
    assert not sol.success and "SystemExit" in (sol.error or "")


def test_memory_render_budget():
    m = Memory("S" * 400, "T" * 400, keep_full=2)
    for i in range(10):
        m.add("A" * 2000, "O" * 3000)
    est = TokenEstimator()
    msgs = m.render(2500, est)
    assert msgs is not None and est.estimate(msgs) <= 2500
    assert m.render(50, est) is None


def test_keyring_rotation():
    k = KeyRing(["a", "b", "c"])
    assert k.current() == "a"
    k.cool_down_current(30)
    assert k.current() == "b"
    k.disable_current()
    assert k.current() == "c"
    k.disable_current()
    assert k.current() == "a"  # only one left (cooling down)
    k.disable_current()
    assert k.all_disabled()


async def test_final_step_keeps_printed_output():
    """sandbox_output of the submitting step must contain what the cell printed (e.g. test results)."""
    reply = "Thought: done\n```python\nprint('ALL TESTS PASSED (2/2)')\nfinal_answer('def f():\\n    return 1')\n```"
    sol = await run_agent([reply])
    assert sol.success
    out = sol.steps[-1].sandbox_output
    assert "ALL TESTS PASSED (2/2)" in out and "final_answer accepted." in out


class TooLargeOnceLLM(ScriptedLLM):
    """Rejects the first request as too large (like Groq's HTTP 413), then answers."""

    def __init__(self, replies, limit):
        super().__init__(replies)
        self.limit = limit
        self.calls = 0

    async def complete(self, messages, *, max_tokens, stop=None, temperature=0.0):
        self.calls += 1
        if self.calls == 1:
            raise RequestTooLargeError("HTTP 413: Request too large ... Limit 6000, Requested 9431", self.limit)
        return await super().complete(messages, max_tokens=max_tokens, stop=stop, temperature=temperature)


async def test_request_too_large_shrinks_prompt_and_continues():
    sb = Sandbox(SandboxConfig(max_execution_time_seconds=3))
    await sb.start()
    try:
        llm = TooLargeOnceLLM(["```python\nfinal_answer('ok')\n```"], limit=6000)
        agent = CodeAgent(llm, sb, "SYSTEM", settings(context_cap_tokens=9500, max_tokens_per_step=900))
        sol = await agent.run("1", "TASK")
    finally:
        await sb.close()
    assert sol.success and sol.solution == "ok" and sol.iterations == 1
    assert llm.calls == 2 and sol.total_requests == 2   # the rejected request is counted


async def test_request_too_large_below_minimum_stops_cleanly():
    sb = Sandbox(SandboxConfig(max_execution_time_seconds=3))
    await sb.start()
    try:
        llm = TooLargeOnceLLM(["```python\nfinal_answer('ok')\n```"], limit=1000)
        agent = CodeAgent(llm, sb, "SYSTEM", settings())
        sol = await agent.run("1", "TASK")
    finally:
        await sb.close()
    assert not sol.success and "too large" in (sol.error or "")


async def test_client_maps_413_to_request_too_large():
    import httpx
    from smith.config import ProviderConfig
    from smith.llm.openai_compat import OpenAICompatibleClient

    def handler(request):
        return httpx.Response(413, json={"error": {"message": "Request too large for model `m` on tokens per "
                                                          "minute (TPM): Limit 6000, Requested 9431"}})
    client = OpenAICompatibleClient(ProviderConfig(name="g", base_url="https://x/v1", api_key_env="K"), "m", ["k1", "k2"])
    client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        await client.complete([{"role": "user", "content": "hi"}], max_tokens=10)
        raise AssertionError("expected RequestTooLargeError")
    except RequestTooLargeError as e:
        assert e.limit == 6000
    finally:
        await client.aclose()
