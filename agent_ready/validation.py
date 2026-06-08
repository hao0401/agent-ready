"""Validation command planning and execution helpers."""

from __future__ import annotations

import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .scan import scan_repo


__all__ = [
    "render_validation_report",
    "run_command",
    "validate_repo",
]


def run_command(command: str, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        output = (completed.stdout or "")[-4000:]
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": completed.returncode,
            "duration_seconds": round(time.time() - started, 3),
            "output": output,
            "status": "passed" if completed.returncode == 0 else "failed",
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": None,
            "duration_seconds": timeout,
            "output": output[-4000:],
            "status": "timeout",
        }


def validation_result(command: str, cwd: Path, timeout: int, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"command": command, "cwd": str(cwd), "exit_code": None, "duration_seconds": 0, "output": "", "status": "planned"}
    return run_command(command, cwd, timeout)


def validate_repo(root: Path, timeout: int, command_names: list[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    scan = scan_repo(root)
    root = Path(scan.root)
    names = command_names or ["test", "build", "lint", "typecheck"]
    results: list[dict[str, Any]] = []
    for name in names:
        for command in scan.commands.get(name, [])[:1]:
            results.append(validation_result(command, root, timeout, dry_run))
    for package in scan.packages:
        package_root = root / package["path"]
        for name in names:
            for command in package.get("commands", {}).get(name, [])[:1]:
                results.append(validation_result(command, package_root, timeout, dry_run))
    return {"scan": asdict(scan), "results": results}


def render_validation_report(data: dict[str, Any]) -> str:
    results = data["results"]
    if not results:
        body = "- No validation commands detected"
    else:
        body = "\n".join(
            f"- [{item['status']}] `{item['command']}` in `{item['cwd']}` ({item['duration_seconds']}s)"
            for item in results
        )
    return f"""# Agent Ready Validation

{body}
"""
