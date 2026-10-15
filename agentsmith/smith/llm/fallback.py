"""Provider fallback: try the primary client, switch to the next one when it is unavailable.

Free tiers run out (e.g. Groq: 200k tokens per day per organization) and models are
withdrawn without notice. ``FallbackClient`` wraps an ordered list of clients
(primary first, then the ``fallbacks`` of ``config/models.json``) and, when the current
client raises an ``LLMError``, switches to the next one and resends the same request.

``RequestTooLargeError`` is NOT a reason to switch: the request itself must shrink, which
is the agent loop's job. Each step's ``api_url`` / ``model_name`` are those of the client
that really answered, so a switch is visible in solution.json.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from smith.llm.base import LLMClient, LLMError, LLMResponse, Message, RequestTooLargeError

log = logging.getLogger("smith.llm")


class FallbackClient(LLMClient):
    def __init__(self, clients: List[LLMClient]):
        super().__init__()
        if not clients:
            raise ValueError("FallbackClient needs at least one client")
        self.clients = clients
        self.index = 0
        self._deadline: Optional[float] = None

    @property
    def current(self) -> LLMClient:
        return self.clients[self.index]

    @property
    def model_name(self) -> str:
        return self.current.model_name

    @property
    def api_url(self) -> str:
        return self.current.api_url

    @property
    def max_request_tokens(self) -> Optional[int]:
        return getattr(self.current, "max_request_tokens", None)

    @property
    def deadline(self) -> Optional[float]:
        return self._deadline

    @deadline.setter
    def deadline(self, value: Optional[float]) -> None:
        self._deadline = value
        for c in self.clients:
            if hasattr(c, "deadline"):
                c.deadline = value

    async def complete(self, messages: List[Message], *, max_tokens: int,
                       stop: Optional[List[str]] = None, temperature: float = 0.0) -> LLMResponse:
        failed_requests = 0
        while True:
            try:
                resp = await self.current.complete(messages, max_tokens=max_tokens, stop=stop,
                                                   temperature=temperature)
            except RequestTooLargeError:
                raise
            except LLMError as e:
                failed_requests += 1
                if self.index + 1 >= len(self.clients):
                    raise
                nxt = self.clients[self.index + 1]
                log.warning("provider %s (%s) unavailable: %s -> falling back to %s (%s)",
                            self.current.api_url, self.current.model_name, str(e)[:160],
                            nxt.api_url, nxt.model_name)
                self.index += 1
                continue
            resp.requests += failed_requests   # total_requests includes the failed attempts
            self.usage.record(resp)
            return resp

    async def aclose(self) -> None:
        for c in self.clients:
            await c.aclose()
