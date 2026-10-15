"""LLM provider layer."""
from __future__ import annotations

import logging
from typing import List, Optional

from smith.config import collect_api_keys, load_models_file, resolve_provider
from smith.llm.base import (
    FatalLLMError,
    LLMClient,
    LLMError,
    LLMResponse,
    RequestTooLargeError,
    RetryableLLMError,
)
from smith.llm.fallback import FallbackClient
from smith.llm.openai_compat import OpenAICompatibleClient, estimate_tokens

log = logging.getLogger("smith.llm")

__all__ = [
    "LLMClient", "LLMResponse", "LLMError", "FatalLLMError", "RetryableLLMError", "RequestTooLargeError",
    "OpenAICompatibleClient", "FallbackClient", "create_client", "estimate_tokens",
]

_CLIENTS = {"openai": OpenAICompatibleClient}


def _build(provider, model_name: str) -> Optional[LLMClient]:
    keys = collect_api_keys(provider.api_key_env)
    if not keys:
        return None
    cls = _CLIENTS.get(provider.kind)
    if cls is None:
        raise FatalLLMError(f"Unsupported provider kind '{provider.kind}'")
    return cls(provider, model_name, keys)


def create_client(
    model_name: str,
    provider_url: Optional[str] = None,
    provider_name: Optional[str] = None,
    models_file: Optional[str] = None,
    api_key_env: Optional[str] = None,
    use_fallbacks: bool = True,
) -> LLMClient:
    """Build a client from CLI arguments + config/models.json + environment.

    Switching provider only requires a new entry in models.json (or a new
    class registered in ``_CLIENTS`` for a non OpenAI-compatible API).
    The ``fallbacks`` of models.json whose keys are available are chained after the
    primary client (see ``FallbackClient``); fallbacks without keys are skipped.
    """
    provider = resolve_provider(provider_url, provider_name, models_file, api_key_env)
    primary = _build(provider, model_name)
    if primary is None:
        raise FatalLLMError(
            f"No API key found for provider '{provider.name}'. "
            f"Set {provider.api_key_env} (or {provider.api_key_env}_2, {provider.api_key_env}S=k1,k2) "
            "in the environment or in a .env file."
        )
    if not use_fallbacks:
        return primary
    chain: List[LLMClient] = [primary]
    for spec in load_models_file(models_file).fallbacks:
        name, _, model = spec.partition(":")
        if not model or (name == provider.name and model == model_name):
            continue
        try:
            client = _build(resolve_provider(None, name, models_file), model)
        except ValueError as e:
            log.warning("ignoring fallback %r: %s", spec, e)
            continue
        if client is None:
            log.debug("fallback %r skipped: no API key", spec)
            continue
        chain.append(client)
    return primary if len(chain) == 1 else FallbackClient(chain)
