"""SARIF rendering for Agent Ready checks."""

from __future__ import annotations

import json
import re
from typing import Any

from . import __version__


def sarif_level(severity: str) -> str:
    if severity in {"critical", "high"}:
        return "error"
    if severity == "medium":
        return "warning"
    return "note"


def sarif_security_severity(severity: str) -> str:
    return {
        "critical": "9.0",
        "high": "7.0",
        "medium": "4.0",
        "low": "1.0",
    }.get(severity, "1.0")


def sarif_rule_id(kind: str) -> str:
    safe_kind = re.sub(r"[^a-z0-9-]+", "-", kind.lower()).strip("-") or "finding"
    return f"agent-ready/{safe_kind}"


def render_check_sarif(data: dict[str, Any]) -> str:
    scan = data["scan"]
    rule_map: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    def add_result(kind: str, severity: str, message: str, path: str | None, line: int | None = None) -> None:
        if not path:
            return
        rule_id = sarif_rule_id(kind)
        if rule_id not in rule_map:
            rule_map[rule_id] = {
                "id": rule_id,
                "name": kind,
                "shortDescription": {"text": kind.replace("-", " ").title()},
                "fullDescription": {"text": "Agent Ready repository-readiness finding."},
                "properties": {"security-severity": sarif_security_severity(severity)},
            }
        region = {"startLine": int(line or 1)}
        results.append(
            {
                "ruleId": rule_id,
                "level": sarif_level(severity),
                "message": {"text": message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": path.replace("\\", "/")},
                            "region": region,
                        }
                    }
                ],
            }
        )

    for finding in scan.get("findings", []):
        add_result(
            str(finding.get("kind", "finding")),
            str(finding.get("severity", "low")),
            str(finding.get("message", "Agent Ready finding")),
            finding.get("path"),
            finding.get("line"),
        )
    for detail in data.get("failure_details", []):
        if detail.get("path") == "AGENTS.md" and "AGENTS.md is missing" in str(detail.get("message", "")):
            add_result("missing-agents", "high", str(detail["message"]), "AGENTS.md", 1)

    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Agent Ready",
                        "version": __version__,
                        "rules": list(rule_map.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
