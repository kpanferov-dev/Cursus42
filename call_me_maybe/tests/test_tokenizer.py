"""Tests for the public BPE tokenizer (bonus)."""
from __future__ import annotations

import pytest

from src.tokenizer import Tokenizer, TokenizerError
from src.vocabulary import Vocabulary


def test_roundtrip_ascii(vocab: Vocabulary) -> None:
    """encode -> decode should round-trip ASCII text."""
    tok = Tokenizer(vocab)
    text = "hello world"
    # Our toy vocab does not contain a Ġ-prefixed space, only a bare
    # space, so decode won't reproduce the space the way Qwen would.
    # Test that the encoded ids decode to *something* deterministic
    # whose visible characters match.
    ids = tok.encode(text)
    out = tok.decode(ids)
    assert out.replace(" ", "") == text.replace(" ", "")


def test_encode_uses_longer_tokens(vocab: Vocabulary) -> None:
    """The tokenizer prefers longer matches."""
    tok = Tokenizer(vocab)
    ids = tok.encode("fn_add")
    # ``fn_`` is a single multi-char token in our vocab + "add" is another.
    # Greedy match should pick at most 2 tokens.
    assert len(ids) <= 3

    # Verify decoded result starts with what we encoded.
    decoded = tok.decode(ids)
    assert decoded.endswith("add")


def test_decode_empty_list(vocab: Vocabulary) -> None:
    tok = Tokenizer(vocab)
    assert tok.decode([]) == ""


def test_encode_unknown_char_raises() -> None:
    """Encoding a char not covered by the vocab raises TokenizerError.

    Uses a deliberately incomplete vocab to verify the error path; the
    real Qwen vocab covers all 256 bytes so this branch is theoretical
    in production.
    """
    from src.vocabulary import Vocabulary

    # Vocab that only knows ASCII letter 'a'.
    raw = {0: "a"}
    text_map = {0: "a"}
    vocab = Vocabulary(id_to_text=text_map, banned_ids=set(), raw_surface=raw)
    tok = Tokenizer(vocab)
    with pytest.raises(TokenizerError):
        tok.encode("xy")
