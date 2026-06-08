# Agent Ready Fix Plan

- Repository: `acme-workbench`
- Score: `90/100`
- Target score: `80/100`
- Check passed: `false`

## Priority Plan

- [P0] **Create primary AGENTS.md instructions**
  - Why: Most coding agents look for repository-level instructions before editing.
  - Action: Generate AGENTS.md plus companion instructions from the current repository scan.
  - Command: `agent-ready . --all --badge`
  - Location: `AGENTS.md`
  - Score impact: +20

## Next Commands

- `agent-ready . --all --badge`
- `agent-ready validate . --dry-run`
- `agent-ready check . --min-score 80 --write-report --write-summary --write-comment --write-plan`
