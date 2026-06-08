"""Pull request comment artifact helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .files import write_file
from .payload import repo_scan_from_dict
from .plan import build_fix_plan
from .scorecard import badge_markdown


__all__ = [
    "build_pr_comment",
    "detect_written_artifact_paths",
    "render_pr_comment",
    "write_pr_comment",
]


def detect_written_artifact_paths(root: Path) -> dict[str, str]:
    candidates = [
        ("summary", ".agent-ready/summary.md"),
        ("report", ".agent-ready/check.md"),
        ("scorecard", ".agent-ready/scorecard.md"),
        ("plan", ".agent-ready/plan.md"),
        ("diff", ".agent-ready/diff.md"),
        ("sarif", ".agent-ready/check.sarif"),
    ]
    return {
        name: path
        for name, path in candidates
        if (root / path).exists()
    }


def build_pr_comment(
    data: dict[str, Any],
    plan: dict[str, Any] | None = None,
    artifact_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    scan = data["scan"]
    plan = plan or build_fix_plan(data)
    config = data.get("config") or {}
    severity_counts: dict[str, int] = {}
    for finding in scan.get("findings", []):
        severity = str(finding.get("severity") or "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return {
        "version": 1,
        "generated_at": scan.get("generated_at"),
        "repo_name": scan.get("repo_name"),
        "passed": bool(data.get("passed")),
        "score": scan.get("score"),
        "target_score": config.get("min_score"),
        "badge": badge_markdown(repo_scan_from_dict(scan)),
        "finding_count": len(scan.get("findings", [])),
        "severity_counts": severity_counts,
        "failures": list(data.get("failures", []))[:6],
        "top_fixes": [
            item
            for item in plan.get("items", [])
            if item.get("priority") != "OK"
        ][:6],
        "paths": artifact_paths if artifact_paths is not None else detect_written_artifact_paths(Path(str(scan["root"]))),
        "next_commands": list(plan.get("next_commands", [])),
    }


def render_pr_comment(comment: dict[str, Any]) -> str:
    status = "PASS" if comment["passed"] else "FAIL"
    target_score = comment.get("target_score")
    target_text = "Not set" if target_score is None else f"{target_score}/100"
    failures = "\n".join(f"- {failure}" for failure in comment.get("failures", [])) or "- No blocking failures"
    if comment.get("top_fixes"):
        fix_lines = []
        for item in comment["top_fixes"]:
            location = str(item.get("path") or "")
            if item.get("line"):
                location += f":{item['line']}"
            suffix = f" (`{location}`)" if location else ""
            fix_lines.append(f"- [{item['priority']}] {item['title']}{suffix}")
        fixes = "\n".join(fix_lines)
    else:
        fixes = "- No priority fixes"
    severity_counts = comment.get("severity_counts") or {}
    if severity_counts:
        severities = ", ".join(f"{name}: {count}" for name, count in sorted(severity_counts.items()))
    else:
        severities = "none"
    path_lines = "\n".join(f"- {name}: `{path}`" for name, path in comment["paths"].items()) or "- No linked artifacts written"
    command_lines = "\n".join(f"- `{command}`" for command in comment.get("next_commands", []))
    return f"""# Agent Ready PR Check: {status}

{comment['badge']}

| Metric | Value |
| --- | --- |
| Repository | `{comment['repo_name']}` |
| Score | `{comment['score']}/100` |
| Target | `{target_text}` |
| Active findings | `{comment['finding_count']}` |
| Severity mix | `{severities}` |

## Blocking Failures

{failures}

## Top Fixes

{fixes}

## CI Artifacts

{path_lines}

## Next Commands

{command_lines}
"""


def write_pr_comment(data: dict[str, Any], comment: dict[str, Any] | None = None) -> dict[str, str]:
    root = Path(data["scan"]["root"])
    comment = comment or build_pr_comment(data)
    return {
        ".agent-ready/pr-comment.md": write_file(root / ".agent-ready" / "pr-comment.md", render_pr_comment(comment), force=True),
        ".agent-ready/pr-comment.json": write_file(root / ".agent-ready" / "pr-comment.json", json.dumps(comment, indent=2, ensure_ascii=False), force=True),
    }
