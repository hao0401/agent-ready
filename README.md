# Agent Ready

Make any repository ready for AI coding agents in one command.

Turn any repo into an AI-agent workspace: instructions, score, badge, CI, PR kit.

`agent-ready` scans a repository, generates agent instruction files, and reports
whether Codex, Claude Code, Cursor, Gemini CLI, or GitHub Copilot can safely work
inside it.

![Agent Ready](https://img.shields.io/badge/Agent%20Ready-CLI-blue)
![No Runtime Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Safe by Default](https://img.shields.io/badge/overwrite-safe%20by%20default-0f766e)

![Agent Ready terminal demo](assets/terminal-demo.svg)

## Why Developers Star It

- **One command to agent-ready a repo**: generates instructions, score report, badge, CI, PR package, MCP recommendations, and a project-specific Codex skill.
- **Built for the multi-agent reality**: writes `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Cursor rules, and GitHub Copilot instructions from the same repo scan.
- **Catches the weird stuff agents read**: flags prompt-injection text, secret-looking values, stale commands, package-manager conflicts, and monorepo ambiguity.
- **GitHub-friendly output**: creates a public score badge, before/after demo, PR body, patch file, and workflow starter.
- **Drop-in GitHub Action**: projects can use the published repository action and get PR annotations without writing install steps.

## Quick Start

Install from source:

```powershell
pipx install .
agent-ready --version
agent-ready C:\path\to\repo --all --badge
```

Or run without installation:

```powershell
python .\agent-ready.py C:\path\to\repo --all --badge
python -m agent_ready C:\path\to\repo --all --badge
```

That creates the full public-ready artifact set and inserts an Agent Ready score
badge into `README.md`.

Run it against the bundled example:

```powershell
python .\agent-ready.py examples\demo-repo --all --badge
python .\agent-ready.py plan examples\demo-repo --min-score 80
python .\agent-ready.py doctor examples\demo-repo
python .\agent-ready.py validate examples\demo-repo --dry-run
python .\agent-ready.py check examples\demo-repo --min-score 80 --format github --no-require-agents
```

## Real Demo

The repository includes a real example monorepo and generated output:

- Input repo: [`examples/demo-repo`](examples/demo-repo)
- One-page summary: [`examples/demo-output/summary.md`](examples/demo-output/summary.md)
- PR comment: [`examples/demo-output/pr-comment.md`](examples/demo-output/pr-comment.md)
- Generated report: [`examples/demo-output/report.md`](examples/demo-output/report.md)
- Scorecard: [`examples/demo-output/scorecard.md`](examples/demo-output/scorecard.md)
- CI check report: [`examples/demo-output/check.md`](examples/demo-output/check.md)
- SARIF report: [`examples/demo-output/check.sarif`](examples/demo-output/check.sarif)
- Prioritized fix plan: [`examples/demo-output/plan.md`](examples/demo-output/plan.md)
- Baseline diff: [`examples/demo-output/diff.md`](examples/demo-output/diff.md)
- Config template: [`examples/demo-output/agent-ready.config.json`](examples/demo-output/agent-ready.config.json)
- Baseline file: [`examples/demo-output/baseline.json`](examples/demo-output/baseline.json)
- Before/after page: [`examples/demo-output/before-after.md`](examples/demo-output/before-after.md)
- Validation dry run: [`examples/demo-output/validation-dry-run.md`](examples/demo-output/validation-dry-run.md)
- PR body: [`examples/demo-output/PR_BODY.md`](examples/demo-output/PR_BODY.md)
- CI workflow: [`examples/demo-output/agent-ready.yml`](examples/demo-output/agent-ready.yml)
- Static screenshot: [`assets/terminal-demo.png`](assets/terminal-demo.png)
- Animated terminal GIF: [`assets/terminal-demo.gif`](assets/terminal-demo.gif)

Regenerate the demo assets:

```powershell
python -m pip install Pillow
python .\scripts\build_demo_assets.py --require-images
```

Example output:

```text
Repo: acme-workbench
Score: 100/100

Files:
- written: AGENTS.md
- written: CLAUDE.md
- written: GEMINI.md
- written: .github/copilot-instructions.md
- written: .cursor/rules/agent-ready.mdc
- written: .agent-ready/report.md
- written: .github/workflows/agent-ready.yml
- updated: README.md
```

## What It Generates

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.github/copilot-instructions.md`
- `.cursor/rules/agent-ready.mdc`
- `.agent-ready/report.md`
- `.agent-ready/agent-ready.json`
- `.agent-ready/summary.md`
- `.agent-ready/summary.json`
- `.agent-ready/pr-comment.md`
- `.agent-ready/pr-comment.json`
- `.agent-ready/scorecard.md`
- `.agent-ready/scorecard.json`
- `.agent-ready/check.md`
- `.agent-ready/check.json`
- `.agent-ready/check.sarif`
- `.agent-ready/plan.md`
- `.agent-ready/plan.json`
- `.agent-ready/diff.md`
- `.agent-ready/diff.json`
- `.agent-ready/baseline.json`
- `agent-ready.config.json`
- `.agent-ready/demo.md`
- `.agent-ready/validation.md`
- `.agent-ready/mcp-recommendations.md`
- `.agent-ready/skills/<repo>-workflow/SKILL.md`
- `.agent-ready/pr/PR_BODY.md`
- `.agent-ready/pr/agent-ready.patch`
- `.github/workflows/agent-ready.yml`

## Before / After

| Before | After |
| --- | --- |
| Agents infer commands from scattered files | Commands are detected and written into `AGENTS.md` |
| Tool-specific instructions drift silently | Codex, Claude, Gemini, Cursor, and Copilot instructions share one repo scan |
| Readiness score looks like a black box | `.agent-ready/scorecard.md` shows every scoring criterion and fix |
| Reviewers need one artifact, not five links | `.agent-ready/summary.md` summarizes status, gaps, top fixes, and diff |
| Prompt-injection and secret-looking docs are easy to miss | High-risk findings are surfaced with file and line |
| GitHub visitors cannot see agent readiness | README badge and `.agent-ready/report.md` show a score |
| CI says "failed" but not what to fix first | `.agent-ready/plan.md` gives P0/P1/P2 remediation steps |
| Gradual adoption hides whether things improved | `.agent-ready/diff.md` shows new, resolved, and unchanged findings |
| PR authors write setup notes by hand | PR body, patch package, CI workflow, and dry-run validation are generated |

## Differentiated Features

- **Agent readiness score**: a visible `0-100` signal for GitHub READMEs and PRs.
- **One-page snapshot**: `agent-ready snapshot .` writes `.agent-ready/summary.md` and `.agent-ready/summary.json` for PRs, dashboards, and release notes.
- **Explainable scorecard**: `agent-ready scorecard .` writes a scoring breakdown with points, status, and next fix per criterion.
- **Multi-agent output**: one scan creates instructions for Codex, Claude, Gemini, Cursor, and Copilot.
- **Prompt-injection audit**: flags suspicious instructions in docs agents are likely to read.
- **Secret-looking scan**: reports file and line while redacting values.
- **Command truthing**: detects install, run, test, build, lint, and typecheck commands from local files.
- **Monorepo map**: detects package-level projects under `apps/`, `packages/`, `services/`, and `libs/`.
- **Project config**: stores CI thresholds, `AGENTS.md` requirements, and known false-positive ignores in `agent-ready.config.json`.
- **Baseline mode**: records existing findings so CI can block only new agent-readiness regressions during adoption.
- **Baseline diff**: `agent-ready diff .` compares current findings to `.agent-ready/baseline.json` and reports score delta, new findings, resolved findings, and unchanged debt.
- **Score ratchet**: `check --ratchet` blocks score regressions below the recorded baseline score.
- **Dry-run validation**: previews detected validation commands before executing local scripts.
- **CI check mode**: `agent-ready check .` fails fast on low score, missing `AGENTS.md`, or high-risk findings.
- **GitHub annotations**: `agent-ready check . --format github` emits `::error` annotations with file and line when available.
- **Check reports on demand**: `agent-ready check . --write-report --write-summary --write-comment` writes CI artifacts plus reviewer-friendly PR context.
- **PR comment artifact**: `.agent-ready/pr-comment.md` is short enough for PR bots while preserving score, blockers, top fixes, and artifact links.
- **Sticky PR comments**: the bundled Action can update the same pull request comment on each run with `post-comment: "true"`.
- **Prioritized fix plan**: `agent-ready plan .` writes `.agent-ready/plan.md` and `.agent-ready/plan.json` with P0/P1/P2 remediation items.
- **Action outputs**: the bundled GitHub Action exposes `passed`, `score`, `report-path`, `summary-path`, `comment-path`, `plan-path`, `diff-path`, `sarif-path`, and `exit-code` for later workflow steps.
- **Marketplace-ready action metadata**: `action.yml` includes composite action inputs, outputs, SARIF support, and GitHub Marketplace branding.
- **SARIF for code scanning**: `agent-ready check . --write-sarif` writes `.agent-ready/check.sarif` for GitHub code scanning upload.
- **Doctor mode**: `agent-ready doctor .` checks Python, git, README writability, package managers, commands, agent files, and high-risk findings.
- **GitHub PR kit**: generates a PR body, patch package, score report, badge, and CI workflow.
- **Project skill generator**: creates a repo-specific Codex skill under `.agent-ready/skills/`.
- **MCP recommendations**: suggests useful MCPs from local repo signals.

## Why It Exists

READMEs are written for humans. Coding agents need sharper context:

- How to install, run, test, build, lint, and typecheck.
- Which directories matter.
- Which directories should never be edited.
- Which package manager the repo actually uses.
- Whether agent instruction files conflict with each other.
- Whether docs contain prompt-injection or secret-looking text.

## Command Menu

Default one-command path:

```powershell
python .\agent-ready.py C:\path\to\repo --all --badge
```

Scan only:

```powershell
python .\agent-ready.py scan C:\path\to\repo
```

Generate core files only:

```powershell
python .\agent-ready.py generate C:\path\to\repo
```

Write an explainable score breakdown:

```powershell
python .\agent-ready.py scorecard C:\path\to\repo
```

Write a one-page summary:

```powershell
python .\agent-ready.py snapshot C:\path\to\repo
```

Write an actionable fix plan without changing source files:

```powershell
python .\agent-ready.py plan C:\path\to\repo --min-score 80
```

Write a starter config:

```powershell
python .\agent-ready.py config C:\path\to\repo
```

Capture the current findings as a baseline:

```powershell
python .\agent-ready.py baseline C:\path\to\repo
python .\agent-ready.py diff C:\path\to\repo
python .\agent-ready.py check C:\path\to\repo --baseline
python .\agent-ready.py check C:\path\to\repo --baseline --ratchet
```

Preview validation without running repo commands:

```powershell
python .\agent-ready.py validate C:\path\to\repo --dry-run
```

Run a read-only CI check:

```powershell
python .\agent-ready.py check C:\path\to\repo --min-score 80
python .\agent-ready.py check C:\path\to\repo --min-score 80 --format github --write-report --write-summary --write-comment --write-scorecard --write-plan
python .\agent-ready.py check C:\path\to\repo --baseline --write-diff
python .\agent-ready.py check C:\path\to\repo --min-score 80 --write-sarif
python .\agent-ready.py check C:\path\to\repo --config agent-ready.config.json
```

Config example:

```json
{
  "check": {
    "min_score": 80,
    "require_agents": true,
    "baseline": ".agent-ready/baseline.json",
    "ratchet": false
  },
  "ignore_findings": [
    {
      "kind": "prompt-injection",
      "path": "docs/known-safe-example.md",
      "message_contains": "Prompt-injection-like instruction found"
    }
  ]
}
```

Diagnose local setup before generation:

```powershell
python .\agent-ready.py doctor C:\path\to\repo
```

Use it in GitHub Actions:

The root [action.yml](action.yml) is a composite action with Marketplace
branding, typed inputs, CI summaries, and reusable outputs.

```yaml
name: Agent Ready

on:
  pull_request:
  push:
    branches: [main, master]

permissions:
  contents: read
  issues: write
  security-events: write

jobs:
  agent-ready:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hao0401/agent-ready@v1
        id: agent_ready
        with:
          path: .
          config: agent-ready.config.json
          baseline: .agent-ready/baseline.json
          ratchet: "true"
          min-score: "80"
          format: github
          write-report: "true"
          write-summary: "true"
          write-comment: "true"
          write-plan: "true"
          write-diff: "true"
          sarif: "true"
          post-comment: "true"
      - name: Print readiness score
        run: echo "Agent Ready score is ${{ steps.agent_ready.outputs.score }}"
      - name: Print fix plan path
        run: echo "Fix plan is ${{ steps.agent_ready.outputs.plan-path }}"
      - name: Print summary path
        run: echo "Summary is ${{ steps.agent_ready.outputs.summary-path }}"
      - name: Print PR comment path
        run: echo "PR comment is ${{ steps.agent_ready.outputs.comment-path }}"
      - name: Print baseline diff path
        run: echo "Baseline diff is ${{ steps.agent_ready.outputs.diff-path }}"
      - name: Upload Agent Ready SARIF
        if: always() && steps.agent_ready.outputs.sarif-path != ''
        uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: ${{ steps.agent_ready.outputs.sarif-path }}
          category: agent-ready
```

Before publishing the repository, run:

```powershell
python -B scripts\dev.py publish-check
```

That preflight expects a local Git repository, an `origin` remote, no placeholder
Action path, and an authenticated GitHub CLI session.

Create a PR-ready package:

```powershell
python .\agent-ready.py pr C:\path\to\repo
```

Use `--force` only when you want to overwrite existing instruction files.

```powershell
python .\agent-ready.py C:\path\to\repo --force
```

`validate` executes detected project commands such as `npm run test` or
`python -m pytest`. Preview the plan without running commands:

```powershell
python .\agent-ready.py validate C:\path\to\repo --dry-run
```

If you run the short entry point from inside the target repository, the path is
optional:

```powershell
python C:\path\to\agent-ready\agent-ready.py --all --badge
```

## Self Check

From the `agent-ready` directory:

```powershell
python -B scripts\dev.py test check release clean
python -B scripts\dev.py publish-check
```

If `make` is available:

```powershell
make test
make check
make build
make clean
make publish-check
```

Or run the checks directly:

```powershell
python -B -m unittest scripts.test_agent_ready
python -B scripts\release_check.py
```

## Project Files

- License: [`LICENSE`](LICENSE)
- Contributing guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)
- Package config: [`pyproject.toml`](pyproject.toml)
- GitHub Action: [`action.yml`](action.yml)
- GitHub workflows: [`.github/workflows`](.github/workflows)
- Local action smoke test: [`.github/workflows/action-smoke.yml`](.github/workflows/action-smoke.yml)

## Agent Readiness Score

The report gives a `0-100` score based on:

- Detected languages, configs, entry points, and project map.
- Detected run/test/build/lint/typecheck commands.
- Presence of primary agent instructions.
- Prompt-injection findings.
- Secret-looking findings.
- Conflicting package manager or command guidance across agent files.

## Codex Skill

This repository is also a Codex skill. Install or place the `agent-ready` folder
in your Codex skills directory, then ask:

```text
Use $agent-ready to scan this repository, generate agent instruction files, and report its agent readiness score.
```

## Design Goals

- No runtime dependencies.
- Safe by default: existing files are skipped unless `--force` is passed.
- Useful output even before generation.
- Works on Windows, macOS, and Linux.
- Small enough for agents to understand and modify.
