"""Basic unit tests for the non-graphical core (run with: pytest)."""
from src.config_loader import load_config, DEFAULTS
from src.highscore import HighScores, sanitize_name
from src.maze_loader import load_maze
from src.constants import PATH


def test_config_defaults_on_missing_file() -> None:
    cfg = load_config("/no/such/file.json")
    assert cfg["lives"] == DEFAULTS["lives"]
    assert len(cfg["levels"]) >= 10


def test_name_sanitisation() -> None:
    assert sanitize_name("Bad/Name!!") == "BadName"
    assert sanitize_name("") == "PLAYER"
    assert len(sanitize_name("x" * 50)) == 10


def test_highscore_topten(tmp_path) -> None:
    hs = HighScores(str(tmp_path / "h.json"))
    for i in range(15):
        hs.add(f"P{i}", i * 10)
    assert len(hs.top()) == 10
    assert hs.top()[0][1] == 140


def test_maze_corners_walkable() -> None:
    m = load_maze(21, 21, 42)
    assert all(m.grid[y][x] == PATH for x, y in m.corners)
    assert m.grid[m.player_start[1]][m.player_start[0]] == PATH
