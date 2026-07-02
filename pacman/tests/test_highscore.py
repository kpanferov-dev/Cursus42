"""Tests for the persistent top-ten highscore system."""
from __future__ import annotations

from pathlib import Path

from src.highscore import MAX_ENTRIES, HighScores, sanitize_name


def test_sanitize_name_rules() -> None:
    assert sanitize_name("Bob!!") == "Bob"
    assert sanitize_name("a really long name here") == "a really l"
    assert sanitize_name("***") == "PLAYER"
    assert sanitize_name("Ab 12") == "Ab 12"


def test_add_keeps_sorted_top_ten(tmp_path: Path) -> None:
    hs = HighScores(str(tmp_path / "hs.json"))
    for i in range(15):
        hs.add(f"P{i}", i * 10)
    top = hs.top()
    assert len(top) == MAX_ENTRIES
    scores = [s for _, s in top]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 140


def test_qualifies(tmp_path: Path) -> None:
    hs = HighScores(str(tmp_path / "hs.json"))
    assert hs.qualifies(10) is True
    assert hs.qualifies(0) is False
    for i in range(MAX_ENTRIES):
        hs.add("X", 100)
    assert hs.qualifies(50) is False
    assert hs.qualifies(200) is True


def test_persistence_roundtrip(tmp_path: Path) -> None:
    path = str(tmp_path / "hs.json")
    HighScores(path).add("Alice", 500)
    reloaded = HighScores(path)
    assert reloaded.top()[0] == ("Alice", 500)


def test_corrupted_file_is_tolerated(tmp_path: Path) -> None:
    path = tmp_path / "hs.json"
    path.write_text("not json at all", encoding="utf-8")
    hs = HighScores(str(path))
    assert hs.top() == []
    hs.add("Bob", 42)  # must still be able to save over the junk
    assert hs.top()[0] == ("Bob", 42)


def test_negative_score_is_clamped(tmp_path: Path) -> None:
    hs = HighScores(str(tmp_path / "hs.json"))
    hs.add("Neg", -5)
    assert hs.top()[0][1] == 0
