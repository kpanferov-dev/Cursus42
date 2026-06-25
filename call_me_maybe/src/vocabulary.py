"""Load the LLM vocabulary and provide token <-> string lookup.

The SDK gives us a path to a JSON file mapping every token id to the
*surface form* of that token. Byte-level BPE tokenizers (used by Qwen,
GPT-2, Llama-3, etc.) encode whitespace and non-ASCII bytes through a
fixed byte<->unicode mapping, so we must reverse it to get the real
string that a token represents in the output.

Why this matters: tokens like ``"Ġhello"`` actually insert ``" hello"``
into the generated text. If the constraint state machine compared raw
surface forms to the JSON it wants to emit, it would reject perfectly
valid tokens. We decode the surface once, here, and everything
downstream works with real strings.

Public surface:

* :func:`load_vocabulary` -- read the JSON, return a :class:`Vocabulary`.
* :class:`Vocabulary`     -- ``text_of(token_id)``, ``id_of(text)``.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# Special tokens we must NEVER allow during constrained generation.
# Any token whose stored surface starts with one of these is dropped:
# they would end the sequence or corrupt the JSON.
_BANNED_PREFIXES = (
    "<|", "<s>", "</s>", "<pad>", "<unk>", "<bos>", "<eos>",
    "<|endoftext|>", "<|im_start|>", "<|im_end|>",
)


@lru_cache(maxsize=1)
def _byte_decoder() -> dict[str, int]:
    """Build the inverse of the GPT-2 / Qwen byte<->unicode table.

    Byte-level BPE tokenizers store every input byte (0-255) as a
    printable unicode character so the vocabulary file can be human
    readable. To recover the real byte sequence of a token we invert
    that mapping.

    Returns:
        Mapping from the stored unicode character to the real byte.
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
    return {chr(c): b for b, c in zip(bs, cs)}


def decode_token_surface(surface: str) -> str:
    """Turn a stored token surface form into the real string it inserts.

    Examples:
        ``"Ġhello"`` -> ``" hello"``
        ``"Ċ"``      -> ``"\\n"``

    Falls back to the raw surface if decoding fails (e.g. for special
    tokens like ``<|im_end|>``).
    """
    decoder = _byte_decoder()
    try:
        return bytes(decoder[ch] for ch in surface).decode(
            "utf-8", errors="strict"
        )
    except (KeyError, UnicodeDecodeError):
        return surface


class Vocabulary:
    """Bidirectional view over the model's vocabulary.

    Attributes:
        id_to_text: ``token_id -> decoded surface string``.
        text_to_id: ``decoded surface string -> token_id`` (first id wins).
        banned_ids: Token ids we never allow during constrained
            generation (special tokens, EOS, etc.).
        raw_surface: ``token_id -> stored surface`` (kept for debugging
            and for the public tokenizer's ``encode`` implementation).
    """

    def __init__(
        self,
        id_to_text: dict[int, str],
        banned_ids: set[int],
        raw_surface: dict[int, str],
    ) -> None:
        self.id_to_text: dict[int, str] = id_to_text
        self.text_to_id: dict[str, int] = {}
        for tid, txt in id_to_text.items():
            if txt and txt not in self.text_to_id:
                self.text_to_id[txt] = tid
        self.banned_ids: set[int] = banned_ids
        self.raw_surface: dict[int, str] = raw_surface

    def text_of(self, token_id: int) -> str:
        """Return the surface string of a token id, or ``""`` if unknown."""
        return self.id_to_text.get(token_id, "")

    def id_of(self, text: str) -> int | None:
        """Return the token id whose surface exactly equals ``text``."""
        return self.text_to_id.get(text)

    @property
    def size(self) -> int:
        """Number of token ids in the vocabulary."""
        return len(self.id_to_text)


def load_vocabulary(vocab_json_path: str | Path) -> Vocabulary:
    """Load the vocabulary JSON exposed by ``Small_LLM_Model``.

    The SDK's vocabulary file is a standard HuggingFace tokenizer
    vocabulary: a JSON object of the form ``{"<surface>": <token_id>}``.
    We invert it and decode every surface form to its real string.

    Args:
        vocab_json_path: Path returned by
            ``Small_LLM_Model.get_path_to_vocabulary_json()``.

    Returns:
        A fully-populated :class:`Vocabulary`.
    """
    path = Path(vocab_json_path)
    with path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)

    id_to_text: dict[int, str] = {}
    raw_surface: dict[int, str] = {}
    banned: set[int] = set()
    for surface, tid in raw.items():
        if not isinstance(tid, int):
            continue
        raw_surface[tid] = surface
        if any(surface.startswith(p) for p in _BANNED_PREFIXES):
            banned.add(tid)
            id_to_text[tid] = ""  # masked out; never matchable
            continue
        id_to_text[tid] = decode_token_surface(surface)

    return Vocabulary(
        id_to_text=id_to_text,
        banned_ids=banned,
        raw_surface=raw_surface,
    )
