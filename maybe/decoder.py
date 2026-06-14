"""The constrained decoder.

Given a model (through the SDK interface), a :class:`~src.vocab.Vocabulary`
and a :class:`~src.grammar.SchemaGuide`, this module generates tokens one
at a time. At every step it asks the guide which tokens keep the output
valid, sets every other token to negative infinity, and selects the
highest-scoring survivor. The model therefore decides *what* to say while
the guide guarantees the result is always structurally and schematically
valid.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np

from src.config import MAX_CALL_TOKENS, MAX_VALUE_TOKENS
from src.grammar import GuideState, Literal, SchemaGuide
from src.vocab import Vocabulary


class SupportsLLM(Protocol):
    """The subset of the LLM SDK that the decoder relies on."""

    def get_logits_from_input_ids(self, input_ids: List[int]) -> List[float]:
        """Return next-token logits for a sequence of token ids."""

    def get_path_to_vocab_file(self) -> str:
        """Return the path to the vocabulary file."""

    def encode(self, text: str) -> object:
        """Encode text into token ids (list or tensor)."""


class DecodeError(Exception):
    """Raised when no valid token can continue the constrained output."""


def to_id_list(encoded: object) -> List[int]:
    """Normalise the result of ``encode`` into a list of ints.

    Args:
        encoded: A list, tuple, or tensor-like object of token ids.

    Returns:
        The token ids as a plain list of ints.

    Raises:
        TypeError: If the object cannot be interpreted as token ids.
    """
    tolist = getattr(encoded, "tolist", None)
    if callable(tolist):
        encoded = tolist()
    if isinstance(encoded, int):
        return [encoded]
    if isinstance(encoded, (list, tuple)):
        flat: List[int] = []
        for item in encoded:
            if isinstance(item, (list, tuple)):
                flat.extend(int(value) for value in item)
            else:
                flat.append(int(item))
        return flat
    raise TypeError("encode() did not return token ids")


class ConstrainedDecoder:
    """Generate schema-valid token sequences with a model and a guide."""

    def __init__(
        self,
        model: SupportsLLM,
        vocabulary: Vocabulary,
        max_tokens: int = MAX_CALL_TOKENS,
    ) -> None:
        """Initialise the decoder.

        Args:
            model: An object implementing the SDK interface.
            vocabulary: The decoded model vocabulary.
            max_tokens: Safety ceiling on generated tokens per call.
        """
        self._model = model
        self._vocab = vocabulary
        self._max_tokens = max_tokens
        self._max_value_chars = MAX_VALUE_TOKENS

    def encode(self, text: str) -> object:
        """Encode prompt text into token ids using the model."""
        return self._model.encode(text)

    def decode(
        self, prompt_ids: List[int], guide: SchemaGuide
    ) -> Tuple[List[int], str]:
        """Generate tokens that satisfy ``guide`` starting from a prompt.

        Args:
            prompt_ids: Token ids of the prompt (context) so far.
            guide: The grammar guide to satisfy.

        Returns:
            A tuple of the generated token ids and their decoded text.

        Raises:
            DecodeError: If generation cannot complete validly.
        """
        state = guide.start_state()
        generated: List[int] = []
        surface_parts: List[str] = []
        steps = 0
        slot_chars = 0
        while not guide.is_complete(state):
            if steps >= self._max_tokens:
                raise DecodeError("exceeded token budget before completion")
            in_slot = self._in_slot(guide, state)
            force_close = in_slot and slot_chars >= self._max_value_chars
            logits = self._model.get_logits_from_input_ids(
                prompt_ids + generated)
            token_id, next_state, text = self._select(
                guide, state, logits, force_close)
            generated.append(token_id)
            surface_parts.append(text)
            if in_slot and state.index == next_state.index:
                slot_chars += len(text)
            else:
                slot_chars = 0
            state = next_state
            steps += 1
        return generated, "".join(surface_parts)

    @staticmethod
    def _in_slot(guide: SchemaGuide, state: GuideState) -> bool:
        """Return whether ``state`` currently sits inside a value slot."""
        program = guide.program
        return state.index < len(program) and not isinstance(
            program[state.index], Literal)

    def _select(
        self,
        guide: SchemaGuide,
        state: GuideState,
        logits: List[float],
        force_close: bool = False,
    ) -> Tuple[int, GuideState, str]:
        """Pick the best allowed token for the current state.

        When ``force_close`` is set, tokens that end the current slot are
        preferred so an over-long value is always terminated cleanly.
        """
        allowed_ids: List[int] = []
        exiting_ids: List[int] = []
        next_states: Dict[int, GuideState] = {}
        for first_char, token_ids in self._vocab.by_first_char.items():
            if not guide.first_char_allowed(state, first_char):
                continue
            for token_id in token_ids:
                surface = self._vocab.surface[token_id]
                if surface is None:
                    continue
                advanced = guide.consume_token(state, surface)
                if advanced is None:
                    continue
                allowed_ids.append(token_id)
                next_states[token_id] = advanced
                if advanced.index > state.index:
                    exiting_ids.append(token_id)
        if not allowed_ids:
            return self._forced(guide, state)
        pool = exiting_ids if (force_close and exiting_ids) else allowed_ids
        scores = np.asarray(logits, dtype=np.float64)[pool]
        best = pool[int(np.argmax(scores))]
        surface = self._vocab.surface[best]
        assert surface is not None
        return best, next_states[best], surface

    def _forced(
        self, guide: SchemaGuide, state: GuideState,
    ) -> Tuple[int, GuideState, str]:
        """Force a deterministic literal character when nothing else fits.

        Some vocabularies may lack a multi-character token that fits a
        mandatory separator. As long as a single-character token exists
        for the required character, generation can always proceed.
        """
        required = self._required_char(guide, state)
        if required is not None:
            token_id = self._vocab.token_for_char.get(required)
            if token_id is not None:
                advanced = guide.consume_token(state, required)
                if advanced is not None:
                    return token_id, advanced, required
        raise DecodeError("no valid token available to continue output")

    @staticmethod
    def _required_char(
        guide: SchemaGuide, state: GuideState,
    ) -> Optional[str]:
        """Return the mandatory next character if the position is literal."""
        index = state.index
        offset = state.literal_offset
        program = guide.program
        while index < len(program):
            instruction = program[index]
            if isinstance(instruction, Literal):
                if offset >= len(instruction.text):
                    index += 1
                    offset = 0
                    continue
                return instruction.text[offset]
            return None
        return None
