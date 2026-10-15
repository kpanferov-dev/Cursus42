"""Client for any OpenAI-compatible ``/chat/completions`` endpoint.

Covers OpenRouter, Groq, Gemini (OpenAI endpoint), Mistral, Cerebras,
Together, Cohere (compat API), vLLM / Ollama, ...

Retry policy
------------
* 429 / 402 / quota messages -> cool the key down (Retry-After aware), rotate
* 401 / 403                  -> disable the key, rotate
* 5xx / timeouts / network   -> exponential backoff, same key
* 413 / "request too large"  -> RequestTooLargeError (the agent resends a smaller prompt)
* 400 / 404                  -> fatal (bad model name, bad params)
Retries stop when ``max_retries`` is reached or the task deadline is near.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from typing import List, Optional

import httpx

from smith.config import ProviderConfig
from smith.llm.base import (
    FatalLLMError,
    LLMClient,
    LLMResponse,
    Message,
    RequestTooLargeError,
    RetryableLLMError,
)
from smith.llm.keys import KeyRing

log = logging.getLogger("smith.llm")

_QUOTA_HINTS = ("rate limit", "quota", "exhausted", "too many requests", "limit exceeded")


def estimate_tokens(text: str) -> int:
    """Conservative token estimate (~3.2 chars/token) when usage is missing."""
    return int(len(text) / 3.2) + 1


class OpenAICompatibleClient(LLMClient):
    def __init__(
        self,
        provider: ProviderConfig,
        model: str,
        keys: List[str],
        max_retries: int = 6,
        base_backoff_s: float = 2.0,
    ):
        super().__init__()
        self.provider = provider
        self._model = model
        self.keys = KeyRing(keys)
        self.max_retries = max_retries
        self.base_backoff_s = base_backoff_s
        self.deadline: Optional[float] = None  # time.monotonic() value set by the agent
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(provider.request_timeout_s, connect=15.0))

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_request_tokens(self) -> Optional[int]:
        return self.provider.max_request_tokens

    @property
    def api_url(self) -> str:
        return self.provider.base_url

    async def aclose(self) -> None:
        await self._http.aclose()

    def _remaining(self) -> float:
        return float("inf") if self.deadline is None else self.deadline - time.monotonic()

    async def complete(
        self,
        messages: List[Message],
        *,
        max_tokens: int,
        stop: Optional[List[str]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max(16, int(max_tokens)),
            "temperature": temperature,
        }
        if stop and self.provider.supports_stop:
            payload["stop"] = stop[: self.provider.max_stop_sequences]

        url = self.provider.base_url.rstrip("/") + "/chat/completions"
        attempts = 0
        last_error = "unknown error"
        t_start = time.perf_counter()
        while attempts <= self.max_retries:
            attempts += 1
            if self.keys.all_disabled():
                raise FatalLLMError(f"All API keys for {self.provider.name} were rejected ({last_error})")
            wait = self.keys.wait_time()
            if wait > 0:
                if wait > self._remaining() - 5:
                    raise RetryableLLMError(f"Rate limited and not enough time left ({last_error})")
                await asyncio.sleep(wait)
            headers = {
                "Authorization": f"Bearer {self.keys.current()}",
                "Content-Type": "application/json",
                **self.provider.extra_headers,
            }
            t0 = time.perf_counter()
            try:
                timeout = min(self.provider.request_timeout_s, max(5.0, self._remaining() - 2))
                r = await self._http.post(url, json=payload, headers=headers, timeout=timeout)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as e:
                last_error = f"{type(e).__name__}: {e}"
                log.warning("LLM request failed (%s), attempt %d", last_error, attempts)
                await self._backoff(attempts)
                continue
            latency_ms = (time.perf_counter() - t0) * 1000

            if r.status_code == 200:
                try:
                    data = r.json()
                    return self._parse(data, messages, latency_ms, attempts, t_start)
                except FatalLLMError:
                    raise
                except Exception as e:  # malformed body -> retry
                    last_error = f"malformed response: {e}"
                    await self._backoff(attempts)
                    continue

            body = r.text[:400]
            last_error = f"HTTP {r.status_code}: {body}"
            log.warning("LLM %s with %s: %s", r.status_code, self.keys.label(), body)
            low = body.lower()
            if r.status_code == 413 or "request too large" in low:
                # Same request will fail on every key: let the agent shrink the prompt.
                m = re.search(r"limit\D{0,3}(\d+)", low)
                raise RequestTooLargeError(last_error, int(m.group(1)) if m else None)
            if r.status_code in (401, 403):
                self.keys.disable_current()
            elif r.status_code in (429, 402) or any(h in low for h in _QUOTA_HINTS):
                self.keys.cool_down_current(self._retry_after(r) or self.base_backoff_s * (2 ** min(attempts, 5)))
            elif r.status_code >= 500 or r.status_code == 408:
                await self._backoff(attempts)
            else:
                raise FatalLLMError(last_error)
        raise RetryableLLMError(f"Gave up after {attempts} attempts: {last_error}")

    async def _backoff(self, attempt: int) -> None:
        delay = min(30.0, self.base_backoff_s * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
        if delay > self._remaining() - 5:
            raise RetryableLLMError("Not enough time left to retry the LLM request")
        await asyncio.sleep(delay)

    @staticmethod
    def _retry_after(r: httpx.Response) -> Optional[float]:
        val = r.headers.get("retry-after")
        try:
            return float(val) if val else None
        except ValueError:
            return None

    def _parse(self, data: dict, messages: List[Message], latency_ms: float, attempts: int, t_start: float) -> LLMResponse:
        if "error" in data and not data.get("choices"):
            err = data["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            if any(h in msg.lower() for h in _QUOTA_HINTS):
                self.keys.cool_down_current(10)
                raise ValueError(msg)
            raise FatalLLMError(msg)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = msg.get("content") or ""
        if isinstance(text, list):  # some providers return content parts
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
        usage = data.get("usage") or {}
        in_tok = usage.get("prompt_tokens")
        out_tok = usage.get("completion_tokens")
        estimated = in_tok is None or out_tok is None
        if in_tok is None:
            in_tok = estimate_tokens("".join(m["content"] for m in messages))
        if out_tok is None:
            out_tok = estimate_tokens(text + (msg.get("reasoning") or ""))
        resp = LLMResponse(
            text=text,
            input_tokens=int(in_tok),
            output_tokens=int(out_tok),
            request_time_ms=latency_ms,
            retries=attempts - 1,
            requests=attempts,
            api_url=self.provider.base_url,
            model_name=self._model,
            finish_reason=choice.get("finish_reason") or "",
            usage_estimated=estimated,
        )
        self.usage.record(resp)
        return resp
