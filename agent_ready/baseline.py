"""Baseline capture and diff helpers."""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import config_check_value, load_project_config, split_ignored_findings
from .files import write_file
from .scan import Finding, RepoScan, rel, scan_repo


__all__ = [
    "build_baseline_diff",
    "finding_fingerprint",
    "finding_location_text",
    "load_baseline",
    "load_baseline_data",
    "normalize_baseline_finding",
    "render_baseline",
    "render_baseline_diff",
    "render_finding_diff_list",
    "resolve_baseline_path",
    "split_baseline_findings",
    "write_baseline",
    "write_baseline_diff",
]


def finding_fingerprint(finding: Finding | dict[str, Any]) -> str:
    if isinstance(finding, Finding):
        severity = finding.severity
        kind = finding.kind
        path = finding.path or ""
        line = finding.line or ""
        message = finding.message
    else:
        severity = str(finding.get("severity", ""))
        kind = str(finding.get("kind", ""))
        path = str(finding.get("path") or "")
        line = finding.get("line") or ""
        message = str(finding.get("message", ""))
    return "|".join([str(severity), str(kind), path, str(line), message])


def render_baseline(scan: RepoScan) -> str:
    findings = []
    for finding in scan.findings:
        item = asdict(finding)
        item["fingerprint"] = finding_fingerprint(finding)
        findings.append(item)
    payload = {
        "version": 1,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "root": scan.root,
        "repo_name": scan.repo_name,
        "score": scan.score,
        "score_reasons": scan.score_reasons,
        "findings": findings,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_baseline(root: Path, path: Path | None = None, force: bool = False) -> dict[str, str]:
    root = root.resolve()
    scan = scan_repo(root)
    target = path or Path(".agent-ready/baseline.json")
    target_path = target if target.is_absolute() else root / target
    relative = rel(target_path, root) if target_path.resolve().is_relative_to(root) else str(target_path)
    return {relative: write_file(target_path, render_baseline(scan), force=force)}


def resolve_baseline_path(root: Path, config: dict[str, Any], baseline_path: Path | str | None = None) -> Path | None:
    root = root.resolve()
    candidate = baseline_path or config_check_value(config, "baseline", None)
    if not candidate:
        return None
    path = candidate if isinstance(candidate, Path) else Path(str(candidate))
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def load_baseline(root: Path, config: dict[str, Any], baseline_path: Path | str | None = None, required: bool = False) -> tuple[set[str], Path | None, int | None]:
    path = resolve_baseline_path(root, config, baseline_path)
    if not path:
        if required:
            raise SystemExit("Ratchet mode requires a baseline file. Run `agent-ready baseline <repo>` first.")
        return set(), None, None
    if not path.exists():
        if required or baseline_path is not None:
            raise SystemExit(f"Baseline file does not exist: {path}")
        return set(), None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON baseline {path}: {exc}") from exc
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise SystemExit("Baseline field `findings` must be a list")
    score = data.get("score")
    if score is not None and (not isinstance(score, int) or isinstance(score, bool) or score < 0 or score > 100):
        raise SystemExit("Baseline field `score` must be an integer from 0 to 100")
    fingerprints: set[str] = set()
    for finding in findings:
        if isinstance(finding, dict):
            fingerprints.add(str(finding.get("fingerprint") or finding_fingerprint(finding)))
    return fingerprints, path, score


def load_baseline_data(root: Path, config: dict[str, Any], baseline_path: Path | str | None = None) -> tuple[dict[str, Any], Path]:
    path = resolve_baseline_path(root, config, baseline_path)
    if not path:
        raise SystemExit("Baseline diff requires a baseline file. Run `agent-ready baseline <repo>` first or pass `--baseline <path>`.")
    if not path.exists():
        raise SystemExit(f"Baseline file does not exist: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON baseline {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Baseline file must contain a JSON object: {path}")
    findings = data.get("findings", [])
    if findings is not None and not isinstance(findings, list):
        raise SystemExit("Baseline field `findings` must be a list")
    score = data.get("score")
    if score is not None and (not isinstance(score, int) or isinstance(score, bool) or score < 0 or score > 100):
        raise SystemExit("Baseline field `score` must be an integer from 0 to 100")
    return data, path


def split_baseline_findings(findings: list[Finding], fingerprints: set[str]) -> tuple[list[Finding], list[Finding]]:
    if not fingerprints:
        return findings, []
    active: list[Finding] = []
    baseline_ignored: list[Finding] = []
    for finding in findings:
        if finding_fingerprint(finding) in fingerprints:
            baseline_ignored.append(finding)
        else:
            active.append(finding)
    return active, baseline_ignored


def normalize_baseline_finding(finding: dict[str, Any]) -> dict[str, Any]:
    item = {
        "severity": str(finding.get("severity", "")),
        "kind": str(finding.get("kind", "")),
        "message": str(finding.get("message", "")),
        "path": finding.get("path"),
        "line": finding.get("line"),
    }
    item["fingerprint"] = str(finding.get("fingerprint") or finding_fingerprint(item))
    return item


def finding_location_text(finding: dict[str, Any]) -> str:
    location = str(finding.get("path") or "")
    if finding.get("line"):
        location += f":{finding['line']}"
    return location or "repository"


def build_baseline_diff(root: Path, config_path: Path | None = None, baseline_path: Path | str | None = None) -> dict[str, Any]:
    config, resolved_config_path = load_project_config(root, config_path)
    baseline, resolved_baseline_path = load_baseline_data(root, config, baseline_path or Path(".agent-ready/baseline.json"))
    scan = scan_repo(root)
    active_findings, ignored_findings = split_ignored_findings(scan.findings, config)
    current_findings = [normalize_baseline_finding(asdict(finding)) for finding in active_findings]
    baseline_findings = [
        normalize_baseline_finding(finding)
        for finding in baseline.get("findings", [])
        if isinstance(finding, dict)
    ]

    current_by_fingerprint = {finding["fingerprint"]: finding for finding in current_findings}
    baseline_by_fingerprint = {finding["fingerprint"]: finding for finding in baseline_findings}
    current_keys = set(current_by_fingerprint)
    baseline_keys = set(baseline_by_fingerprint)
    new_keys = sorted(current_keys - baseline_keys)
    resolved_keys = sorted(baseline_keys - current_keys)
    unchanged_keys = sorted(current_keys & baseline_keys)
    baseline_score = baseline.get("score")
    score_delta = scan.score - baseline_score if isinstance(baseline_score, int) else None

    return {
        "version": 1,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "root": scan.root,
        "repo_name": scan.repo_name,
        "score": scan.score,
        "baseline_score": baseline_score,
        "score_delta": score_delta,
        "baseline_path": str(resolved_baseline_path),
        "config_path": str(resolved_config_path) if resolved_config_path else None,
        "new_findings": [current_by_fingerprint[key] for key in new_keys],
        "resolved_findings": [baseline_by_fingerprint[key] for key in resolved_keys],
        "unchanged_findings": [current_by_fingerprint[key] for key in unchanged_keys],
        "ignored_findings": [asdict(finding) for finding in ignored_findings],
    }


def render_finding_diff_list(findings: list[dict[str, Any]], empty: str) -> str:
    if not findings:
        return f"- {empty}"
    lines: list[str] = []
    for finding in findings:
        lines.append(
            f"- [{finding['severity']}] {finding['kind']}: {finding['message']} "
            f"(`{finding_location_text(finding)}`)"
        )
    return "\n".join(lines)


def render_baseline_diff(data: dict[str, Any]) -> str:
    score_delta = data.get("score_delta")
    if score_delta is None:
        delta_text = "Not available"
    elif score_delta > 0:
        delta_text = f"+{score_delta}"
    else:
        delta_text = str(score_delta)
    return f"""# Agent Ready Baseline Diff

- Repository: `{data['repo_name']}`
- Current score: `{data['score']}/100`
- Baseline score: `{data['baseline_score'] if data.get('baseline_score') is not None else 'Not recorded'}`
- Score delta: `{delta_text}`
- Baseline: `{data['baseline_path']}`

## New Findings

{render_finding_diff_list(data['new_findings'], 'No new findings')}

## Resolved Findings

{render_finding_diff_list(data['resolved_findings'], 'No resolved findings')}

## Still Present

{render_finding_diff_list(data['unchanged_findings'], 'No unchanged findings')}
"""


def write_baseline_diff(data: dict[str, Any]) -> dict[str, str]:
    root = Path(str(data["root"]))
    return {
        ".agent-ready/diff.md": write_file(root / ".agent-ready" / "diff.md", render_baseline_diff(data), force=True),
        ".agent-ready/diff.json": write_file(root / ".agent-ready" / "diff.json", json.dumps(data, indent=2, ensure_ascii=False), force=True),
    }
