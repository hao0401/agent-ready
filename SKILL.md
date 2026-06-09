---
name: agent-ready
description: Use when the user wants to make a code repository ready for AI coding agents, generate or audit AGENTS.md, CLAUDE.md, GEMINI.md, Cursor rules, GitHub Copilot instructions, repository maps, agent workflows, agent readiness scores, or prompt-injection/secret/conflict checks for repo instructions.
metadata:
  short-description: Make repos ready for AI coding agents
---

# Agent Ready

Make a repository easier for coding agents to understand, modify, and verify. The
skill scans the repo, generates agent-facing instruction files, and audits those
files for conflicts, prompt-injection risk, secret exposure, and stale commands.

## Use Cases

- Generate `AGENTS.md` for Codex, OpenAI Codex CLI, or other coding agents.
- Generate companion files for Claude Code, Gemini CLI, GitHub Copilot, and Cursor.
- Audit existing agent instructions before a PR or release.
- Produce an "agent readiness" report with a score, missing pieces, and fixes.
- Build a project map: entry points, key configs, test/build commands, and do-not-edit areas.

## Workflow

1. Find this skill directory.
2. Use the one-command path first:

```powershell
python .\agent-ready.py <repo-path>
```

This scans the repo, generates agent instruction files, writes the readiness
report, and prints the score. If the command is run from inside the target
repository, `<repo-path>` is optional.

3. Use advanced commands only when the user asks for a narrower action:

```powershell
python .\agent-ready.py scan <repo-path>
python .\agent-ready.py lint <repo-path>
python .\agent-ready.py check <repo-path>
python .\agent-ready.py scorecard <repo-path>
python .\agent-ready.py snapshot <repo-path>
python .\agent-ready.py plan <repo-path>
python .\agent-ready.py diff <repo-path>
python .\agent-ready.py doctor <repo-path>
python .\agent-ready.py generate <repo-path>
python .\agent-ready.py validate <repo-path>
python .\agent-ready.py demo <repo-path>
python .\agent-ready.py badge <repo-path>
python .\agent-ready.py mcp <repo-path>
python .\agent-ready.py skill <repo-path>
python .\agent-ready.py ci <repo-path>
python .\agent-ready.py config <repo-path>
python .\agent-ready.py baseline <repo-path>
python .\agent-ready.py pr <repo-path>
```

Use `python .\agent-ready.py <repo-path> --minimal --badge` when introducing the
tool to an existing repository and the user wants low-noise output. This writes
`AGENTS.md` and core `.agent-ready` reports without companion tool files.

Use `python .\agent-ready.py <repo-path> --all --badge` when the user wants the
full GitHub-ready feature set in one pass.

Use `--force` only when the user clearly wants existing instruction files
overwritten. Without `--force`, the script skips files that already exist.

`validate` is plan-only by default. Use `--dry-run` when the user wants to make
that plan-only behavior explicit in scripts, and use `--execute` only after the
user trusts the repository commands. Never describe the safety scan as a
replacement for Gitleaks, TruffleHog, CodeQL, dependency audit, or human security
review.

Use `check` for CI-friendly read-only validation. It returns non-zero when the
score is below the minimum, `AGENTS.md` is missing, or high/critical findings
exist.

Use `scorecard` when the user wants an explainable score breakdown. It writes
`.agent-ready/scorecard.md` and `.agent-ready/scorecard.json` with points,
status, and a next fix for each scoring criterion.

Use `snapshot` when the user wants one readable artifact for PRs, dashboards, or
release notes. It writes `.agent-ready/summary.md` and
`.agent-ready/summary.json` with status, score, gaps, top fixes, optional
baseline diff summary, and useful next commands.

Use `config` to write `agent-ready.config.json` when a project needs stable CI
thresholds, `AGENTS.md` policy, documented false-positive ignores, or scan
overrides for commands/frameworks/entry points that heuristics cannot infer.
`check` auto-detects `agent-ready.config.json` and `.agent-ready/config.json`;
use `check --config <path>` for a nonstandard location.

Use `baseline` when a repo has existing findings but should still adopt CI now.
It writes `.agent-ready/baseline.json`; then `check --baseline` ignores only
matching existing findings while still failing on new findings, low score, or
missing required agent instructions.

Use `diff` after `baseline` when the user wants a readable adoption delta. It
writes `.agent-ready/diff.md` and `.agent-ready/diff.json` with score delta, new
findings, resolved findings, and unchanged findings. It returns non-zero when
new findings appear.

Use `check --baseline --ratchet` when the user wants gradual improvement: the
check also fails if the current score drops below the score recorded in the
baseline file.

Use `plan` when the user wants an actionable remediation route without changing
source files. It writes `.agent-ready/plan.md` and `.agent-ready/plan.json` with
P0/P1/P2 fixes, score impact hints, locations, and next commands.

For GitHub Actions, prefer `check --format github --write-report
--write-summary --write-comment --write-sarif --write-plan --github-summary --github-output`.
Add `--write-diff` when baseline mode is active. This emits annotations, writes
`.agent-ready/check.md`, `.agent-ready/summary.md`,
`.agent-ready/pr-comment.md`, and `.agent-ready/plan.md`, appends the markdown
report to `GITHUB_STEP_SUMMARY`, and exposes `passed`, `score`, `report-path`,
`summary-path`, `comment-path`, `plan-path`, `diff-path`, `sarif-path`, and
`exit-code` via `GITHUB_OUTPUT`. In the bundled Action, set
`post-comment: "true"` on pull request workflows to create or update the same
Agent Ready PR comment; grant `issues: write` permission for that workflow.

Use `doctor` when a user asks why generation, packaging, or validation may not
work on their machine. It checks Python, git, README writability, detected
commands, package managers, agent files, and high-risk findings without writing
repo files.

4. Before publishing or after editing the skill, run the self-check from the
   `agent-ready` directory:

```powershell
python -B -m unittest scripts.test_agent_ready
python -B scripts\release_check.py
```

## Output Files

The generator may create:

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
- `.agent-ready/validation.json`
- `.agent-ready/mcp-recommendations.md`
- `.agent-ready/skills/<repo>-workflow/SKILL.md`
- `.agent-ready/pr/PR_BODY.md`
- `.agent-ready/pr/agent-ready.patch`
- `.github/workflows/agent-ready.yml`

The generated GitHub Actions workflow is a starter workflow. It adds detected
Node and Python setup steps when local files make that clear, then runs detected
validation commands.

Do not invent commands. Prefer commands detected from package metadata and local
config files. If detection is uncertain, write the command as "Not detected" and
tell the user what should be verified manually. For known custom commands, add
them under `overrides.commands` in `agent-ready.config.json` so the correction is
reviewable and repeatable.

## Review Rules

When auditing agent instructions, check for:

- Conflicting package managers or commands across agent files.
- Instructions that contradict detected repo facts.
- Prompt-injection phrases in README/docs/instruction files.
- Hard-coded credentials or secret-looking values.
- Missing test/build commands.
- Overly broad rules that block normal development.
- Agent files that are too long to be useful in context.

## Scoring Guidance

Treat the score as a product signal, not a perfect security grade or proof that
the agent will reason better. Explain the highest-impact fixes before low-impact
polish. A good score requires:

- Clear project map.
- Correct test/build/run commands.
- At least one primary agent instruction file.
- No obvious instruction conflicts.
- No obvious prompt-injection or secret findings in files that agents will read.

## Safety

- Never expose secrets in the chat. If the scanner finds one, report the file and
  line, but redact the value.
- Do not delete or rewrite existing user files unless requested.
- For generated files, preserve existing files by default and tell the user when
  `--force` is needed.
- If a repo has multiple apps/packages, describe it as a monorepo and generate
  top-level guidance plus package-specific notes rather than pretending there is
  only one app.
