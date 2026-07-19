"""Bonus: query expansion.

Lexical retrieval misses when the question and the source use different words
for the same idea ("delete" vs "unload", "endpoint" vs "route"). This module
rewrites a query by appending domain synonyms and identifier variants, which
widens BM25/TF-IDF matching without changing the original intent. Expansion is
opt-in via the ``--expand`` CLI flag.
"""

from __future__ import annotations

import re
from typing import Dict, List

# Small, hand-curated domain synonym map for the vLLM codebase. Keys and values
# are lowercase single tokens; expansion only *adds* terms, never removes them.
_SYNONYMS: Dict[str, List[str]] = {
    "configure": ["config", "setup", "set", "option", "arg"],
    "config": ["configure", "setup", "option"],
    "endpoint": ["route", "api", "path", "url", "handler"],
    "server": ["serve", "app", "fastapi", "http"],
    "load": ["loading", "register", "add"],
    "unload": ["remove", "delete", "deregister"],
    "delete": ["remove", "unload"],
    "create": ["build", "make", "init", "construct"],
    "adapter": ["lora", "peft"],
    "method": ["function", "def", "api"],
    "function": ["method", "def"],
    "class": ["object", "type"],
    "parameter": ["argument", "arg", "param", "option"],
    "argument": ["parameter", "arg", "param"],
    "modality": ["multimodal", "mm", "image", "audio", "video"],
    "token": ["tokenizer", "tokenization", "ids"],
    "batch": ["batched", "batching"],
    "quantization": ["quantize", "quant", "int8", "fp8", "gptq", "awq"],
    "attention": ["attn", "kv", "cache"],
    "sampling": ["sampler", "temperature", "topk", "topp"],
}

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def _identifier_variants(token: str) -> List[str]:
    """Return split-token variants of a possible identifier."""
    variants: List[str] = []
    if "_" in token:
        variants.extend(p for p in token.lower().split("_") if p)
    parts = [p.lower() for p in _CAMEL_RE.findall(token)]
    if len(parts) > 1:
        variants.extend(parts)
    return variants


def expand_query(query: str, max_extra: int = 24) -> str:
    """Append domain synonyms and identifier variants to ``query``.

    Args:
        query: The original question.
        max_extra: Upper bound on the number of appended terms.

    Returns:
        The original query followed by deduplicated expansion terms.
    """
    if not query or not query.strip():
        return query
    seen = {t.lower() for t in _TOKEN_RE.findall(query)}
    extra: List[str] = []
    for token in _TOKEN_RE.findall(query):
        lowered = token.lower()
        for syn in _SYNONYMS.get(lowered, []):
            if syn not in seen:
                seen.add(syn)
                extra.append(syn)
        for variant in _identifier_variants(token):
            if variant not in seen:
                seen.add(variant)
                extra.append(variant)
        if len(extra) >= max_extra:
            break
    if not extra:
        return query
    return query + " " + " ".join(extra[:max_extra])
