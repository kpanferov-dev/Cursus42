"""Environment and model-configuration loading.

API keys are NEVER stored in code. They come from environment variables,
optionally populated from a ``.env`` file. Several keys per provider are
supported, in any of these forms::

    OPENROUTER_API_KEY=key1
    OPENROUTER_API_KEY_2=key2          # numbered suffixes _2, _3, ...
    OPENROUTER_API_KEYS=key3,key4      # comma separated list

The provider is resolved from ``config/models.json`` by matching the
``--provider-url`` (or by provider name).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODELS_FILE = PROJECT_ROOT / "config" / "models.json"


class ProviderConfig(BaseModel):
    """One LLM provider (OpenAI-compatible HTTP API)."""
    name: str
    base_url: str
    api_key_env: str = Field(..., description="Base env var name, e.g. OPENROUTER_API_KEY")
    kind: str = Field(default="openai", description="Client implementation to use")
    extra_headers: Dict[str, str] = Field(default_factory=dict)
    supports_stop: bool = True
    max_stop_sequences: int = 4
    request_timeout_s: float = 120.0
    max_request_tokens: Optional[int] = Field(
        default=None, description="Provider cap on prompt + max_tokens of one request (e.g. Groq free-tier TPM)")
    models: List[str] = Field(default_factory=list, description="Known-good models (informative)")


class ModelsFile(BaseModel):
    providers: List[ProviderConfig]
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    fallbacks: List[str] = Field(default_factory=list,
                                 description="'provider:model' entries tried in order when the primary is unavailable")


def load_env(env_file: Optional[str] = None) -> None:
    """Load a .env file (explicit path first, then ./.env and project .env).

    Existing environment variables are never overwritten, so values exported
    by the exam script win over files.
    """
    if env_file:
        if not Path(env_file).is_file():
            raise FileNotFoundError(f"--env-file not found: {env_file}")
        load_dotenv(env_file, override=False)
    for candidate in (Path.cwd() / ".env", PROJECT_ROOT / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)


def collect_api_keys(base_env: str) -> List[str]:
    """Return every API key available for ``base_env`` (deduplicated, ordered)."""
    keys: List[str] = []
    if os.environ.get(base_env):
        keys.append(os.environ[base_env].strip())
    numbered = []
    pat = re.compile(rf"^{re.escape(base_env)}_(\d+)$")
    for name, value in os.environ.items():
        m = pat.match(name)
        if m and value.strip():
            numbered.append((int(m.group(1)), value.strip()))
    keys.extend(v for _, v in sorted(numbered))
    plural = os.environ.get(base_env + "S", "")
    keys.extend(k.strip() for k in plural.split(",") if k.strip())
    seen, unique = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def load_models_file(path: Optional[str] = None) -> ModelsFile:
    p = Path(path) if path else DEFAULT_MODELS_FILE
    with open(p, encoding="utf-8") as f:
        return ModelsFile.model_validate(json.load(f))


def _norm_url(url: str) -> str:
    return url.rstrip("/").lower()


def resolve_provider(
    provider_url: Optional[str],
    provider_name: Optional[str] = None,
    models_file: Optional[str] = None,
    api_key_env: Optional[str] = None,
) -> ProviderConfig:
    """Find the provider matching a URL / name; build an ad-hoc one otherwise.

    For an unknown URL, the key env var is guessed from the host name
    (``api.groq.com`` -> ``GROQ_API_KEY``) unless ``api_key_env`` is given.
    """
    cfg = load_models_file(models_file)
    if provider_name:
        for p in cfg.providers:
            if p.name == provider_name:
                return _override(p, provider_url, api_key_env)
        raise ValueError(f"Unknown provider name '{provider_name}' in models config")
    if provider_url:
        for p in cfg.providers:
            if _norm_url(p.base_url) == _norm_url(provider_url):
                return _override(p, None, api_key_env)
        host = urlparse(provider_url).hostname or "custom"
        parts = [x for x in host.split(".") if x not in ("api", "www", "com", "ai", "io", "dev", "net", "org")]
        guess = (parts[0] if parts else "LLM").upper().replace("-", "_") + "_API_KEY"
        return ProviderConfig(name=host, base_url=provider_url, api_key_env=api_key_env or guess)
    if cfg.default_provider:
        return resolve_provider(None, cfg.default_provider, models_file, api_key_env)
    raise ValueError("No provider given (use --provider-url or --provider)")


def _override(p: ProviderConfig, url: Optional[str], key_env: Optional[str]) -> ProviderConfig:
    data = p.model_dump()
    if url:
        data["base_url"] = url
    if key_env:
        data["api_key_env"] = key_env
    return ProviderConfig.model_validate(data)
