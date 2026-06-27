# Project Management

> Fill these in with your team's real data — this is a starter template.

## Timeline / Gantt
- Week 1: config loader, maze adapter, highscore (DONE)
- Week 2: entities, level, ghost AI
- Week 3: UI screens, cheat mode, polish
- Week 4: packaging (Itch.io/Steam), docs, peer-review prep

## Progress tracking
| Task | Owner | Planned | Actual | Status |
|------|-------|---------|--------|--------|
| Maze adapter | <login> | W1 | W1 | done |
| Ghost AI | <login> | W2 |  | ... |

## Risk analysis
| Risk | Impact | Mitigation |
|------|--------|------------|
| Assigned maze package changes API | High | Adapter isolates the call site |
| Generator fails at runtime | Medium | MazeError handled, clean message |
| flake8/mypy failures at defense | Medium | `make lint` in CI before submit |

## Team organisation
Who did what, how decisions were made, how conflicts were resolved.

## Acceptance test plan
- Bad config (missing/extra/out-of-range keys) -> no crash, defaults used.
- Missing maze package -> clean error.
- Win path, lose path, highscore entry, pause/resume, all cheats.
