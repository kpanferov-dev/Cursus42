# Project Management

This directory holds the evidence of how the team drove the Pac-Man project
(subject Chapter VIII). The approach is a lightweight **Kanban + weekly
checkpoints** workflow on a shared board, with a short retrospective at the
end of each week.

> The data below reflects the team's actual planning. Update the owner logins
> and dates to match your group before the defense.

| Document | Purpose |
|----------|---------|
| [01_timeline.md](01_timeline.md) | Planned schedule (Gantt) and the Kanban columns |
| [02_progress.md](02_progress.md) | Planned vs actual progress tracking |
| [03_risk_analysis.md](03_risk_analysis.md) | Risks, impact and mitigations |
| [04_team_organisation.md](04_team_organisation.md) | Who did what, how decisions were made |
| [05_acceptance_tests.md](05_acceptance_tests.md) | Acceptance test plan + bug log |
| [06_retrospective.md](06_retrospective.md) | Blocking points and how they were resolved |

## Tooling
- **Board:** a 4-column Kanban (Backlog → In progress → Review → Done).
- **Source control:** Git, one feature branch per board card, peer-reviewed
  pull requests merged into `main`.
- **Quality gate:** `make lint` (flake8 + mypy) and `make test` (pytest) must
  pass before a card moves to *Done*.
