"""Provider fallback chain and per-provider request caps (no network)."""
import json

import pytest

from smith.agent.loop import CodeAgent
from smith.llm import FallbackClient, create_client
from smith.llm.base import FatalLLMError, LLMClient, LLMResponse, RequestTooLargeError, RetryableLLMError
from smith.models import SandboxConfig
from smith.sandbox import Sandbox
from tests.test_agent import ScriptedLLM, settings


class FailingLLM(LLMClient):
    def __init__(self, exc):
        super().__init__()
        self.exc = exc
        self.calls = 0

    model_name = "failing"
    api_url = "local://failing"

    async def complete(self, messages, *, max_tokens, stop=None, temperature=0.0):
        self.calls += 1
        raise self.exc


async def test_fallback_switches_on_quota_error_and_records_real_model():
    primary = FailingLLM(RetryableLLMError("Rate limited and not enough time left (TPD)"))
    backup = ScriptedLLM(["```python\nfinal_answer('ok')\n```"])
    llm = FallbackClient([primary, backup])
    sb = Sandbox(SandboxConfig(max_execution_time_seconds=3))
    await sb.start()
    try:
        sol = await CodeAgent(llm, sb, "SYSTEM", settings()).run("1", "TASK")
    finally:
        await sb.close()
    assert sol.success and primary.calls == 1
    assert sol.steps[0].model_name == "scripted"          # the model that really answered
    assert sol.total_requests == 2                         # failed attempt is counted


async def test_fallback_also_on_fatal_error_but_not_on_request_too_large():
    llm = FallbackClient([FailingLLM(FatalLLMError("404 model not found")), ScriptedLLM(["x"])])
    resp = await llm.complete([{"role": "user", "content": "hi"}], max_tokens=10)
    assert resp.model_name == "scripted"
    too_large = FallbackClient([FailingLLM(RequestTooLargeError("413", 6000)), ScriptedLLM(["x"])])
    with pytest.raises(RequestTooLargeError):
        await too_large.complete([{"role": "user", "content": "hi"}], max_tokens=10)
    assert too_large.index == 0                            # the loop shrinks the prompt instead


async def test_last_client_error_is_raised():
    llm = FallbackClient([FailingLLM(RetryableLLMError("a")), FailingLLM(RetryableLLMError("b"))])
    with pytest.raises(RetryableLLMError, match="b"):
        await llm.complete([{"role": "user", "content": "hi"}], max_tokens=10)


def _models_file(tmp_path):
    cfg = {"fallbacks": ["p1:m1", "p2:m2"], "providers": [
        {"name": "p1", "base_url": "https://p1/v1", "api_key_env": "P1_KEY", "max_request_tokens": 6000},
        {"name": "p2", "base_url": "https://p2/v1", "api_key_env": "P2_KEY"}]}
    path = tmp_path / "models.json"
    path.write_text(json.dumps(cfg))
    return str(path)


def test_create_client_chains_only_fallbacks_with_keys(tmp_path, monkeypatch):
    f = _models_file(tmp_path)
    monkeypatch.setenv("P1_KEY", "k1")
    monkeypatch.delenv("P2_KEY", raising=False)
    c = create_client("m1", provider_name="p1", models_file=f)
    assert not isinstance(c, FallbackClient)               # p1:m1 is the primary itself, p2 has no key
    assert c.max_request_tokens == 6000
    monkeypatch.setenv("P2_KEY", "k2")
    c = create_client("m1", provider_name="p1", models_file=f)
    assert isinstance(c, FallbackClient) and [x.model_name for x in c.clients] == ["m1", "m2"]
    assert not isinstance(create_client("m1", provider_name="p1", models_file=f, use_fallbacks=False),
                          FallbackClient)


class CapRecordingLLM(ScriptedLLM):
    max_request_tokens = 3000

    def __init__(self, replies):
        super().__init__(replies)
        self.calls = 0

    async def complete(self, messages, *, max_tokens, stop=None, temperature=0.0):
        self.calls += 1
        return await super().complete(messages, max_tokens=max_tokens, stop=stop, temperature=temperature)


async def _run_capped(task_chars):
    llm = CapRecordingLLM(["```python\nfinal_answer('ok')\n```"])
    sb = Sandbox(SandboxConfig(max_execution_time_seconds=3))
    await sb.start()
    try:
        sol = await CodeAgent(llm, sb, "SYSTEM", settings(context_cap_tokens=9500, max_tokens_per_step=900)
                              ).run("1", "T" * task_chars)
    finally:
        await sb.close()
    return llm, sol


async def test_loop_respects_provider_request_cap():
    # ~1k-token task fits in 3000 - 900 = 2100 tokens: solved normally
    llm, sol = await _run_capped(3000)
    assert sol.success and llm.calls == 1
    # ~4k-token task cannot fit the provider cap even though context_cap is 9500:
    # the loop must stop BEFORE sending a request the provider would reject
    llm, sol = await _run_capped(13000)
    assert not sol.success and llm.calls == 0 and "input token budget" in (sol.error or "")
