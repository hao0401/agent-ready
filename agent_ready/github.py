"""GitHub Actions output and annotation helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


__all__ = [
    "escape_github_command_data",
    "escape_github_command_property",
    "github_error_annotation",
    "write_github_outputs",
]


def written_artifact_path(statuses: dict[str, str] | None, path: str) -> str:
    if statuses and path in statuses:
        return path
    return ""


def write_github_outputs(
    data: dict[str, Any],
    report_statuses: dict[str, str] | None = None,
    sarif_statuses: dict[str, str] | None = None,
    plan_statuses: dict[str, str] | None = None,
    diff_statuses: dict[str, str] | None = None,
    summary_statuses: dict[str, str] | None = None,
    comment_statuses: dict[str, str] | None = None,
) -> str | None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return None
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    config = data.get("config") or {}
    values = {
        "passed": "true" if data["passed"] else "false",
        "score": str(data["scan"]["score"]),
        "report-path": written_artifact_path(report_statuses, ".agent-ready/check.md"),
        "summary-path": written_artifact_path(summary_statuses, ".agent-ready/summary.md"),
        "comment-path": written_artifact_path(comment_statuses, ".agent-ready/pr-comment.md"),
        "sarif-path": written_artifact_path(sarif_statuses, ".agent-ready/check.sarif"),
        "plan-path": written_artifact_path(plan_statuses, ".agent-ready/plan.md"),
        "diff-path": written_artifact_path(diff_statuses, ".agent-ready/diff.md"),
        "config-path": str(config.get("path") or ""),
        "baseline-path": str(config.get("baseline") or ""),
        "baseline-score": "" if config.get("baseline_score") is None else str(config.get("baseline_score")),
        "ratchet": "true" if config.get("ratchet") else "false",
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")
    return str(path)


def escape_github_command_data(value: Any) -> str:
    text = str(value)
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_github_command_property(value: Any) -> str:
    return escape_github_command_data(value).replace(":", "%3A").replace(",", "%2C")


def github_error_annotation(detail: dict[str, Any]) -> str:
    properties = []
    if detail.get("path"):
        properties.append(f"file={escape_github_command_property(detail['path'])}")
    if detail.get("line"):
        properties.append(f"line={int(detail['line'])}")
    property_text = f" {','.join(properties)}" if properties else ""
    return f"::error{property_text}::{escape_github_command_data(detail['message'])}"
