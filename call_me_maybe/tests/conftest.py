"""Shared fixtures: a tiny in-memory vocabulary and a stub model."""
from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from src.schemas import FunctionDefinition, ParamSpec
from src.tokenizer import _byte_encoder
from src.vocabulary import Vocabulary, decode_token_surface


def _to_surface(text: str) -> str:
    """Convert a real string to GPT-2 byte-level surface form."""
    enc = _byte_encoder()
    return "".join(enc[b] for b in text.encode("utf-8"))


def build_char_vocab() -> Vocabulary:
    """A toy vocabulary mimicking real byte-level BPE storage.

    Includes single-byte tokens for every byte 0-255 (real Qwen vocab
    does too), plus a handful of multi-byte tokens to exercise
    boundary-spanning matches.
    """
    real_multi = [
        '", "', '"name"', '"parameters"', 'fn_', '_numbers',
        'add', 'greet', 'reverse_string', 'is_even',
        '{"', '": "', '": ',
    ]
    id_to_text: dict[int, str] = {}
    raw_surface: dict[int, str] = {}
    next_id = 0
    seen: set[str] = set()
    # Single-byte tokens cover every possible byte.
    for b in range(256):
        surf = _to_surface(bytes([b]).decode("latin-1"))
        if surf in seen:
            continue
        seen.add(surf)
        raw_surface[next_id] = surf
        id_to_text[next_id] = decode_token_surface(surf)
        next_id += 1
    # Multi-byte tokens accelerate matches.
    for c in real_multi:
        surf = _to_surface(c)
        if surf in seen:
            continue
        seen.add(surf)
        raw_surface[next_id] = surf
        id_to_text[next_id] = decode_token_surface(surf)
        next_id += 1
    return Vocabulary(id_to_text=id_to_text, banned_ids=set(), raw_surface=raw_surface)


@pytest.fixture
def vocab() -> Vocabulary:
    """The toy character vocabulary."""
    return build_char_vocab()


@pytest.fixture
def functions() -> list[FunctionDefinition]:
    """A small set of functions used across tests."""
    return [
        FunctionDefinition(
            name="fn_add_numbers",
            description="add two numbers",
            parameters={
                "a": ParamSpec(type="number"),
                "b": ParamSpec(type="number"),
            },
            returns={"type": "number"},
        ),
        FunctionDefinition(
            name="fn_greet",
            description="greet a person",
            parameters={"name": ParamSpec(type="string")},
            returns={"type": "string"},
        ),
        FunctionDefinition(
            name="fn_is_even",
            description="check parity",
            parameters={"n": ParamSpec(type="integer")},
            returns={"type": "boolean"},
        ),
    ]


class StubModel:
    """A model that returns uniform logits.

    Useful for testing that the constraint mask alone determines what
    gets emitted -- the model itself adds no signal.
    """

    def __init__(self, vocab: Vocabulary, vocab_json_path: str = "/dev/null") -> None:
        self._vocab = vocab
        self._path = vocab_json_path

    def get_logits_from_input_ids(self, input_ids: Any) -> np.ndarray:
        """Return uniform zero logits at the size of the vocab."""
        size = max(self._vocab.id_to_text.keys()) + 1
        return np.zeros(size, dtype=np.float64)

    def get_path_to_vocab_file(self) -> str:
        """Return the path used to load the vocabulary."""
        return self._path


@pytest.fixture
def stub_model(vocab: Vocabulary) -> StubModel:
    """A stub model bound to the toy vocabulary."""
    return StubModel(vocab)
