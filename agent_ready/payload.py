"""Payload conversion helpers shared by report builders."""

from __future__ import annotations

from typing import Any

from .scan import Finding, RepoScan


__all__ = ["repo_scan_from_dict"]


def repo_scan_from_dict(data: dict[str, Any]) -> RepoScan:
    findings = [
        Finding(
            severity=str(finding.get("severity", "")),
            kind=str(finding.get("kind", "")),
            message=str(finding.get("message", "")),
            path=finding.get("path"),
            line=finding.get("line"),
        )
        for finding in data.get("findings", [])
        if isinstance(finding, dict)
    ]
    return RepoScan(
        root=str(data["root"]),
        repo_name=str(data["repo_name"]),
        generated_at=str(data["generated_at"]),
        languages=list(data.get("languages", [])),
        frameworks=list(data.get("frameworks", [])),
        package_managers=list(data.get("package_managers", [])),
        commands=dict(data.get("commands", {})),
        entry_points=list(data.get("entry_points", [])),
        config_files=list(data.get("config_files", [])),
        important_dirs=list(data.get("important_dirs", [])),
        generated_dirs=list(data.get("generated_dirs", [])),
        agent_files=list(data.get("agent_files", [])),
        monorepo_hints=list(data.get("monorepo_hints", [])),
        packages=list(data.get("packages", [])),
        findings=findings,
        score=int(data.get("score", 0)),
        score_reasons=list(data.get("score_reasons", [])),
    )
