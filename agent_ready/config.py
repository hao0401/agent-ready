"""Agent Ready project config loading and finding ignore rules."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any

from .scan import CONFIG_CANDIDATES, Finding


__all__ = [
    "config_check_value",
    "configured_min_score",
    "configured_ratchet",
    "configured_require_agents",
    "finding_matches_ignore_rule",
    "load_project_config",
    "resolve_config_path",
    "split_ignored_findings",
]


def resolve_config_path(root: Path, config_path: Path | None = None) -> Path | None:
    root = root.resolve()
    if config_path:
        path = config_path if config_path.is_absolute() else root / config_path
        return path.resolve()
    for candidate in CONFIG_CANDIDATES:
        path = root / candidate
        if path.exists():
            return path.resolve()
    return None


def load_project_config(root: Path, config_path: Path | None = None) -> tuple[dict[str, Any], Path | None]:
    path = resolve_config_path(root, config_path)
    if not path:
        return {}, None
    if not path.exists():
        raise SystemExit(f"Config file does not exist: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Config file must contain a JSON object: {path}")
    check = data.get("check", {})
    if check is not None and not isinstance(check, dict):
        raise SystemExit("Config field `check` must be an object")
    ignore_findings = data.get("ignore_findings", [])
    if ignore_findings is not None and not isinstance(ignore_findings, list):
        raise SystemExit("Config field `ignore_findings` must be a list")
    return data, path


def config_check_value(config: dict[str, Any], key: str, default: Any) -> Any:
    check = config.get("check", {})
    if isinstance(check, dict) and key in check:
        return check[key]
    return config.get(key, default)


def configured_min_score(config: dict[str, Any], cli_value: int | None = None, default: int = 80) -> int:
    value = cli_value if cli_value is not None else config_check_value(config, "min_score", default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 100:
        raise SystemExit("Config field `check.min_score` must be an integer from 0 to 100")
    return value


def configured_require_agents(config: dict[str, Any], cli_no_require_agents: bool = False, default: bool = True) -> bool:
    if cli_no_require_agents:
        return False
    value = config_check_value(config, "require_agents", default)
    if not isinstance(value, bool):
        raise SystemExit("Config field `check.require_agents` must be true or false")
    return value


def configured_ratchet(config: dict[str, Any], cli_value: bool | None = None, default: bool = False) -> bool:
    if cli_value is not None:
        return cli_value
    value = config_check_value(config, "ratchet", default)
    if not isinstance(value, bool):
        raise SystemExit("Config field `check.ratchet` must be true or false")
    return value


def finding_matches_ignore_rule(finding: Finding, rule: Any) -> bool:
    if isinstance(rule, str):
        return finding.kind == rule or finding.severity == rule
    if not isinstance(rule, dict):
        return False
    if "kind" in rule and finding.kind != str(rule["kind"]):
        return False
    if "severity" in rule and finding.severity != str(rule["severity"]):
        return False
    if "path" in rule:
        finding_path = finding.path or ""
        if not fnmatch.fnmatch(finding_path, str(rule["path"])):
            return False
    if "line" in rule:
        try:
            rule_line = int(rule["line"])
        except (TypeError, ValueError):
            return False
        if finding.line != rule_line:
            return False
    if "message_contains" in rule and str(rule["message_contains"]) not in finding.message:
        return False
    return True


def split_ignored_findings(findings: list[Finding], config: dict[str, Any]) -> tuple[list[Finding], list[Finding]]:
    rules = config.get("ignore_findings", []) or []
    active: list[Finding] = []
    ignored: list[Finding] = []
    for finding in findings:
        if any(finding_matches_ignore_rule(finding, rule) for rule in rules):
            ignored.append(finding)
        else:
            active.append(finding)
    return active, ignored
