"""Score badge and scorecard rendering helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .files import write_file
from .scan import RepoScan, scan_repo, scorecard_items


__all__ = [
    "badge_markdown",
    "build_scorecard",
    "render_scorecard",
    "write_scorecard",
]


def badge_markdown(scan: RepoScan) -> str:
    color = "brightgreen" if scan.score >= 85 else "yellow" if scan.score >= 60 else "orange" if scan.score >= 40 else "red"
    return f"![Agent Ready](https://img.shields.io/badge/Agent%20Ready-{scan.score}%2F100-{color})"


def build_scorecard(scan: RepoScan) -> dict[str, Any]:
    items = scorecard_items(scan)
    raw_score = sum(int(item["points"]) for item in items)
    category_totals: dict[str, dict[str, int]] = {}
    for item in items:
        category = str(item["category"])
        totals = category_totals.setdefault(category, {"points": 0, "max_points": 0})
        totals["points"] += int(item["points"])
        totals["max_points"] += int(item["max_points"])
    return {
        "version": 1,
        "generated_at": scan.generated_at,
        "repo_name": scan.repo_name,
        "score": min(raw_score, 100),
        "raw_score": raw_score,
        "max_score": 100,
        "raw_max_score": sum(int(item["max_points"]) for item in items),
        "score_cap_applied": raw_score > 100,
        "badge": badge_markdown(scan),
        "categories": category_totals,
        "items": items,
    }


def render_scorecard(scorecard: dict[str, Any]) -> str:
    rows = [
        "| Category | Check | Points | Status | Fix |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in scorecard["items"]:
        rows.append(
            f"| {item['category']} | {item['check']} | {item['points']}/{item['max_points']} | "
            f"{item['status']} | {item['fix']} |"
        )
    cap_note = "Yes" if scorecard["score_cap_applied"] else "No"
    return f"""# Agent Ready Scorecard

- Repository: `{scorecard['repo_name']}`
- Score: `{scorecard['score']}/100`
- Raw score: `{scorecard['raw_score']}/{scorecard['raw_max_score']}`
- Score cap applied: `{cap_note}`

## Breakdown

{chr(10).join(rows)}
"""


def write_scorecard(root: Path, scan: RepoScan | None = None) -> dict[str, str]:
    root = root.resolve()
    scan = scan or scan_repo(root)
    scorecard = build_scorecard(scan)
    return {
        ".agent-ready/scorecard.md": write_file(root / ".agent-ready" / "scorecard.md", render_scorecard(scorecard), force=True),
        ".agent-ready/scorecard.json": write_file(root / ".agent-ready" / "scorecard.json", json.dumps(scorecard, indent=2, ensure_ascii=False), force=True),
    }
