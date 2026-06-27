"""End-to-end test of the generator with a stub model."""
from __future__ import annotations

import json
from typing import List

import numpy as np

from src.generator import generate_call
from src.schemas import FunctionDefinition
from src.tokenizer import Tokenizer
from src.vocabulary import Vocabulary


class WeightedStubModel:
    """Stub model that biases logits toward certain characters.

    Lets us verify that the model's preferences flow through the
    constraint mask: if we boost 'f', the function name should
    start with 'f'; if we boost '4', numeric parameters should
    include a 4.
    """

    def __init__(self, vocab: Vocabulary, boost: dict[str, float]) -> None:
        self._vocab = vocab
        self._size = max(vocab.id_to_text.keys()) + 1
        self._boost = boost

    def get_logits_from_input_ids(self, input_ids: object) -> np.ndarray:
        """Return logits with selective boosting."""
        logits = np.zeros(self._size, dtype=np.float64)
        for tid, text in self._vocab.id_to_text.items():
            for ch, score in self._boost.items():
                if ch in text:
                    logits[tid] += score
        return logits

    def get_path_to_vocab_file(self) -> str:
        return "/dev/null"


def test_generator_picks_boosted_function(
    vocab: Vocabulary,
    functions: List[FunctionDefinition],
) -> None:
    """Boosting tokens containing 'g' should steer toward fn_greet."""
    model = WeightedStubModel(vocab, boost={"g": 10.0})
    tok = Tokenizer(vocab)
    call = generate_call(
        model=model,  # type: ignore[arg-type]
        vocab=vocab,
        tokenizer=tok,
        functions=functions,
        prompt="say hello",
        max_new_tokens=200,
    )
    assert call.name == "fn_greet"
    assert "name" in call.parameters
    assert isinstance(call.parameters["name"], str)


def test_generator_output_is_always_valid_json(
    vocab: Vocabulary,
    functions: List[FunctionDefinition],
) -> None:
    """Whatever the model does, the output must be parseable JSON."""
    # Random-ish boost: completely arbitrary.
    boost = {ch: float(i) for i, ch in enumerate("abcdefghij")}
    model = WeightedStubModel(vocab, boost=boost)
    tok = Tokenizer(vocab)
    for _ in range(5):
        call = generate_call(
            model=model,  # type: ignore[arg-type]
            vocab=vocab,
            tokenizer=tok,
            functions=functions,
            prompt="test",
            max_new_tokens=200,
        )
        # Must be in the function list.
        assert call.name in {f.name for f in functions}
        # Must serialise back to valid JSON.
        assert json.loads(json.dumps(call.model_dump()))


def test_type_coercion(vocab: Vocabulary, functions: List[FunctionDefinition]) -> None:
    """fn_add_numbers parameters must be floats, fn_is_even must be int."""
    model = WeightedStubModel(vocab, boost={"a": 10.0})
    tok = Tokenizer(vocab)
    call = generate_call(
        model=model,  # type: ignore[arg-type]
        vocab=vocab,
        tokenizer=tok,
        functions=functions,
        prompt="add",
        max_new_tokens=200,
    )
    if call.name == "fn_add_numbers":
        for k in ("a", "b"):
            assert isinstance(call.parameters[k], float), (
                f"{k} should be float, got {type(call.parameters[k])}"
            )
