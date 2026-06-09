# Changelog

All notable changes to Agent Ready are documented here.

## 1.0.0 - 2026-06-09

### Added

- Dependency-free `agent-ready` CLI for scanning and preparing repositories for AI coding agents.
- One-command generation for `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Cursor rules, and GitHub Copilot instructions.
- Agent readiness score, scorecard, one-page summary, badge output, and full readiness report.
- Prompt-injection scan, redacted secret-looking finding scan, package-manager conflict detection, and monorepo hints.
- Baseline, baseline diff, score ratchet, dry-run validation, doctor mode, PR kit, and project-specific Codex skill generation.
- Composite GitHub Action with PR annotations, sticky PR comments, workflow summaries, outputs, and SARIF support.
- Reproducible demo repository, before/after artifacts, terminal screenshot, terminal GIF, and public showcase README.

### Verified

- Release gate compiles all Python entry points, runs the regression suite, regenerates demo assets, checks local Markdown links, scans public demo outputs, verifies wheel and sdist contents, and smoke-tests the installed console command.
