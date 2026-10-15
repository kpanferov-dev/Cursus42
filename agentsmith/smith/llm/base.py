"""Provider-agnostic LLM interface.

Every concrete client turns a list of chat messages into an ``LLMResponse``
that carries the text plus everything needed for usage tracking
(tokens, latency, retries, endpoint, model).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

Message = Dict[str, str]  # {"role": "system"|"user"|"assistant", "content": str}


class LLMError(Exception):
    """Base class for provider errors."""


class RetryableLLMError(LLMError):
    """Transient failure (rate limit, 5xx, timeout): retry / rotate key."""

    def __init__(self, message: str, retry_after: Optional[float] = None, rotate_key: bool = False):
        super().__init__(message)
        self.retry_after = retry_after
        self.rotate_key = rotate_key


class FatalLLMError(LLMError):
    """Non-recoverable failure (bad request, unknown model, all keys invalid)."""


class RequestTooLargeError(LLMError):
    """The request exceeds a per-request size limit of the provider (HTTP 413, e.g. Groq's
    free-tier tokens-per-minute cap). Not fatal: the caller should resend a smaller prompt.
    ``limit`` is the provider's token limit when the error message states it."""

    def __init__(self, message: str, limit: Optional[int] = None):
        super().__init__(message)
        self.limit = limit


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    retries: int
    requests: int
    api_url: str
    model_name: str
    finish_reason: str = ""
    usage_estimated: bool = False


@dataclass
class UsageTracker:
    """Aggregated usage over the life of one client (one task run)."""
    requests: int = 0
    failed_requests: int = 0
    retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_latency_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    def record(self, resp: LLMResponse) -> None:
        self.requests += resp.requests
        self.retries += resp.retries
        self.failed_requests += resp.requests - 1
        self.input_tokens += resp.input_tokens
        self.output_tokens += resp.output_tokens
        self.total_latency_ms += resp.request_time_ms


class LLMClient(ABC):
    """Abstract chat-completion client."""

    def __init__(self) -> None:
        self.usage = UsageTracker()

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def api_url(self) -> str: ...

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        *,
        max_tokens: int,
        stop: Optional[List[str]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Return one completion. Must raise ``LLMError`` subclasses on failure."""

    @property
    def max_request_tokens(self) -> Optional[int]:
        """Provider limit on prompt + max_tokens of a single request (None = unknown)."""
        return None

    async def aclose(self) -> None:  # pragma: no cover - optional
        return None
