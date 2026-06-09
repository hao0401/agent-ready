# Agent Ready Summary

- Repository: `acme-workbench`
- Status: `failed`
- Score: `93/100`
- Findings: `1`

![Agent Ready](https://img.shields.io/badge/Agent%20Ready-93%2F100-brightgreen)

## Failures

- critical secret: Secret-looking value found; value redacted (README.md:16)

## Scorecard Gaps

- [missing] No secret findings: 0/7 - Remove the value, rotate it if real, and keep only redacted examples.

## Top Fixes

- [P0] Fix secret finding in README.md:16

## Baseline Diff

- Score delta: `-7`
- New findings: `1`
- Resolved findings: `0`
- Still present: `0`

## Useful Commands

- generate: `agent-ready . --all --badge`
- validate: `agent-ready validate .`
- check: `agent-ready check . --min-score 80 --write-report --write-summary --write-comment --write-scorecard --write-plan`
- baseline_diff: `agent-ready diff .`

## Related Files

- report: `.agent-ready/report.md`
- scorecard: `.agent-ready/scorecard.md`
- plan: `.agent-ready/plan.md`
- diff: `.agent-ready/diff.md`
- check: `.agent-ready/check.md`
