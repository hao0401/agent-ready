# Changelog

All notable changes to Agent Ready are documented here.

## 2.0.0 - 2026-06-09

### Changed

- Breaking safety change: `agent-ready validate` is plan-only by default and no longer executes detected project commands unless `--execute` is passed.
- `--dry-run` remains as an explicit plan-only alias, and `--dry-run` plus `--execute` is rejected as an invalid combination.
- Validation reports now record whether commands were actually executed and explain how to opt in safely.

### Documentation

- README, skill instructions, PR package guidance, and demo references now show `--execute` as the only command-running path.

## 1.2.0 - 2026-06-09

### Added

- `agent-ready.config.json` scan overrides for custom commands, frameworks, entry points, important directories, generated directories, package managers, and monorepo hints.
- Regression tests for override precedence and invalid override handling.

### Changed

- The generated config template now includes an explicit `overrides` section so complex repositories can correct heuristic misses without patching the scanner.
- Demo output uses normalized generated timestamps to reduce noisy showcase diffs.

## 1.1.0 - 2026-06-09

### Added

- Low-noise `--minimal` generation mode for teams that want only `AGENTS.md` and core `.agent-ready` reports.
- AGENTS.md quality scoring so instruction files earn points for command coverage, project map, safety guidance, and maintainability.
- Strict 100-point scorecard, replacing the previous raw-score cap behavior.
- Validation reports now make `--dry-run` safety status explicit.

### Changed

- README now documents honest limits, security boundaries, heuristic detection limits, and the fact that Agent Ready is not an agent framework.
- PR package validation guidance now recommends `agent-ready validate <repo> --dry-run` before executing detected commands.
- GitHub Action example now pins to an exact release tag.

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
