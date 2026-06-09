#!/usr/bin/env python3
"""Scan repositories and generate agent-ready instruction files.

This script intentionally uses only the Python standard library so the skill can
run in fresh repositories without a dependency install step.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import __version__
from .baseline import *  # re-export baseline helpers for compatibility
from .comment import *  # re-export PR comment helpers for compatibility
from .config import *  # re-export config helpers for compatibility
from .files import *  # re-export file helpers for compatibility
from .github import *  # re-export GitHub helpers for compatibility
from .payload import *  # re-export payload helpers for compatibility
from .plan import *  # re-export fix-plan helpers for compatibility
from .scan import *  # re-export scanner APIs for compatibility
from .sarif import *  # re-export SARIF helpers for compatibility
from .scorecard import *  # re-export scorecard helpers for compatibility
from .validation import *  # re-export validation helpers for compatibility


def render_config_template() -> str:
    data = {
        "check": {
            "min_score": 80,
            "require_agents": True,
            "baseline": ".agent-ready/baseline.json",
            "ratchet": False,
        },
        "ignore_findings": [
            {
                "kind": "prompt-injection",
                "path": "docs/known-safe-example.md",
                "message_contains": "Prompt-injection-like instruction found",
            }
        ],
        "overrides": {
            "commands": {
                "test": [],
                "build": [],
                "lint": [],
                "typecheck": [],
                "run": [],
                "install": [],
            },
            "frameworks": [],
            "entry_points": [],
            "important_dirs": [],
            "generated_dirs": [],
            "package_managers": [],
            "monorepo_hints": [],
        },
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_config_template(root: Path, force: bool = False) -> dict[str, str]:
    root = root.resolve()
    return {"agent-ready.config.json": write_file(root / "agent-ready.config.json", render_config_template(), force=force)}


def command_block(commands: dict[str, list[str]]) -> str:
    labels = [
        ("install", "Install"),
        ("run", "Run locally"),
        ("test", "Test"),
        ("build", "Build"),
        ("lint", "Lint"),
        ("typecheck", "Typecheck"),
    ]
    lines: list[str] = []
    for key, label in labels:
        values = commands.get(key, [])
        if values:
            lines.append(f"- {label}: `{values[0]}`")
            for extra in values[1:3]:
                lines.append(f"  - Also detected: `{extra}`")
        else:
            lines.append(f"- {label}: Not detected")
    return "\n".join(lines)


def python_command_note() -> str:
    return "If `python` is not available on macOS or Linux, run the same command with `python3`."


def list_or_none(items: list[str], limit: int = 12) -> str:
    if not items:
        return "- Not detected"
    return "\n".join(f"- `{item}`" for item in items[:limit])


def language_summary(scan: RepoScan) -> str:
    if not scan.languages:
        return "Not detected"
    return ", ".join(f"{item['language']} ({item['files']})" for item in scan.languages[:5])


def package_summary_block(scan: RepoScan) -> str:
    if not scan.packages:
        return "- No package-level projects detected"
    lines: list[str] = []
    for package in scan.packages[:12]:
        commands = package.get("commands", {})
        command_bits = []
        for key in ["run", "test", "build", "lint", "typecheck"]:
            values = commands.get(key, [])
            if values:
                command_bits.append(f"{key}: `{values[0]}`")
        command_text = "; ".join(command_bits) if command_bits else "commands: Not detected"
        frameworks = ", ".join(package.get("frameworks", [])) or "Not detected"
        managers = ", ".join(package.get("package_managers", [])) or "Not detected"
        lines.append(f"- `{package['path']}` - {frameworks}; {managers}; {command_text}")
    return "\n".join(lines)


def render_agents_md(scan: RepoScan) -> str:
    frameworks = ", ".join(scan.frameworks) if scan.frameworks else "Not detected"
    package_managers = ", ".join(scan.package_managers) if scan.package_managers else "Not detected"
    monorepo = "\n".join(f"- {hint}" for hint in scan.monorepo_hints) if scan.monorepo_hints else "- No monorepo hints detected"
    generated = list_or_none(scan.generated_dirs)
    important = list_or_none(scan.important_dirs)
    entries = list_or_none(scan.entry_points)
    configs = list_or_none(scan.config_files)
    return f"""# AGENTS.md

Instructions for AI coding agents working in this repository.

## Repository Snapshot

- Repository: `{scan.repo_name}`
- Main languages: {language_summary(scan)}
- Frameworks/libraries detected: {frameworks}
- Package managers/build tools: {package_managers}

## Project Map

Entry points:

{entries}

Important directories:

{important}

Configuration files:

{configs}

Generated or dependency directories agents should avoid editing:

{generated}

Monorepo signals:

{monorepo}

Package-level projects:

{package_summary_block(scan)}

## Commands

{command_block(scan.commands)}

If a command is marked "Not detected", inspect package metadata or CI config before
claiming it works.

{python_command_note()}

## Agent Workflow

1. Read this file before editing.
2. Inspect the smallest relevant module before changing code.
3. Prefer existing patterns, helpers, and framework conventions.
4. Keep edits scoped to the requested behavior.
5. Run the most specific detected validation command before finishing.
6. Report any command that could not be run, including the reason.

## Safety Rules

- Do not edit generated output, dependency folders, caches, or build artifacts.
- Do not expose secrets. If a secret-looking value is found, report only the file
  and line with the value redacted.
- Do not invent test/build commands. Use detected commands or explain what needs
  manual verification.
- For broad changes, check CI workflow files and package metadata before editing.
- If repository facts conflict with these instructions, trust current files and
  update this instruction file in the same change.
"""


def render_companion(scan: RepoScan, tool_name: str) -> str:
    return f"""# {tool_name} Repository Instructions

Use `AGENTS.md` as the primary source of repository instructions.

Key detected commands:

{command_block(scan.commands)}

Project map:

- Languages: {language_summary(scan)}
- Frameworks: {", ".join(scan.frameworks) if scan.frameworks else "Not detected"}
- Entry points: {", ".join(scan.entry_points[:8]) if scan.entry_points else "Not detected"}

Before finishing changes, run the most specific relevant validation command that
is available. If validation cannot be run, explain why.

{python_command_note()}
"""


def render_cursor_rule(scan: RepoScan) -> str:
    return f"""---
description: Repository instructions for AI coding agents
alwaysApply: true
---

# Agent Ready Rules

Follow `AGENTS.md` first. Keep changes scoped, prefer existing project patterns,
and run relevant validation before finishing.

Detected commands:

{command_block(scan.commands)}

Avoid editing generated/dependency directories:

{list_or_none(scan.generated_dirs)}
"""


def render_report(scan: RepoScan) -> str:
    finding_lines = []
    if scan.findings:
        for finding in scan.findings:
            location = ""
            if finding.path:
                location = f" ({finding.path}"
                if finding.line:
                    location += f":{finding.line}"
                location += ")"
            finding_lines.append(f"- [{finding.severity}] {finding.kind}: {finding.message}{location}")
    else:
        finding_lines.append("- No findings")
    reasons = "\n".join(f"- {reason}" for reason in scan.score_reasons) or "- No score reasons"
    missing: list[str] = []
    if not scan.commands.get("test"):
        missing.append("Add or document a test command")
    if not scan.commands.get("build"):
        missing.append("Add or document a build command")
    if "AGENTS.md" not in scan.agent_files:
        missing.append("Create AGENTS.md")
    if not scan.entry_points:
        missing.append("Document entry points")
    if not scan.findings:
        missing.append("No major fixes detected")
    missing_block = "\n".join(f"- {item}" for item in missing)
    badge_color = "brightgreen" if scan.score >= 85 else "yellow" if scan.score >= 60 else "orange" if scan.score >= 40 else "red"
    badge = f"![Agent Ready](https://img.shields.io/badge/Agent%20Ready-{scan.score}%2F100-{badge_color})"
    return f"""# Agent Ready Report

Score: **{scan.score}/100**

{badge}

## Score Reasons

{reasons}

## Findings

{chr(10).join(finding_lines)}

## Recommended Fixes

{missing_block}

## Detected Commands

{command_block(scan.commands)}

## Detected Project Map

- Languages: {language_summary(scan)}
- Frameworks: {", ".join(scan.frameworks) if scan.frameworks else "Not detected"}
- Package managers/build tools: {", ".join(scan.package_managers) if scan.package_managers else "Not detected"}

Entry points:

{list_or_none(scan.entry_points)}

Important directories:

{list_or_none(scan.important_dirs)}

Generated/dependency directories:

{list_or_none(scan.generated_dirs)}

## Package-Level Projects

{package_summary_block(scan)}
"""


def recommend_mcp(scan: RepoScan) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    config_set = set(scan.config_files)
    frameworks = set(scan.frameworks)
    dirs = set(scan.important_dirs)
    if ".github/workflows" in config_set or (Path(scan.root) / ".github").exists():
        recs.append({"name": "GitHub MCP", "reason": "Repository has GitHub workflow or metadata files; useful for PRs, issues, and CI inspection."})
    if "pytest" in frameworks or "Playwright" in frameworks or (Path(scan.root) / "playwright.config.ts").exists():
        recs.append({"name": "Playwright MCP", "reason": "Useful for browser validation and UI smoke tests."})
    if any((Path(scan.root) / name).exists() for name in ["docker-compose.yml", "compose.yml"]):
        recs.append({"name": "Docker MCP", "reason": "Compose files detected; useful for local service orchestration."})
    if any((Path(scan.root) / name).exists() for name in ["prisma", "migrations", "alembic"]) or "api" in dirs:
        recs.append({"name": "Database MCP", "reason": "Database or API structure detected; useful for schema and migration work."})
    if (Path(scan.root) / "sentry.properties").exists():
        recs.append({"name": "Sentry MCP", "reason": "Sentry config detected; useful for production error context."})
    if not recs:
        recs.append({"name": "No specific MCP recommendation", "reason": "No strong local signal found; start with filesystem and shell access only."})
    return recs


def render_mcp_report(scan: RepoScan) -> str:
    lines = [f"- **{rec['name']}**: {rec['reason']}" for rec in recommend_mcp(scan)]
    return f"""# MCP Recommendations

Repository: `{scan.repo_name}`

{chr(10).join(lines)}

These are recommendations from local repository signals, not required dependencies.
"""


def render_demo(scan: RepoScan) -> str:
    before = [
        "Agent must infer package manager from scattered files.",
        "Test/build commands may be guessed or skipped.",
        "Tool-specific instruction files can conflict silently.",
        "Prompt-injection and secret-looking text may be read without warning.",
    ]
    after = [
        f"Agent readiness score: **{scan.score}/100**.",
        "Primary and companion instruction files are generated.",
        "Detected commands, project map, and package-level projects are documented.",
        "Prompt-injection, secret-looking values, and package-manager conflicts are reported.",
    ]
    return f"""# Agent Ready Demo

Repository: `{scan.repo_name}`

## Before

{chr(10).join(f"- {item}" for item in before)}

## After

{chr(10).join(f"- {item}" for item in after)}

## Badge

{badge_markdown(scan)}

## Top Commands

{command_block(scan.commands)}

## Package-Level Projects

{package_summary_block(scan)}
"""


def insert_badge(root: Path, force: bool = False) -> dict[str, str]:
    scan = scan_repo(root)
    readme = root / "README.md"
    badge = badge_markdown(scan)
    if not readme.exists():
        write_file(readme, f"# {scan.repo_name}{os.linesep}{os.linesep}{badge}{os.linesep}", force=True)
        return {"README.md": "written"}
    text = read_text(readme, max_bytes=1_000_000)
    if text == "" and readme.stat().st_size > 0:
        return {"README.md": "skipped-large-or-unreadable"}
    if "img.shields.io/badge/Agent%20Ready" in text:
        new_text = re.sub(r"!\[Agent Ready\]\(https://img\.shields\.io/badge/Agent%20Ready-[^)]+\)", badge, text)
        readme.write_text(new_text, encoding="utf-8")
        return {"README.md": "updated"}
    if not force and "![Agent Ready]" in text:
        return {"README.md": "skipped"}
    lines = text.splitlines()
    insert_at = 1 if lines and lines[0].startswith("#") else 0
    lines.insert(insert_at, badge)
    lines.insert(insert_at + 1, "")
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"README.md": "updated"}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "repo"


def render_project_skill(scan: RepoScan) -> str:
    skill_name = f"{slugify(scan.repo_name)}-workflow"
    return f"""---
name: {skill_name}
description: Use when working inside the {scan.repo_name} repository and needing project-specific commands, package map, validation steps, or agent workflow guidance.
---

# {scan.repo_name} Workflow

## Repository Map

- Languages: {language_summary(scan)}
- Frameworks: {", ".join(scan.frameworks) if scan.frameworks else "Not detected"}
- Package managers/build tools: {", ".join(scan.package_managers) if scan.package_managers else "Not detected"}

Entry points:

{list_or_none(scan.entry_points)}

Package-level projects:

{package_summary_block(scan)}

## Commands

{command_block(scan.commands)}

## Workflow

1. Read `AGENTS.md` first.
2. Inspect the smallest relevant module before editing.
3. Use package-level commands when working in a package directory.
4. Run the most specific validation command before finishing.
5. Report skipped validation with the reason.
"""


def render_ci_workflow(scan: RepoScan) -> str:
    install_commands = scan.commands.get("install", [])[:1]
    commands = []
    for key in ["test", "build", "lint", "typecheck"]:
        values = scan.commands.get(key, [])
        if values:
            commands.append(values[0])
    config_set = set(scan.config_files)
    managers = set(scan.package_managers)
    setup_steps: list[str] = []
    if "package.json" in config_set:
        if "pnpm" in managers:
            setup_steps.append(
                """      - uses: pnpm/action-setup@v4
        with:
          version: 10"""
            )
        cache_manager = next((manager for manager in ["pnpm", "yarn", "npm"] if manager in managers), "")
        cache_line = f'\n          cache: "{cache_manager}"' if cache_manager else ""
        setup_steps.append(
            """      - uses: actions/setup-node@v4
        with:
          node-version: "20"{cache_line}""".format(
                cache_line=cache_line
            )
        )
    if any(item in config_set for item in ["pyproject.toml", "requirements.txt", "setup.py", "pytest.ini"]):
        setup_steps.append(
            '      - uses: actions/setup-python@v5\n'
            '        with:\n'
            '          python-version: "3.x"'
        )
    install_script = "\n".join(f"          {command}" for command in install_commands) or "          echo \"No install command detected\""
    command_script = "\n".join(f"          {command}" for command in commands) or "          echo \"No validation command detected\""
    setup_block = "\n".join(setup_steps)
    if setup_block:
        setup_block += "\n"
    return f"""name: Agent Ready

on:
  pull_request:
  push:
    branches: [ main, master ]

jobs:
  agent-ready:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
{setup_block}      - name: Agent instruction smoke check
        run: |
          test -f AGENTS.md
          test -f .agent-ready/report.md || true
      - name: Install dependencies
        run: |
{install_script}
      - name: Detected validation commands
        run: |
{command_script}
"""


def render_pr_summary(scan: RepoScan, statuses: dict[str, str]) -> str:
    changed = "\n".join(f"- {status}: `{path}`" for path, status in statuses.items())
    return f"""# PR: Make repository agent-ready

## Summary

- Add agent instruction files for Codex, Claude Code, Gemini CLI, GitHub Copilot, and Cursor.
- Add Agent Ready report and score badge.
- Document detected commands, project map, monorepo/package guidance, and safety rules.

## Files

{changed}

## Validation

- Run `agent-ready validate <repo> --dry-run` before executing detected commands.
- Run `agent-ready validate <repo>` only for repositories you trust.
"""


def create_pr_patch(root: Path, force: bool) -> dict[str, str]:
    root = root.resolve()
    scan, statuses = generate_files(root, force=force)
    statuses.update(generate_extra_files(root, scan, force=force, include_ci=True, include_mcp=True, include_skill=True, include_demo=True))
    patch_dir = root / ".agent-ready" / "pr"
    patch_dir.mkdir(parents=True, exist_ok=True)
    summary_path = patch_dir / "PR_BODY.md"
    summary_path.write_text(render_pr_summary(scan, statuses), encoding="utf-8")
    patch_path = patch_dir / "agent-ready.patch"
    if (root / ".git").exists() and shutil.which("git"):
        result = subprocess.run("git diff -- AGENTS.md CLAUDE.md GEMINI.md .github .cursor .agent-ready", cwd=str(root), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        patch_path.write_text(result.stdout or "# No git diff output\n", encoding="utf-8")
    else:
        patch_path.write_text("# Git repository not detected; generated files are present in the working tree.\n", encoding="utf-8")
    statuses[".agent-ready/pr/PR_BODY.md"] = "written"
    statuses[".agent-ready/pr/agent-ready.patch"] = "written"
    return statuses


def generate_extra_files(
    root: Path,
    scan: RepoScan,
    force: bool,
    include_ci: bool = False,
    include_mcp: bool = False,
    include_skill: bool = False,
    include_demo: bool = False,
) -> dict[str, str]:
    outputs: dict[str, str] = {}
    if include_ci:
        outputs[".github/workflows/agent-ready.yml"] = render_ci_workflow(scan)
    if include_mcp:
        outputs[".agent-ready/mcp-recommendations.md"] = render_mcp_report(scan)
    if include_skill:
        outputs[f".agent-ready/skills/{slugify(scan.repo_name)}-workflow/SKILL.md"] = render_project_skill(scan)
    if include_demo:
        outputs[".agent-ready/demo.md"] = render_demo(scan)
    statuses: dict[str, str] = {}
    for relative, content in outputs.items():
        statuses[relative] = write_file(root / relative, content, force=force)
    return statuses


def generate_files(root: Path, force: bool, companion: bool = True) -> tuple[RepoScan, dict[str, str]]:
    scan = scan_repo(root)
    outputs = {
        "AGENTS.md": render_agents_md(scan),
        ".agent-ready/report.md": render_report(scan),
        ".agent-ready/agent-ready.json": json.dumps(asdict(scan), indent=2, ensure_ascii=False),
    }
    if companion:
        outputs.update(
            {
                "CLAUDE.md": render_companion(scan, "Claude Code"),
                "GEMINI.md": render_companion(scan, "Gemini CLI"),
                ".github/copilot-instructions.md": render_companion(scan, "GitHub Copilot"),
                ".cursor/rules/agent-ready.mdc": render_cursor_rule(scan),
            }
        )
    statuses: dict[str, str] = {}
    for relative, content in outputs.items():
        statuses[relative] = write_file(root / relative, content, force=force)
    # Rescan so score accounts for newly created agent files when files were written.
    scan = scan_repo(root)
    write_file(root / ".agent-ready" / "report.md", render_report(scan), force=True)
    write_file(root / ".agent-ready" / "agent-ready.json", json.dumps(asdict(scan), indent=2, ensure_ascii=False), force=True)
    write_scorecard(root, scan=scan)
    write_snapshot_for_repo(root)
    statuses[".agent-ready/report.md"] = "written"
    statuses[".agent-ready/agent-ready.json"] = "written"
    statuses[".agent-ready/scorecard.md"] = "written"
    statuses[".agent-ready/scorecard.json"] = "written"
    statuses[".agent-ready/summary.md"] = "written"
    statuses[".agent-ready/summary.json"] = "written"
    return scan, statuses


def print_statuses(label: str, statuses: dict[str, str], as_json: bool = False, payload: dict[str, Any] | None = None) -> None:
    if as_json:
        data = {"files": statuses}
        if payload:
            data.update(payload)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    print(label)
    for path, status in statuses.items():
        print(f"- {status}: {path}")


def print_scan(scan: RepoScan, as_json: bool) -> None:
    if as_json:
        print(json.dumps(asdict(scan), indent=2, ensure_ascii=False))
        return
    print(f"Repo: {scan.repo_name}")
    print(f"Score: {scan.score}/100")
    print(f"Languages: {language_summary(scan)}")
    print(f"Frameworks: {', '.join(scan.frameworks) if scan.frameworks else 'Not detected'}")
    print(f"Package managers/build tools: {', '.join(scan.package_managers) if scan.package_managers else 'Not detected'}")
    print("")
    print("Commands:")
    print(command_block(scan.commands))
    print("")
    print("Agent files:")
    print(list_or_none(scan.agent_files))
    print("")
    print("Findings:")
    if scan.findings:
        for finding in scan.findings:
            location = f" {finding.path or ''}"
            if finding.line:
                location += f":{finding.line}"
            print(f"- [{finding.severity}] {finding.kind}: {finding.message}{location}")
    else:
        print("- No findings")


def print_generate(scan: RepoScan, statuses: dict[str, str], as_json: bool) -> None:
    if as_json:
        print(json.dumps({"scan": asdict(scan), "files": statuses}, indent=2, ensure_ascii=False))
        return
    print(f"Repo: {scan.repo_name}")
    print(f"Score: {scan.score}/100")
    print("")
    print("Files:")
    for path, status in statuses.items():
        print(f"- {status}: {path}")
    print("")
    print("Next:")
    print("- Read .agent-ready/report.md")
    print("- Add the badge from the report to README.md if you want a public signal")
    if scan.findings:
        print("")
        print("Findings:")
        for finding in scan.findings:
            location = f" {finding.path or ''}"
            if finding.line:
                location += f":{finding.line}"
            print(f"- [{finding.severity}] {finding.kind}: {finding.message}{location}")


def check_repo(
    root: Path,
    min_score: int | None = None,
    require_agents: bool | None = None,
    config_path: Path | None = None,
    config: dict[str, Any] | None = None,
    baseline_path: Path | str | None = None,
    ratchet: bool | None = None,
) -> dict[str, Any]:
    loaded_config: dict[str, Any]
    resolved_config_path: Path | None
    if config is None:
        loaded_config, resolved_config_path = load_project_config(root, config_path)
    else:
        loaded_config = config
        resolved_config_path = resolve_config_path(root, config_path)
    effective_min_score = configured_min_score(loaded_config, cli_value=min_score)
    effective_require_agents = configured_require_agents(loaded_config) if require_agents is None else require_agents
    effective_ratchet = configured_ratchet(loaded_config, cli_value=ratchet)
    baseline_fingerprints, resolved_baseline_path, baseline_score = load_baseline(root, loaded_config, baseline_path, required=effective_ratchet)
    scan = scan_repo(root)
    active_findings, ignored_findings = split_ignored_findings(scan.findings, loaded_config)
    active_findings, baseline_ignored_findings = split_baseline_findings(active_findings, baseline_fingerprints)
    scan.findings = active_findings
    scan.score, scan.score_reasons = compute_score(scan)
    failures: list[str] = []
    failure_details: list[dict[str, Any]] = []

    def fail(message: str, path: str | None = None, line: int | None = None) -> None:
        failures.append(message)
        failure_details.append({"message": message, "path": path, "line": line})

    if scan.score < effective_min_score:
        fail(f"Score {scan.score}/100 is below required minimum {effective_min_score}/100")
    if effective_ratchet:
        if baseline_score is None:
            raise SystemExit("Ratchet mode requires a baseline with a recorded score. Recreate it with `agent-ready baseline <repo>`.")
        if scan.score < baseline_score:
            fail(f"Score {scan.score}/100 is below baseline score {baseline_score}/100")
    if effective_require_agents and "AGENTS.md" not in scan.agent_files:
        fail("AGENTS.md is missing", path="AGENTS.md")
    for finding in scan.findings:
        if finding.severity in {"high", "critical"}:
            location = ""
            if finding.path:
                location = f" ({finding.path}"
                if finding.line:
                    location += f":{finding.line}"
                location += ")"
            fail(f"{finding.severity} {finding.kind}: {finding.message}{location}", path=finding.path, line=finding.line)
    return {
        "scan": asdict(scan),
        "passed": not failures,
        "failures": failures,
        "failure_details": failure_details,
        "ignored_findings": [asdict(finding) for finding in ignored_findings],
        "baseline_ignored_findings": [asdict(finding) for finding in baseline_ignored_findings],
        "config": {
            "path": str(resolved_config_path) if resolved_config_path else None,
            "min_score": effective_min_score,
            "require_agents": effective_require_agents,
            "baseline": str(resolved_baseline_path) if resolved_baseline_path else None,
            "baseline_score": baseline_score,
            "ratchet": effective_ratchet,
        },
    }


def render_check_report(data: dict[str, Any]) -> str:
    scan = data["scan"]
    status = "passed" if data["passed"] else "failed"
    config = data.get("config") or {}
    config_path = config.get("path") or "Not detected"
    baseline_path = config.get("baseline") or "Not active"
    baseline_score = config.get("baseline_score")
    baseline_score_text = f"{baseline_score}/100" if baseline_score is not None else "Not active"
    ratchet = "enabled" if config.get("ratchet") else "disabled"
    failures = "\n".join(f"- {failure}" for failure in data["failures"]) if data["failures"] else "- No blocking failures"
    findings = []
    for finding in scan.get("findings", []):
        location = finding.get("path") or ""
        if finding.get("line"):
            location += f":{finding['line']}"
        suffix = f" ({location})" if location else ""
        findings.append(f"- [{finding['severity']}] {finding['kind']}: {finding['message']}{suffix}")
    finding_text = "\n".join(findings) if findings else "- No findings"
    ignored_lines = []
    for finding in data.get("ignored_findings", []):
        location = finding.get("path") or ""
        if finding.get("line"):
            location += f":{finding['line']}"
        suffix = f" ({location})" if location else ""
        ignored_lines.append(f"- [{finding['severity']}] {finding['kind']}: {finding['message']}{suffix}")
    ignored_text = "\n".join(ignored_lines) if ignored_lines else "- No ignored findings"
    baseline_lines = []
    for finding in data.get("baseline_ignored_findings", []):
        location = finding.get("path") or ""
        if finding.get("line"):
            location += f":{finding['line']}"
        suffix = f" ({location})" if location else ""
        baseline_lines.append(f"- [{finding['severity']}] {finding['kind']}: {finding['message']}{suffix}")
    baseline_text = "\n".join(baseline_lines) if baseline_lines else "- No baseline findings"
    plan = build_fix_plan(data)
    plan_text = "\n".join(f"- [{item['priority']}] {item['title']}" for item in plan["items"][:8])
    return f"""# Agent Ready Check

- Status: `{status}`
- Repository: `{scan['repo_name']}`
- Score: `{scan['score']}/100`
- Config: `{config_path}`
- Baseline: `{baseline_path}`
- Baseline score: `{baseline_score_text}`
- Ratchet: `{ratchet}`

## Failures

{failures}

## Findings

{finding_text}

## Ignored Findings

{ignored_text}

## Baseline Findings

{baseline_text}

## Fix Plan

{plan_text}
"""


def write_check_report(data: dict[str, Any]) -> dict[str, str]:
    root = Path(data["scan"]["root"])
    return {
        ".agent-ready/check.md": write_file(root / ".agent-ready" / "check.md", render_check_report(data), force=True),
        ".agent-ready/check.json": write_file(root / ".agent-ready" / "check.json", json.dumps(data, indent=2, ensure_ascii=False), force=True),
    }


def build_snapshot(data: dict[str, Any], diff: dict[str, Any] | None = None) -> dict[str, Any]:
    scan = data["scan"]
    scorecard = build_scorecard(repo_scan_from_dict(scan))
    plan = build_fix_plan(data)
    gaps = [
        item
        for item in scorecard["items"]
        if item["status"] in {"missing", "partial"}
    ]
    top_plan = [
        item
        for item in plan["items"]
        if item["priority"] != "OK"
    ][:5]
    diff_summary = None
    if diff:
        diff_summary = {
            "score_delta": diff.get("score_delta"),
            "new_findings": len(diff.get("new_findings", [])),
            "resolved_findings": len(diff.get("resolved_findings", [])),
            "unchanged_findings": len(diff.get("unchanged_findings", [])),
            "baseline_path": diff.get("baseline_path"),
        }
    return {
        "version": 1,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "root": scan["root"],
        "repo_name": scan["repo_name"],
        "passed": bool(data["passed"]),
        "score": scan["score"],
        "badge": scorecard["badge"],
        "failures": data.get("failures", []),
        "finding_count": len(scan.get("findings", [])),
        "scorecard_gaps": gaps[:8],
        "top_plan": top_plan,
        "diff": diff_summary,
        "commands": {
            "generate": "agent-ready . --all --badge",
            "validate": "agent-ready validate . --dry-run",
            "check": "agent-ready check . --min-score 80 --write-report --write-summary --write-comment --write-scorecard --write-plan",
            "baseline_diff": "agent-ready diff .",
        },
        "paths": {
            "report": ".agent-ready/report.md",
            "scorecard": ".agent-ready/scorecard.md",
            "plan": ".agent-ready/plan.md",
            "diff": ".agent-ready/diff.md" if diff else "",
            "check": ".agent-ready/check.md",
        },
    }


def render_snapshot(snapshot: dict[str, Any]) -> str:
    status = "passed" if snapshot["passed"] else "failed"
    failures = "\n".join(f"- {failure}" for failure in snapshot["failures"]) if snapshot["failures"] else "- No blocking failures"
    if snapshot["scorecard_gaps"]:
        gap_lines = "\n".join(
            f"- [{item['status']}] {item['check']}: {item['points']}/{item['max_points']} - {item['fix']}"
            for item in snapshot["scorecard_gaps"]
        )
    else:
        gap_lines = "- No scorecard gaps"
    if snapshot["top_plan"]:
        plan_lines = "\n".join(
            f"- [{item['priority']}] {item['title']}"
            for item in snapshot["top_plan"]
        )
    else:
        plan_lines = "- No priority fixes"
    diff = snapshot.get("diff")
    if diff:
        delta = diff.get("score_delta")
        delta_text = "Not available" if delta is None else f"+{delta}" if int(delta) > 0 else str(delta)
        diff_lines = "\n".join(
            [
                f"- Score delta: `{delta_text}`",
                f"- New findings: `{diff['new_findings']}`",
                f"- Resolved findings: `{diff['resolved_findings']}`",
                f"- Still present: `{diff['unchanged_findings']}`",
            ]
        )
    else:
        diff_lines = "- Baseline diff not active"
    command_lines = "\n".join(f"- {name}: `{command}`" for name, command in snapshot["commands"].items())
    path_lines = "\n".join(f"- {name}: `{path}`" for name, path in snapshot["paths"].items() if path)
    return f"""# Agent Ready Summary

- Repository: `{snapshot['repo_name']}`
- Status: `{status}`
- Score: `{snapshot['score']}/100`
- Findings: `{snapshot['finding_count']}`

{snapshot['badge']}

## Failures

{failures}

## Scorecard Gaps

{gap_lines}

## Top Fixes

{plan_lines}

## Baseline Diff

{diff_lines}

## Useful Commands

{command_lines}

## Related Files

{path_lines}
"""


def maybe_build_snapshot_diff(root: Path, config_path: Path | None, baseline_path: Path | str | None) -> dict[str, Any] | None:
    config, _config_path = load_project_config(root, config_path)
    resolved = resolve_baseline_path(root, config, baseline_path)
    if not resolved or not resolved.exists():
        return None
    return build_baseline_diff(root, config_path=config_path, baseline_path=baseline_path or resolved)


def write_snapshot(data: dict[str, Any], diff: dict[str, Any] | None = None) -> dict[str, str]:
    root = Path(data["scan"]["root"])
    snapshot = build_snapshot(data, diff=diff)
    return {
        ".agent-ready/summary.md": write_file(root / ".agent-ready" / "summary.md", render_snapshot(snapshot), force=True),
        ".agent-ready/summary.json": write_file(root / ".agent-ready" / "summary.json", json.dumps(snapshot, indent=2, ensure_ascii=False), force=True),
    }


def write_snapshot_for_repo(
    root: Path,
    min_score: int | None = None,
    require_agents: bool | None = None,
    config_path: Path | None = None,
    baseline_path: Path | str | None = None,
    ratchet: bool | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    data = check_repo(
        root,
        min_score=min_score,
        require_agents=require_agents,
        config_path=config_path,
        baseline_path=baseline_path,
        ratchet=ratchet,
    )
    diff = maybe_build_snapshot_diff(Path(data["scan"]["root"]), config_path, baseline_path)
    return build_snapshot(data, diff=diff), write_snapshot(data, diff=diff)


def write_check_sarif(data: dict[str, Any]) -> dict[str, str]:
    root = Path(data["scan"]["root"])
    return {
        ".agent-ready/check.sarif": write_file(root / ".agent-ready" / "check.sarif", render_check_sarif(data), force=True),
    }


def append_github_step_summary(data: dict[str, Any]) -> str | None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return None
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(render_check_report(data))
        handle.write("\n")
    return str(path)


def print_check(data: dict[str, Any], output_format: str = "text") -> None:
    if output_format == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if output_format == "sarif":
        print(render_check_sarif(data))
        return
    if output_format == "github":
        if data["passed"]:
            scan = data["scan"]
            print(f"Agent Ready check passed: {scan['score']}/100")
            return
        for detail in data.get("failure_details", []):
            print(github_error_annotation(detail))
        return
    scan = data["scan"]
    status = "passed" if data["passed"] else "failed"
    print(f"Agent Ready check: {status}")
    print(f"Repo: {scan['repo_name']}")
    print(f"Score: {scan['score']}/100")
    if data["failures"]:
        print("")
        print("Failures:")
        for failure in data["failures"]:
            print(f"- {failure}")
        print("")
        print("Next:")
        if any("AGENTS.md is missing" in failure for failure in data["failures"]):
            print("- Run `agent-ready . --all --badge` to generate agent instructions and a score report.")
        if any("below required minimum" in failure for failure in data["failures"]):
            print("- Read `.agent-ready/report.md` or run `agent-ready . --all --badge` to create one.")
        if any(("high " in failure or "critical " in failure) for failure in data["failures"]):
            print("- Inspect the reported file and line, then remove or rewrite the risky instruction/value.")
    else:
        print("")
        print("No blocking findings")


def doctor_repo(root: Path) -> dict[str, Any]:
    scan = scan_repo(root)
    repo = Path(scan.root)
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, message: str) -> None:
        checks.append({"name": name, "status": status, "message": message})

    add(
        "python",
        "ok" if sys.version_info >= (3, 10) else "fail",
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )
    add("repository path", "ok", str(repo))
    git = shutil.which("git")
    if git:
        git_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        add("git", "ok" if git_check.returncode == 0 else "warn", "Git repository detected" if git_check.returncode == 0 else "Git installed, but this path is not a Git worktree")
    else:
        add("git", "warn", "Git executable not found")
    readme = repo / "README.md"
    if readme.exists():
        add("README.md", "ok" if os.access(readme, os.W_OK) else "warn", "README.md exists and is writable" if os.access(readme, os.W_OK) else "README.md exists but may not be writable")
    else:
        add("README.md", "warn", "README.md not found; badge insertion will create a basic README")
    add(
        "package manager",
        "ok" if scan.package_managers else "warn",
        ", ".join(scan.package_managers) if scan.package_managers else "No package manager or build tool detected",
    )
    command_count = sum(len(commands) for commands in scan.commands.values())
    add("commands", "ok" if command_count else "warn", f"{command_count} validation/setup commands detected" if command_count else "No run/test/build/lint/typecheck commands detected")
    add("agent files", "ok" if scan.agent_files else "warn", ", ".join(scan.agent_files) if scan.agent_files else "No agent instruction files detected yet")
    high_findings = [finding for finding in scan.findings if finding.severity in {"high", "critical"}]
    add("high-risk findings", "ok" if not high_findings else "fail", "No high/critical findings" if not high_findings else f"{len(high_findings)} high/critical findings")
    return {"scan": asdict(scan), "checks": checks, "passed": not any(check["status"] == "fail" for check in checks)}


def print_doctor(data: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    status = "passed" if data["passed"] else "failed"
    scan = data["scan"]
    print(f"Agent Ready doctor: {status}")
    print(f"Repo: {scan['repo_name']}")
    print("")
    for check in data["checks"]:
        print(f"- [{check['status']}] {check['name']}: {check['message']}")
    warnings = [check for check in data["checks"] if check["status"] == "warn"]
    if warnings:
        print("")
        print("Next:")
        print("- Run `agent-ready . --all --badge` after warnings are resolved or accepted.")
        print("- Use `agent-ready validate . --dry-run` before executing project commands.")


def normalize_argv(argv: list[str] | None) -> list[str] | None:
    if argv is None:
        argv = sys_argv()
    if not argv:
        if Path.cwd().resolve() == SKILL_ROOT:
            return ["scan", "."]
        return ["ready", "."]
    if argv[0] in {"-h", "--help", "--version"}:
        return argv
    commands = {"ready", "scan", "lint", "check", "scorecard", "snapshot", "plan", "diff", "doctor", "generate", "validate", "demo", "badge", "mcp", "skill", "ci", "pr", "config", "baseline"}
    first = argv[0]
    if first not in commands:
        return ["ready", *argv]
    return argv


def sys_argv() -> list[str]:
    # Keep sys imported only where it is needed so the script stays easy to audit.
    import sys

    return sys.argv[1:]


def main(argv: list[str] | None = None) -> int:
    argv = normalize_argv(argv)
    parser = argparse.ArgumentParser(
        description="Make a repository ready for AI coding agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  agent-ready . --all --badge
  agent-ready scan .
  agent-ready check . --min-score 80
  agent-ready scorecard .
  agent-ready snapshot .
  agent-ready plan .
  agent-ready diff . --baseline
  agent-ready doctor .
  agent-ready validate . --dry-run
  agent-ready config .
  agent-ready baseline .
  agent-ready pr .
""",
    )
    parser.add_argument("--version", action="version", version=f"agent-ready {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    ready_parser = subparsers.add_parser("ready", help="Scan, generate files, and print the readiness report.")
    ready_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    ready_parser.add_argument("--force", action="store_true", help="Overwrite existing generated files.")
    ready_parser.add_argument("--minimal", action="store_true", help="Generate only AGENTS.md and .agent-ready core reports.")
    ready_parser.add_argument("--demo", action="store_true", help="Generate .agent-ready/demo.md.")
    ready_parser.add_argument("--badge", action="store_true", help="Insert or update the Agent Ready badge in README.md.")
    ready_parser.add_argument("--mcp", action="store_true", help="Generate MCP recommendations.")
    ready_parser.add_argument("--skill", action="store_true", help="Generate a project-specific Codex skill.")
    ready_parser.add_argument("--ci", action="store_true", help="Generate a GitHub Actions workflow.")
    ready_parser.add_argument("--all", action="store_true", help="Generate all advanced artifacts.")
    ready_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    scan_parser = subparsers.add_parser("scan", help="Scan a repository and print detected facts.")
    scan_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    scan_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    lint_parser = subparsers.add_parser("lint", help="Audit existing agent instruction files.")
    lint_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    lint_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    check_parser = subparsers.add_parser("check", help="CI-friendly read-only readiness check.")
    check_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    check_parser.add_argument("--min-score", type=int, default=None, help="Minimum required Agent Ready score.")
    check_parser.add_argument("--no-require-agents", action="store_true", help="Do not fail when AGENTS.md is missing.")
    check_parser.add_argument("--config", type=Path, default=None, help="Path to an Agent Ready JSON config file.")
    check_parser.add_argument("--baseline", nargs="?", const=Path(".agent-ready/baseline.json"), default=None, type=Path, help="Ignore findings already recorded in a baseline file.")
    check_parser.add_argument("--ratchet", action="store_true", help="Fail when the current score drops below the baseline score.")
    check_parser.add_argument("--format", choices=["text", "json", "github", "sarif"], default="text", help="Output format for CI logs.")
    check_parser.add_argument("--write-report", action="store_true", help="Write .agent-ready/check.md and check.json.")
    check_parser.add_argument("--write-sarif", action="store_true", help="Write .agent-ready/check.sarif for GitHub code scanning upload.")
    check_parser.add_argument("--write-scorecard", action="store_true", help="Write .agent-ready/scorecard.md and scorecard.json.")
    check_parser.add_argument("--write-summary", action="store_true", help="Write .agent-ready/summary.md and summary.json with score, gaps, fixes, and optional baseline diff.")
    check_parser.add_argument("--write-comment", action="store_true", help="Write .agent-ready/pr-comment.md and pr-comment.json for PR comment bots.")
    check_parser.add_argument("--write-plan", action="store_true", help="Write .agent-ready/plan.md and plan.json with prioritized fixes.")
    check_parser.add_argument("--write-diff", action="store_true", help="Write .agent-ready/diff.md and diff.json when a baseline is available.")
    check_parser.add_argument("--github-summary", action="store_true", help="Append the check report to GITHUB_STEP_SUMMARY when available.")
    check_parser.add_argument("--github-output", action="store_true", help="Write passed, score, report-path, summary-path, comment-path, sarif-path, plan-path, and diff-path to GITHUB_OUTPUT when available.")
    check_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    scorecard_parser = subparsers.add_parser("scorecard", help="Write an explainable score breakdown.")
    scorecard_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    scorecard_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    snapshot_parser = subparsers.add_parser("snapshot", help="Write a one-page Agent Ready summary.")
    snapshot_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    snapshot_parser.add_argument("--min-score", type=int, default=None, help="Minimum required Agent Ready score for the summary status.")
    snapshot_parser.add_argument("--no-require-agents", action="store_true", help="Do not treat missing AGENTS.md as a blocking summary failure.")
    snapshot_parser.add_argument("--config", type=Path, default=None, help="Path to an Agent Ready JSON config file.")
    snapshot_parser.add_argument("--baseline", nargs="?", const=Path(".agent-ready/baseline.json"), default=None, type=Path, help="Include baseline diff summary when this baseline file exists.")
    snapshot_parser.add_argument("--ratchet", action="store_true", help="Account for score regression against the baseline score.")
    snapshot_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    plan_parser = subparsers.add_parser("plan", help="Write an actionable prioritized fix plan.")
    plan_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    plan_parser.add_argument("--min-score", type=int, default=None, help="Target Agent Ready score for the plan.")
    plan_parser.add_argument("--no-require-agents", action="store_true", help="Do not include missing AGENTS.md as a blocking check failure.")
    plan_parser.add_argument("--config", type=Path, default=None, help="Path to an Agent Ready JSON config file.")
    plan_parser.add_argument("--baseline", nargs="?", const=Path(".agent-ready/baseline.json"), default=None, type=Path, help="Account for findings already recorded in a baseline file.")
    plan_parser.add_argument("--ratchet", action="store_true", help="Account for score regression against the baseline score.")
    plan_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    diff_parser = subparsers.add_parser("diff", help="Compare current findings against a baseline file.")
    diff_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    diff_parser.add_argument("--config", type=Path, default=None, help="Path to an Agent Ready JSON config file.")
    diff_parser.add_argument("--baseline", nargs="?", const=Path(".agent-ready/baseline.json"), default=Path(".agent-ready/baseline.json"), type=Path, help="Baseline file to compare against.")
    diff_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    doctor_parser = subparsers.add_parser("doctor", help="Diagnose local environment and repo readiness inputs.")
    doctor_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    doctor_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    gen_parser = subparsers.add_parser("generate", help="Generate agent instruction files and report.")
    gen_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    gen_parser.add_argument("--force", action="store_true", help="Overwrite existing generated files.")
    gen_parser.add_argument("--minimal", action="store_true", help="Generate only AGENTS.md and .agent-ready core reports.")
    gen_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    validate_parser = subparsers.add_parser("validate", help="Run detected validation commands and write a validation report.")
    validate_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    validate_parser.add_argument("--timeout", type=int, default=120)
    validate_parser.add_argument("--commands", nargs="*", choices=["test", "build", "lint", "typecheck"], default=None)
    validate_parser.add_argument("--dry-run", action="store_true", help="Print and write the validation plan without executing commands.")
    validate_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")

    demo_parser = subparsers.add_parser("demo", help="Generate a before/after demo markdown page.")
    demo_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    demo_parser.add_argument("--force", action="store_true")
    demo_parser.add_argument("--json", action="store_true")

    badge_parser = subparsers.add_parser("badge", help="Insert or update the Agent Ready badge in README.md.")
    badge_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    badge_parser.add_argument("--force", action="store_true")
    badge_parser.add_argument("--json", action="store_true")

    mcp_parser = subparsers.add_parser("mcp", help="Generate MCP recommendations.")
    mcp_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    mcp_parser.add_argument("--force", action="store_true")
    mcp_parser.add_argument("--json", action="store_true")

    skill_parser = subparsers.add_parser("skill", help="Generate a project-specific Codex skill.")
    skill_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    skill_parser.add_argument("--force", action="store_true")
    skill_parser.add_argument("--json", action="store_true")

    ci_parser = subparsers.add_parser("ci", help="Generate a GitHub Actions workflow for agent readiness.")
    ci_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    ci_parser.add_argument("--force", action="store_true")
    ci_parser.add_argument("--json", action="store_true")

    config_parser = subparsers.add_parser("config", help="Write a starter agent-ready.config.json file.")
    config_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    config_parser.add_argument("--force", action="store_true")
    config_parser.add_argument("--json", action="store_true")

    baseline_parser = subparsers.add_parser("baseline", help="Write a baseline of current findings for gradual CI adoption.")
    baseline_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    baseline_parser.add_argument("--path", type=Path, default=Path(".agent-ready/baseline.json"), help="Baseline file to write.")
    baseline_parser.add_argument("--force", action="store_true")
    baseline_parser.add_argument("--json", action="store_true")

    pr_parser = subparsers.add_parser("pr", help="Generate agent-ready files plus PR body and patch package.")
    pr_parser.add_argument("repo", nargs="?", type=Path, default=Path("."))
    pr_parser.add_argument("--force", action="store_true")
    pr_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command in {"scan", "lint"}:
        scan = scan_repo(args.repo)
        print_scan(scan, as_json=args.json)
        return 1 if args.command == "lint" and scan.findings else 0
    if args.command == "check":
        data = check_repo(
            args.repo,
            min_score=args.min_score,
            require_agents=False if args.no_require_agents else None,
            config_path=args.config,
            baseline_path=args.baseline,
            ratchet=True if args.ratchet else None,
        )
        report_statuses = None
        summary_statuses = None
        comment_statuses = None
        sarif_statuses = None
        scorecard_statuses = None
        plan_statuses = None
        diff_statuses = None
        if args.write_report:
            report_statuses = write_check_report(data)
        if args.write_sarif:
            sarif_statuses = write_check_sarif(data)
        if args.write_scorecard:
            scorecard_statuses = write_scorecard(Path(data["scan"]["root"]))
        if args.write_summary:
            summary_diff = maybe_build_snapshot_diff(Path(data["scan"]["root"]), args.config, args.baseline)
            summary_statuses = write_snapshot(data, diff=summary_diff)
        if args.write_plan:
            plan_statuses = write_fix_plan(data)
        if args.write_diff:
            diff_data = build_baseline_diff(args.repo, config_path=args.config, baseline_path=args.baseline)
            diff_statuses = write_baseline_diff(diff_data)
        if args.write_comment:
            comment_statuses = write_pr_comment(data)
        if args.github_summary:
            append_github_step_summary(data)
        if args.github_output:
            write_github_outputs(
                data,
                report_statuses=report_statuses,
                summary_statuses=summary_statuses,
                sarif_statuses=sarif_statuses,
                plan_statuses=plan_statuses,
                diff_statuses=diff_statuses,
                comment_statuses=comment_statuses,
            )
        output_format = "json" if args.json else args.format
        print_check(data, output_format=output_format)
        return 0 if data["passed"] else 1
    if args.command == "scorecard":
        scan = scan_repo(args.repo)
        scorecard = build_scorecard(scan)
        statuses = write_scorecard(Path(scan.root), scan=scan)
        if args.json:
            print(json.dumps({"scorecard": scorecard, "files": statuses}, indent=2, ensure_ascii=False))
        else:
            print(render_scorecard(scorecard))
        return 0
    if args.command == "snapshot":
        snapshot, statuses = write_snapshot_for_repo(
            args.repo,
            min_score=args.min_score,
            require_agents=False if args.no_require_agents else None,
            config_path=args.config,
            baseline_path=args.baseline,
            ratchet=True if args.ratchet else None,
        )
        if args.json:
            print(json.dumps({"snapshot": snapshot, "files": statuses}, indent=2, ensure_ascii=False))
        else:
            print(render_snapshot(snapshot))
        return 0
    if args.command == "plan":
        data = check_repo(
            args.repo,
            min_score=args.min_score,
            require_agents=False if args.no_require_agents else None,
            config_path=args.config,
            baseline_path=args.baseline,
            ratchet=True if args.ratchet else None,
        )
        plan = build_fix_plan(data)
        statuses = write_fix_plan(data, plan=plan)
        if args.json:
            print(json.dumps({"plan": plan, "files": statuses}, indent=2, ensure_ascii=False))
        else:
            print(render_fix_plan(plan))
        return 0
    if args.command == "diff":
        data = build_baseline_diff(args.repo, config_path=args.config, baseline_path=args.baseline)
        statuses = write_baseline_diff(data)
        if args.json:
            print(json.dumps({"diff": data, "files": statuses}, indent=2, ensure_ascii=False))
        else:
            print(render_baseline_diff(data))
        return 1 if data["new_findings"] else 0
    if args.command == "doctor":
        data = doctor_repo(args.repo)
        print_doctor(data, as_json=args.json)
        return 0 if data["passed"] else 1
    if args.command in {"ready", "generate"}:
        scan, statuses = generate_files(args.repo, force=args.force, companion=not args.minimal)
        if args.command == "ready":
            include_all = getattr(args, "all", False)
            extra = generate_extra_files(
                Path(scan.root),
                scan,
                force=args.force,
                include_ci=include_all or args.ci,
                include_mcp=include_all or args.mcp,
                include_skill=include_all or args.skill,
                include_demo=include_all or args.demo,
            )
            statuses.update(extra)
            if include_all or args.badge:
                statuses.update(insert_badge(Path(scan.root), force=args.force))
        print_generate(scan, statuses, as_json=args.json)
        return 0
    if args.command == "validate":
        data = validate_repo(args.repo, timeout=args.timeout, command_names=args.commands, dry_run=args.dry_run)
        root = Path(data["scan"]["root"])
        write_file(root / ".agent-ready" / "validation.md", render_validation_report(data), force=True)
        write_file(root / ".agent-ready" / "validation.json", json.dumps(data, indent=2, ensure_ascii=False), force=True)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(render_validation_report(data))
        return 1 if any(item["status"] not in {"passed", "planned"} for item in data["results"]) else 0
    if args.command in {"demo", "mcp", "skill", "ci"}:
        scan = scan_repo(args.repo)
        statuses = generate_extra_files(
            Path(scan.root),
            scan,
            force=args.force,
            include_ci=args.command == "ci",
            include_mcp=args.command == "mcp",
            include_skill=args.command == "skill",
            include_demo=args.command == "demo",
        )
        print_statuses(f"{args.command} files:", statuses, as_json=args.json, payload={"scan": asdict(scan)})
        return 0
    if args.command == "config":
        statuses = write_config_template(args.repo, force=args.force)
        print_statuses("config files:", statuses, as_json=args.json)
        return 0
    if args.command == "baseline":
        statuses = write_baseline(args.repo, path=args.path, force=args.force)
        print_statuses("baseline files:", statuses, as_json=args.json)
        return 0
    if args.command == "badge":
        statuses = insert_badge(args.repo.resolve(), force=args.force)
        print_statuses("badge files:", statuses, as_json=args.json)
        return 0
    if args.command == "pr":
        statuses = create_pr_patch(args.repo, force=args.force)
        print_statuses("pr package files:", statuses, as_json=args.json)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
