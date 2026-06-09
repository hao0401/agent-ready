"""Fix-plan building and rendering helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .files import write_file


__all__ = [
    "add_plan_item",
    "build_fix_plan",
    "finding_plan_action",
    "first_detected_package_manager",
    "render_fix_plan",
    "safe_plan_id",
    "write_fix_plan",
]


def safe_plan_id(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-") or "item"


def first_detected_package_manager(scan: dict[str, Any]) -> str:
    managers = scan.get("package_managers", []) or []
    for manager in managers:
        if manager in {"pnpm", "yarn", "npm", "bun"}:
            return str(manager)
    if managers:
        return str(managers[0])
    return "project metadata"


def add_plan_item(
    items: list[dict[str, Any]],
    *,
    priority: str,
    category: str,
    title: str,
    why: str,
    action: str,
    command: str | None = None,
    path: str | None = None,
    line: int | None = None,
    score_impact: int | None = None,
) -> None:
    item: dict[str, Any] = {
        "id": safe_plan_id(f"{category}-{path or title}-{line or ''}"),
        "priority": priority,
        "category": category,
        "title": title,
        "why": why,
        "action": action,
    }
    if command:
        item["command"] = command
    if path:
        item["path"] = path
    if line:
        item["line"] = line
    if score_impact is not None:
        item["score_impact"] = score_impact
    items.append(item)


def finding_plan_action(finding: dict[str, Any], scan: dict[str, Any]) -> tuple[str, str, str, int | None]:
    kind = str(finding.get("kind") or "finding")
    severity = str(finding.get("severity") or "low")
    manager = first_detected_package_manager(scan)
    if kind == "prompt-injection":
        return (
            "P0",
            "security",
            "Rewrite or remove prompt-injection-like text before agents read it.",
            10,
        )
    if kind == "secret":
        return (
            "P0",
            "security",
            "Remove the secret-looking value, rotate it if it was real, and keep only a redacted example.",
            10,
        )
    if kind == "conflict":
        return (
            "P0" if severity in {"high", "critical"} else "P1",
            "instruction-conflict",
            f"Align agent instructions with the detected package manager or build tool: {manager}.",
            10,
        )
    if kind == "length":
        return (
            "P2",
            "instruction-quality",
            "Tighten the agent instruction file so agents can load only the decisions and commands they need.",
            None,
        )
    return (
        "P1" if severity in {"high", "critical"} else "P2",
        "finding",
        "Inspect the finding and update the referenced file so future checks no longer flag it.",
        None,
    )


def build_fix_plan(data: dict[str, Any]) -> dict[str, Any]:
    scan = data["scan"]
    config = data.get("config") or {}
    target_score = int(config.get("min_score") or 80)
    items: list[dict[str, Any]] = []

    require_agents = bool(config.get("require_agents", True))
    if "AGENTS.md" not in (scan.get("agent_files") or []):
        add_plan_item(
            items,
            priority="P0" if require_agents else "P1",
            category="agent-instructions",
            title="Create primary AGENTS.md instructions",
            why="Most coding agents look for repository-level instructions before editing.",
            action="Generate AGENTS.md plus companion instructions from the current repository scan.",
            command="agent-ready . --all --badge",
            path="AGENTS.md",
            score_impact=20,
        )

    for finding in scan.get("findings", []):
        priority, category, action, score_impact = finding_plan_action(finding, scan)
        location = finding.get("path") or "repository"
        if finding.get("line"):
            location = f"{location}:{finding['line']}"
        add_plan_item(
            items,
            priority=priority,
            category=category,
            title=f"Fix {finding.get('kind', 'finding')} finding in {location}",
            why=str(finding.get("message") or "Agent Ready reported a repository-readiness finding."),
            action=action,
            path=finding.get("path"),
            line=finding.get("line"),
            score_impact=score_impact,
        )

    commands = scan.get("commands", {}) or {}
    config_files = set(scan.get("config_files", []) or [])
    manager = first_detected_package_manager(scan)
    if not commands.get("test"):
        action = "Add a deterministic test command to standard project metadata."
        if "package.json" in config_files:
            action = f"Add a package.json test script so Agent Ready can detect `{manager} test`."
        elif any(name in config_files for name in ["pyproject.toml", "requirements.txt", "setup.py", "pytest.ini"]):
            action = "Add pytest configuration or a tests directory so `python -m pytest` is detected."
        add_plan_item(
            items,
            priority="P1",
            category="validation",
            title="Add a detectable test command",
            why="Agents need one trusted command to verify behavior before finishing changes.",
            action=action,
            score_impact=15,
        )
    if not commands.get("build"):
        action = "Add a deterministic build command to standard project metadata."
        if "package.json" in config_files:
            action = f"Add a package.json build script so Agent Ready can detect `{manager} build`."
        add_plan_item(
            items,
            priority="P2",
            category="validation",
            title="Add a detectable build command",
            why="A build command catches integration errors that tests may miss.",
            action=action,
            score_impact=10,
        )
    if not commands.get("run"):
        add_plan_item(
            items,
            priority="P2",
            category="developer-workflow",
            title="Add a detectable local run command",
            why="A run command helps agents reproduce the app locally instead of guessing startup steps.",
            action="Add a conventional start/dev/run script or Makefile target.",
            score_impact=5,
        )
    if not (scan.get("entry_points") or scan.get("important_dirs")):
        add_plan_item(
            items,
            priority="P1",
            category="project-map",
            title="Expose the main project entry points",
            why="Agents need a reliable map before making scoped edits.",
            action="Add conventional entry files or top-level app directories that reflect the real project structure.",
            score_impact=10,
        )
    if not scan.get("config_files"):
        add_plan_item(
            items,
            priority="P2",
            category="project-map",
            title="Add recognizable project config",
            why="Config files let agents identify package managers, frameworks, and validation commands.",
            action="Add standard project metadata such as package.json, pyproject.toml, go.mod, Cargo.toml, or a Makefile.",
            score_impact=10,
        )
    if not scan.get("languages"):
        add_plan_item(
            items,
            priority="P2",
            category="project-map",
            title="Add source files or include the real source tree",
            why="No language signal was detected, so the repo may look empty or generated-only to agents.",
            action="Keep real source files in the repository path being scanned and avoid scanning only generated output.",
            score_impact=10,
        )

    for finding in data.get("baseline_ignored_findings", []):
        add_plan_item(
            items,
            priority="P2",
            category="baseline-debt",
            title=f"Retire baseline finding: {finding.get('kind', 'finding')}",
            why="Baseline mode lets CI adopt gradually, but the finding still exists in the repo.",
            action="Fix the underlying issue, regenerate the baseline, and enable ratchet mode if score regressions should block.",
            path=finding.get("path"),
            line=finding.get("line"),
        )
    for finding in data.get("ignored_findings", []):
        add_plan_item(
            items,
            priority="P2",
            category="ignored-finding",
            title=f"Review ignored finding: {finding.get('kind', 'finding')}",
            why="Config ignores should remain narrow and documented.",
            action="Confirm the ignore rule is still needed, then remove it after the underlying issue is fixed.",
            path=finding.get("path"),
            line=finding.get("line"),
        )

    if not items:
        add_plan_item(
            items,
            priority="OK",
            category="maintenance",
            title="No blocking fixes detected",
            why="The repository meets the active Agent Ready check policy.",
            action="Keep the score stable by running `agent-ready check . --write-report --write-summary --write-comment --write-plan` in CI.",
        )

    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "OK": 3}
    for order, item in enumerate(items):
        item["_order"] = order
    items.sort(key=lambda item: (priority_rank.get(str(item["priority"]), 9), int(item["_order"])))
    for item in items:
        item.pop("_order", None)

    next_commands = [
        "agent-ready . --all --badge",
        "agent-ready validate .",
        "agent-ready check . --min-score 80 --write-report --write-summary --write-comment --write-plan",
    ]
    return {
        "version": 1,
        "generated_at": scan.get("generated_at"),
        "repo_name": scan.get("repo_name"),
        "score": scan.get("score"),
        "target_score": target_score,
        "passed": bool(data.get("passed")),
        "items": items,
        "next_commands": next_commands,
    }


def render_fix_plan(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in plan["items"]:
        lines.append(f"- [{item['priority']}] **{item['title']}**")
        lines.append(f"  - Why: {item['why']}")
        lines.append(f"  - Action: {item['action']}")
        if item.get("command"):
            lines.append(f"  - Command: `{item['command']}`")
        if item.get("path"):
            location = str(item["path"])
            if item.get("line"):
                location += f":{item['line']}"
            lines.append(f"  - Location: `{location}`")
        if item.get("score_impact") is not None:
            lines.append(f"  - Score impact: +{item['score_impact']}")
    command_lines = "\n".join(f"- `{command}`" for command in plan["next_commands"])
    return f"""# Agent Ready Fix Plan

- Repository: `{plan['repo_name']}`
- Score: `{plan['score']}/100`
- Target score: `{plan['target_score']}/100`
- Check passed: `{"true" if plan['passed'] else "false"}`

## Priority Plan

{chr(10).join(lines)}

## Next Commands

{command_lines}
"""


def write_fix_plan(data: dict[str, Any], plan: dict[str, Any] | None = None) -> dict[str, str]:
    root = Path(data["scan"]["root"])
    plan = plan or build_fix_plan(data)
    return {
        ".agent-ready/plan.md": write_file(root / ".agent-ready" / "plan.md", render_fix_plan(plan), force=True),
        ".agent-ready/plan.json": write_file(root / ".agent-ready" / "plan.json", json.dumps(plan, indent=2, ensure_ascii=False), force=True),
    }
