#!/usr/bin/env python3
"""Cross-platform maintainer tasks for Agent Ready."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY_COMPILE_TARGETS = [
    "agent-ready.py",
    "agent_ready/baseline.py",
    "agent_ready/cli.py",
    "agent_ready/comment.py",
    "agent_ready/config.py",
    "agent_ready/files.py",
    "agent_ready/github.py",
    "agent_ready/__main__.py",
    "agent_ready/payload.py",
    "agent_ready/plan.py",
    "agent_ready/scan.py",
    "agent_ready/sarif.py",
    "agent_ready/scorecard.py",
    "agent_ready/validation.py",
    "scripts/agent_ready.py",
    "scripts/test_agent_ready.py",
    "scripts/build_demo_assets.py",
    "scripts/release_check.py",
    "scripts/dev.py",
]


def run(command: list[str]) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=str(ROOT), check=True)


def task_lint() -> None:
    run([sys.executable, "-B", "-m", "py_compile", *PY_COMPILE_TARGETS])


def task_test() -> None:
    run([sys.executable, "-B", "-m", "unittest", "scripts.test_agent_ready"])


def task_demo() -> None:
    run([sys.executable, "-B", "scripts/build_demo_assets.py", "--require-images"])


def task_doctor() -> None:
    run([sys.executable, "-B", "agent-ready.py", "doctor", "examples/demo-repo"])


def task_check() -> None:
    run([sys.executable, "-B", "agent-ready.py", "check", ".", "--min-score", "80"])


def task_run() -> None:
    run([sys.executable, "-B", "agent-ready.py", "--help"])


def task_clean() -> None:
    from scripts.release_check import clean_generated_noise

    clean_generated_noise()
    print("+ cleaned generated noise")


def task_release() -> None:
    run([sys.executable, "-B", "scripts/release_check.py"])


def command_result(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def task_publish_check() -> None:
    problems: list[str] = []
    if not (ROOT / ".git").exists():
        problems.append("Git repository is not initialized.")
    else:
        remote = command_result(["git", "remote", "get-url", "origin"])
        if remote.returncode != 0 or not remote.stdout.strip():
            problems.append("Git remote `origin` is not configured.")
    placeholder_patterns = ["OWNER/agent-ready", "github.com/OWNER/agent-ready", "owner/repo@", "your-org/"]
    placeholder_hits: list[str] = []
    for path in [ROOT / "README.md", ROOT / "action.yml", ROOT / "examples" / "demo-output" / "check.sarif"]:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern in text for pattern in placeholder_patterns):
                placeholder_hits.append(path.relative_to(ROOT).as_posix())
    if placeholder_hits:
        problems.append("Publish placeholders remain in: " + ", ".join(placeholder_hits))
    if not shutil.which("gh"):
        problems.append("GitHub CLI `gh` is not installed.")
    else:
        auth = command_result(["gh", "auth", "status"])
        if auth.returncode != 0:
            problems.append("GitHub CLI `gh` is not authenticated.")
    if problems:
        print("Publish readiness: failed")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("Publish readiness: passed")


def task_all() -> None:
    for task in [task_lint, task_test, task_demo, task_doctor, task_check]:
        task()


TASKS: dict[str, Callable[[], None]] = {
    "all": task_all,
    "build": task_release,
    "check": task_check,
    "clean": task_clean,
    "demo": task_demo,
    "doctor": task_doctor,
    "lint": task_lint,
    "publish-check": task_publish_check,
    "release": task_release,
    "run": task_run,
    "test": task_test,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Agent Ready maintainer tasks.")
    parser.add_argument("tasks", nargs="+", choices=sorted(TASKS), help="Task name(s) to run in order.")
    args = parser.parse_args(argv)
    for task_name in args.tasks:
        TASKS[task_name]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
