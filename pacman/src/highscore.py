"""Persistent top-10 highscore system stored as a JSON file.

The design goal is robustness: the game must never crash because the score
file is missing, empty or corrupted.  In every error case we simply start
from an empty list and overwrite the file on the next save.
"""
from __future__ import annotations

import json
from typing import List, Optional, Tuple, TypedDict

MAX_ENTRIES: int = 10
MAX_NAME_LEN: int = 10


class Entry(TypedDict):
    """One highscore record."""

    name: str
    score: int


def sanitize_name(name: str) -> str:
    """Return a valid player name (alphanumeric + spaces, max 10 chars).

    Invalid characters are stripped; an empty result becomes ``"PLAYER"``.
    """
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch == " ")
    cleaned = cleaned.strip()[:MAX_NAME_LEN]
    return cleaned if cleaned else "PLAYER"


class HighScores:
    """Load, query and persist the top-ten highscores."""

    def __init__(self, filename: str) -> None:
        """Create the manager bound to *filename* and load existing data."""
        self._filename = filename
        self._scores: List[Entry] = []
        self.load()

    @property
    def scores(self) -> List[Entry]:
        """The current ordered list of entries."""
        return self._scores

    def load(self) -> None:
        """Load highscores from disk, tolerating any file error."""
        self._scores = []
        try:
            with open(self._filename, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return  # no file yet, or corrupted -> start empty
        if not isinstance(data, list):
            return
        for item in data:
            entry = self._coerce(item)
            if entry is not None:
                self._scores.append(entry)
        self._scores.sort(key=self._sort_key, reverse=True)
        self._scores = self._scores[:MAX_ENTRIES]

    def save(self) -> None:
        """Write the current highscores to disk, ignoring write errors."""
        try:
            with open(self._filename, "w", encoding="utf-8") as handle:
                json.dump(self._scores, handle, indent=2)
        except OSError as error:
            print(f"[highscore] could not save scores: {error}")

    def qualifies(self, score: int) -> bool:
        """Return True if *score* would enter the top ten."""
        if score <= 0:
            return False
        if len(self._scores) < MAX_ENTRIES:
            return True
        return score > self._scores[-1]["score"]

    def add(self, name: str, score: int) -> None:
        """Insert a validated record and keep only the top ten."""
        if score < 0:
            score = 0
        entry: Entry = {"name": sanitize_name(name), "score": score}
        self._scores.append(entry)
        self._scores.sort(key=self._sort_key, reverse=True)
        self._scores = self._scores[:MAX_ENTRIES]
        self.save()

    def top(self, count: int = MAX_ENTRIES) -> List[Tuple[str, int]]:
        """Return up to *count* entries as plain (name, score) tuples."""
        return [(e["name"], e["score"]) for e in self._scores[:count]]

    @staticmethod
    def _sort_key(entry: Entry) -> int:
        return entry["score"]

    @staticmethod
    def _coerce(item: object) -> Optional[Entry]:
        """Validate one raw entry coming from the file."""
        if not isinstance(item, dict):
            return None
        name = item.get("name")
        score = item.get("score")
        if not isinstance(name, str) or not isinstance(score, int):
            return None
        if score < 0:
            return None
        entry: Entry = {"name": sanitize_name(name), "score": score}
        return entry
