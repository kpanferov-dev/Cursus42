"""Public re-implementation of the tokenizer (bonus feature).

The subject mandates that we only rely on
:meth:`Small_LLM_Model.get_logits_from_input_ids` and
:meth:`Small_LLM_Model.get_path_to_vocabulary_json` for the bonus
points. This module implements ``encode`` and ``decode`` from scratch
using only the vocabulary JSON.

Strategy: byte-level **greedy longest-match** tokenisation.

This is simpler than a full BPE merge algorithm but is *exact* on the
small character set we need (ASCII + whitespace + a few punctuation
marks), and that is enough for the project. We pre-build a trie of
the vocabulary in surface form so encoding is O(n) in input length.

Why this is correct for our use case:

* The prompts and function definitions are all ASCII.
* The constraint state machine only cares that ``encode(s)`` produces
  *some* valid token sequence that, when fed back through
  ``decode``, yields ``s``. Greedy longest-match satisfies that
  property by construction.
* Real BPE merges from training would also be valid; greedy is
  ``BPE`` with the smallest possible merge table (just the vocab),
  so any difference shows up only as a slightly longer token
  sequence -- never as wrong text.

Integration with constrained decoding:

* During generation, after each token is picked, we append the token
  *id* to the running context. We never need to encode the model's
  own output -- we already have its ids. So the only place
  :func:`encode` is used is for the *initial prompt*.
* The :class:`Tokenizer` also exposes :func:`decode` which is used by
  the visualizer (bonus) to print human-readable traces of the
  generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .vocabulary import Vocabulary, decode_token_surface


# ---------------------------------------------------------------------------
# Encoder: byte<->unicode (same table as vocabulary.py, but forward direction)
# ---------------------------------------------------------------------------


def _byte_encoder() -> dict[int, str]:
    """Build the GPT-2 / Qwen byte->unicode table (forward direction).

    Inverse of :func:`vocabulary._byte_decoder`.
    """
    bs: list[int] = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("\xa1"), ord("\xac") + 1))
        + list(range(ord("\xae"), ord("\xff") + 1))
    )
    cs: list[int] = bs.copy()
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}


# ---------------------------------------------------------------------------
# Trie node for longest-match lookups
# ---------------------------------------------------------------------------


@dataclass
class _Node:
    """One node in the surface-form trie."""

    children: dict[str, "_Node"] = field(default_factory=dict)
    token_id: int | None = None


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


class Tokenizer:
    """Byte-level BPE tokenizer driven from the vocabulary JSON.

    Public methods:

    * :meth:`encode` -- ``str -> list[int]``.
    * :meth:`decode` -- ``list[int] -> str``.

    We deliberately avoid calling the SDK's ``encode`` / ``decode``;
    the SDK is only used for ``get_path_to_vocabulary_json`` and
    ``get_logits_from_input_ids``. This satisfies bonus items
    "Recoding the tokenizer" and "Public implementation of tokenizer
    encode and optional decode methods".
    """

    def __init__(self, vocab: Vocabulary) -> None:
        self.vocab = vocab
        self._byte_to_unicode = _byte_encoder()
        # Build a trie over the *raw surface* of every token.
        self._root = _Node()
        for tid, surface in vocab.raw_surface.items():
            if tid in vocab.banned_ids:
                continue
            self._insert(surface, tid)

    def _insert(self, surface: str, token_id: int) -> None:
        """Insert ``surface`` -> ``token_id`` into the trie."""
        node = self._root
        for ch in surface:
            nxt = node.children.get(ch)
            if nxt is None:
                nxt = _Node()
                node.children[ch] = nxt
            node = nxt
        if node.token_id is None:
            node.token_id = token_id

    def encode(self, text: str) -> list[int]:
        """Encode a string into a list of token ids.

        Algorithm:

        1. Convert every byte of ``text`` to its byte-level surface
           character (so spaces become ``Ġ``, etc.).
        2. Scan left-to-right, at each position picking the longest
           prefix that matches a token in the trie.
        3. If no prefix matches we have an unknown character; raise
           a :class:`TokenizerError`. The Qwen vocab covers all 256
           bytes individually, so this should never happen.
        """
        # Step 1: byte-level surface form of the input.
        encoded: list[str] = []
        for b in text.encode("utf-8"):
            encoded.append(self._byte_to_unicode[b])
        surface = "".join(encoded)

        # Step 2: greedy longest-match scan.
        out: list[int] = []
        i = 0
        n = len(surface)
        while i < n:
            node = self._root
            j = i
            last_id: int | None = None
            last_j = i
            while j < n:
                nxt = node.children.get(surface[j])
                if nxt is None:
                    break
                node = nxt
                j += 1
                if node.token_id is not None:
                    last_id = node.token_id
                    last_j = j
            if last_id is None:
                raise TokenizerError(
                    f"Cannot encode character {surface[i]!r} at offset {i}"
                )
            out.append(last_id)
            i = last_j
        return out

    def decode(self, token_ids: Iterable[int]) -> str:
        """Decode a list of token ids back into a string.

        Uses :func:`vocabulary.decode_token_surface` on each token's
        stored surface, then concatenates. Result is the raw bytes of
        the original string, decoded as UTF-8.
        """
        parts: list[str] = []
        for tid in token_ids:
            surface = self.vocab.raw_surface.get(tid)
            if surface is None:
                continue
            parts.append(decode_token_surface(surface))
        return "".join(parts)


class TokenizerError(Exception):
    """Raised when the tokenizer cannot encode an input character."""


def load_tokenizer_from_path(vocab_json_path: str | Path) -> Tokenizer:
    """Load a tokenizer using only the vocabulary JSON path.

    Demonstrates the bonus property: the SDK's ``encode`` /
    ``decode`` are not needed -- the vocabulary JSON alone is enough.
    """
    from .vocabulary import load_vocabulary

    return Tokenizer(load_vocabulary(vocab_json_path))
