"""Shared file-writing helpers."""

from __future__ import annotations

from pathlib import Path


__all__ = ["write_file"]


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return "skipped"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    return "written"
