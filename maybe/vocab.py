"""Vocabulary handling for constrained decoding.

The constrained decoder needs to know the *surface string* that every
token id contributes so it can decide, at each step, which tokens keep
the output valid. This module loads the vocabulary file returned by the
SDK and builds two fast lookup structures:

* ``surface`` - the decoded text of every token id;
* ``by_first_char`` - token ids grouped by the first character of their
  surface, so the decoder only tests a small, relevant subset per step.

Qwen (like GPT-2) stores its vocabulary using a *byte-level* BPE scheme:
each raw byte is mapped to a printable Unicode character, so the token
text in the file must be mapped back to real bytes before use. The
classic ``bytes_to_unicode`` table implements that mapping.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.io_utils import load_json


def bytes_to_unicode() -> Dict[int, str]:
    """Return the GPT-2/Qwen byte-to-unicode mapping.

    Returns:
        A mapping from byte value (0-255) to the printable Unicode
        character used to represent it in the vocabulary file.
    """
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


class Vocabulary:
    """An indexed, decoded view of a model vocabulary."""

    def __init__(self, surface: List[Optional[str]]) -> None:
        """Initialise from a list of token surfaces.

        Args:
            surface: ``surface[i]`` is the text of token id ``i`` or
                ``None`` for special/undecodable tokens.
        """
        self.surface = surface
        self.by_first_char: Dict[str, List[int]] = {}
        self.token_for_char: Dict[str, int] = {}
        for token_id, text in enumerate(surface):
            if not text:
                continue
            first = text[0]
            self.by_first_char.setdefault(first, []).append(token_id)
            if len(text) == 1 and first not in self.token_for_char:
                self.token_for_char[first] = token_id

    @property
    def size(self) -> int:
        """Return the number of token ids in the vocabulary."""
        return len(self.surface)

    @classmethod
    def from_file(cls, path: str) -> "Vocabulary":
        """Build a vocabulary from the SDK's vocabulary file.

        Args:
            path: Path to the vocabulary JSON file.

        Returns:
            A ready-to-use :class:`Vocabulary`.

        Raises:
            InputError: If the file cannot be read or parsed.
            ValueError: If the file structure is not recognised.
        """
        raw = load_json(path)
        token_to_id = cls._as_token_to_id(raw)
        decoder = {char: byte for byte, char in bytes_to_unicode().items()}
        highest = max(token_to_id.values())
        surface: List[Optional[str]] = [None] * (highest + 1)
        for token, token_id in token_to_id.items():
            surface[token_id] = cls._decode_token(token, decoder)
        return cls(surface)

    @staticmethod
    def _as_token_to_id(raw: object) -> Dict[str, int]:
        """Normalise several possible vocab layouts to ``token -> id``."""
        if isinstance(raw, dict):
            items = list(raw.items())
            if items and isinstance(items[0][1], int):
                return {str(token): int(idx) for token, idx in items}
            if items and isinstance(items[0][0], str):
                # Layout "id": "token" with string keys.
                converted: Dict[str, int] = {}
                for key, value in items:
                    converted[str(value)] = int(key)
                return converted
        if isinstance(raw, list):
            return {str(token): index for index, token in enumerate(raw)}
        raise ValueError("unrecognised vocabulary file structure")

    @staticmethod
    def _decode_token(token: str, decoder: Dict[str, int]) -> Optional[str]:
        """Decode a byte-level token string into real text.

        Special tokens (such as ``<|endoftext|>``) contain characters
        outside the byte-level alphabet; they are returned as ``None`` so
        the decoder never selects them inside a value.
        """
        try:
            data = bytes(decoder[char] for char in token)
        except KeyError:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None
