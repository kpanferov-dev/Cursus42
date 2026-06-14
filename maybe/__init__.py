"""A MOCK stand-in for the provided ``llm_sdk`` package.

IMPORTANT: This is **not** the real SDK. It exists only so the project
can run and be tested without downloading the Qwen model. It implements
the exact public interface described in the subject
(``get_logits_from_input_ids``, ``get_path_to_vocab_file``, ``encode``,
``decode``) but returns deterministic pseudo-random logits instead of
real model predictions.

Because constrained decoding guarantees valid, schema-compliant output
*regardless* of the logits, this mock is enough to verify structural
correctness. For real accuracy, replace this package with the official
``llm_sdk`` (copy it next to ``src``) and run ``uv sync``.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Dict, List

import numpy as np


def _bytes_to_unicode() -> Dict[int, str]:
    """Return the GPT-2/Qwen byte-to-unicode mapping (see src.vocab)."""
    printable = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("\u00a1"), ord("\u00ac") + 1))
        + list(range(ord("\u00ae"), ord("\u00ff") + 1))
    )
    mapping = list(printable)
    extra = 0
    for byte in range(256):
        if byte not in printable:
            printable.append(byte)
            mapping.append(256 + extra)
            extra += 1
    return {byte: chr(code) for byte, code in zip(printable, mapping)}


_EXTRA_WORDS: List[str] = [
    "fn_add_numbers", "fn_greet", "fn_reverse_string", "fn_multiply",
    "hello", "world", "shrek", "john", "true", "false", "name",
    "parameters", "number", "string",
]


class Small_LLM_Model:  # noqa: N801 - name mirrors the real SDK class
    """Deterministic mock implementing the LLM SDK interface."""

    def __init__(self, model_name: str = "Qwen/Qwen3-0.6B") -> None:
        """Build the mock vocabulary and persist it to a temp file.

        Args:
            model_name: Accepted for interface compatibility; unused.
        """
        self.model_name = model_name
        self._byte_to_char = _bytes_to_unicode()
        self._char_to_byte = {c: b for b, c in self._byte_to_char.items()}
        self._token_to_id: Dict[str, int] = {}
        self._id_to_token: List[str] = []
        self._byte_token_id: Dict[int, int] = {}
        self._build_vocab()
        self._vocab_path = self._write_vocab()

    def _build_vocab(self) -> None:
        """Register single-byte tokens, words and special tokens."""
        for byte in range(256):
            self._register(self._byte_to_char[byte])
            self._byte_token_id[byte] = self._token_to_id[
                self._byte_to_char[byte]]
        for word in _EXTRA_WORDS:
            encoded = "".join(
                self._byte_to_char[b] for b in word.encode("utf-8"))
            self._register(encoded)
        for special in ("<|im_start|>", "<|im_end|>", "<|endoftext|>"):
            self._register(special)

    def _register(self, token: str) -> None:
        """Add a token to the vocabulary if it is new."""
        if token not in self._token_to_id:
            self._token_to_id[token] = len(self._id_to_token)
            self._id_to_token.append(token)

    def _write_vocab(self) -> str:
        """Write the vocabulary to a temporary JSON file."""
        directory = tempfile.mkdtemp(prefix="mock_llm_sdk_")
        path = os.path.join(directory, "vocab.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self._token_to_id, handle, ensure_ascii=False)
        return path

    def get_path_to_vocab_file(self) -> str:
        """Return the path to the mock vocabulary file."""
        return self._vocab_path

    def encode(self, text: str) -> List[int]:
        """Encode text as one token per UTF-8 byte."""
        return [self._byte_token_id[byte] for byte in text.encode("utf-8")]

    def decode(self, token_ids: List[int]) -> str:
        """Decode token ids back into text (best effort)."""
        data = bytearray()
        for token_id in token_ids:
            token = self._id_to_token[token_id]
            try:
                data.extend(self._char_to_byte[char] for char in token)
            except KeyError:
                continue
        return data.decode("utf-8", errors="replace")

    def get_logits_from_input_ids(self, input_ids: List[int]) -> List[float]:
        """Return deterministic pseudo-random logits for the next token.

        The values depend only on the input, so runs are reproducible.
        They are intentionally unrelated to any "correct" answer to show
        that constrained decoding alone enforces a valid result.
        """
        seed = (sum(input_ids) * 1103515245 + len(input_ids) * 12345) % (
            2 ** 32)
        generator = np.random.default_rng(seed)
        logits = generator.standard_normal(len(self._id_to_token))
        return [float(value) for value in logits]
