# PR: Make repository agent-ready

## Summary

- Add agent instruction files for Codex, Claude Code, Gemini CLI, GitHub Copilot, and Cursor.
- Add Agent Ready report and score badge.
- Document detected commands, project map, monorepo/package guidance, and safety rules.

## Files

- written: `AGENTS.md`
- written: `.agent-ready/report.md`
- written: `.agent-ready/agent-ready.json`
- written: `CLAUDE.md`
- written: `GEMINI.md`
- written: `.github/copilot-instructions.md`
- written: `.cursor/rules/agent-ready.mdc`
- written: `.agent-ready/scorecard.md`
- written: `.agent-ready/scorecard.json`
- written: `.agent-ready/summary.md`
- written: `.agent-ready/summary.json`
- written: `.github/workflows/agent-ready.yml`
- written: `.agent-ready/mcp-recommendations.md`
- written: `.agent-ready/skills/acme-workbench-workflow/SKILL.md`
- written: `.agent-ready/demo.md`

## Validation

- Run `agent-ready validate <repo>` to preview detected commands without executing them.
- Run `agent-ready validate <repo> --execute` only for repositories you trust.
