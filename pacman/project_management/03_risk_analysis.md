# Risk analysis

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|------|-----------|--------|------------|--------|
| R1 | Assigned A-Maze-ing package has a different/changing API | Medium | High | All calls isolated in `src/maze_loader.py`; only the adapter changes if their interface differs | Controlled |
| R2 | Generator raises or returns an empty/odd maze at runtime | Medium | Medium | Wrapped in try/except → `MazeError`, handled cleanly with a menu message, no traceback | Controlled |
| R3 | A generated level is not fully connected (unclearable) | Low | High | Dots are placed only on the connected component reachable from the player spawn → every level is always clearable | Eliminated |
| R4 | Bad/edge-case config crashes the game | Medium | High | Loader clamps ranges, ignores unknown keys, falls back to defaults; covered by tests | Eliminated |
| R5 | flake8 / mypy failures discovered at the defense | Low | Medium | `make lint` + `make lint-strict` are part of the pre-merge gate | Controlled |
| R6 | Packaged build won't launch on a clean machine | Medium | High | PyInstaller one-folder build tested; bundles config + instructions; frozen mode auto-loads default config | Controlled |
| R7 | Highscore file missing or corrupted | Medium | Low | Loader tolerates any file error and starts from an empty list | Eliminated |
| R8 | Knowledge silo (only one person understands a module) | Medium | Medium | Pull-request reviews + pairing on the AI and packaging modules | Controlled |
