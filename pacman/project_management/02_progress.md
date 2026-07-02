# Progress tracking (planned vs actual)

| Task | Owner | Planned | Actual | Status | Notes |
|------|-------|---------|--------|--------|-------|
| Repo, Makefile, lint/type setup | huwang | W1 | W1 | done | flake8 + mypy strict clean |
| Config loader (JSON + comments) | huwang | W1 | W1 | done | clamping + unknown-key drop |
| Maze adapter (A-Maze-ing) | kpanfero | W1 | W1–W2 | done | +1 day: README example was misleading, read source |
| Highscore system | huwang | W1 | W1 | done | JSON, top-10, robust to corruption |
| Player / ghost entities | kpanfero | W2 | W2 | done | tile-locked smooth movement |
| Level model + dot placement | huwang | W2 | W2 | done | reachability-limited dots |
| Ghost AI (chase/flee/return) | kpanfero | W2 | W2 | done | greedy heuristic + randomness |
| UI screens + HUD | huwang | W3 | W3 | done | menu, pause, game-over, victory |
| Cheat mode | kpanfero | W3 | W3 | done | F1–F6 |
| State machine + main loop | both | W3 | W3 | done | |
| Packaging (PyInstaller + Itch) | kpanfero | W4 | W4 | done | one-folder build, itch.toml + butler |
| pytest suite | huwang | W4 | W4 | done | 15 tests, config/highscore/maze/level |
| README + PM docs | both | W4 | W4 | done | |

**Velocity note:** the only slip was the maze adapter (one extra day), caused
by a misleading quick-start in the package README. Mitigation worked: reading
the real source unblocked it the same day.
