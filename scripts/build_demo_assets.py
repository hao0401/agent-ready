#!/usr/bin/env python3
"""Build repeatable GitHub demo assets for Agent Ready."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_SOURCE = ROOT / "examples" / "demo-repo"
DEMO_OUTPUT = ROOT / "examples" / "demo-output"
ASSETS = ROOT / "assets"
CLI = ROOT / "agent-ready.py"


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )


def run_expect(command: list[str], cwd: Path, expected_codes: set[int]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode not in expected_codes:
        raise subprocess.CalledProcessError(completed.returncode, command, output=completed.stdout)
    return completed


def copy_selected(repo: Path) -> None:
    if DEMO_OUTPUT.exists():
        shutil.rmtree(DEMO_OUTPUT)
    DEMO_OUTPUT.mkdir(parents=True)
    selected = {
        ".agent-ready/report.md": "report.md",
        ".agent-ready/summary.md": "summary.md",
        ".agent-ready/summary.json": "summary.json",
        ".agent-ready/scorecard.md": "scorecard.md",
        ".agent-ready/scorecard.json": "scorecard.json",
        ".agent-ready/pr-comment.md": "pr-comment.md",
        ".agent-ready/pr-comment.json": "pr-comment.json",
        ".agent-ready/check.md": "check.md",
        ".agent-ready/check.sarif": "check.sarif",
        ".agent-ready/plan.md": "plan.md",
        ".agent-ready/plan.json": "plan.json",
        ".agent-ready/diff.md": "diff.md",
        ".agent-ready/diff.json": "diff.json",
        ".agent-ready/baseline.json": "baseline.json",
        "agent-ready.config.json": "agent-ready.config.json",
        ".agent-ready/demo.md": "before-after.md",
        ".agent-ready/validation.md": "validation-dry-run.md",
        ".agent-ready/mcp-recommendations.md": "mcp-recommendations.md",
        ".agent-ready/pr/PR_BODY.md": "PR_BODY.md",
        ".github/workflows/agent-ready.yml": "agent-ready.yml",
        "AGENTS.md": "AGENTS.md",
    }
    for source, target in selected.items():
        source_path = repo / source
        if source_path.exists():
            text = source_path.read_text(encoding="utf-8")
            text = sanitize_demo_text(text, repo)
            (DEMO_OUTPUT / target).write_text(text, encoding="utf-8", newline="\n")


def sanitize_demo_text(text: str, repo: Path) -> str:
    stable_root = "examples/demo-repo"
    normalized = text.replace(str(repo), stable_root)
    normalized = normalized.replace(str(repo).replace("\\", "/"), stable_root)
    normalized = normalized.replace(str(repo).replace("\\", "\\\\"), stable_root)
    normalized = normalized.replace(str(repo).replace("\\", "//"), stable_root)
    normalized = normalized.replace("\\", "/")
    normalized = re.sub(r"[A-Z]:/+Users/[^`\"\s)]+/agent-ready-demo-[^`\"\s)]+/acme-workbench", stable_root, normalized)
    while f"{stable_root}//" in normalized:
        normalized = normalized.replace(f"{stable_root}//", f"{stable_root}/")
    normalized = normalized.replace("/.agent-ready//", "/.agent-ready/")
    return normalized


def terminal_svg(lines: list[str]) -> str:
    width = 920
    line_height = 24
    top = 66
    height = top + line_height * len(lines) + 34
    rendered = []
    for index, line in enumerate(lines):
        y = top + index * line_height
        fill = "#d1fae5" if line.startswith("+") else "#dbeafe" if line.startswith("$") else "#e5e7eb"
        rendered.append(f'<text x="32" y="{y}" fill="{fill}">{html.escape(line)}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Agent Ready terminal demo">
  <rect width="100%" height="100%" rx="14" fill="#0f172a"/>
  <circle cx="32" cy="30" r="7" fill="#ef4444"/>
  <circle cx="56" cy="30" r="7" fill="#f59e0b"/>
  <circle cx="80" cy="30" r="7" fill="#22c55e"/>
  <text x="116" y="36" fill="#94a3b8" font-family="Consolas, Monaco, monospace" font-size="15">agent-ready demo</text>
  <g font-family="Consolas, Monaco, monospace" font-size="17">
    {chr(10).join(rendered)}
  </g>
</svg>
'''


def write_terminal_png(lines: list[str], path: Path) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return False
    width = 920
    line_height = 24
    top = 66
    height = top + line_height * len(lines) + 34
    image = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("consola.ttf", 17)
        title_font = ImageFont.truetype("consola.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=14, fill="#0f172a")
    draw.ellipse((25, 23, 39, 37), fill="#ef4444")
    draw.ellipse((49, 23, 63, 37), fill="#f59e0b")
    draw.ellipse((73, 23, 87, 37), fill="#22c55e")
    draw.text((116, 22), "agent-ready demo", fill="#94a3b8", font=title_font)
    for index, line in enumerate(lines):
        y = top + index * line_height - 16
        fill = "#d1fae5" if line.startswith("+") else "#dbeafe" if line.startswith("$") else "#e5e7eb"
        draw.text((32, y), line, fill=fill, font=font)
    image.save(path)
    return True


def write_terminal_gif(lines: list[str], path: Path) -> bool:
    try:
        from PIL import Image
    except Exception:
        return False
    with tempfile.TemporaryDirectory(prefix="agent-ready-gif-") as tmp:
        tmp_path = Path(tmp)
        frames: list[Image.Image] = []
        frame_counts = [1, 6, 12, len(lines)]
        for index, count in enumerate(frame_counts):
            frame_path = tmp_path / f"frame-{index}.png"
            write_terminal_png(lines[:count], frame_path)
            if frame_path.exists():
                frames.append(Image.open(frame_path).convert("P", palette=Image.Palette.ADAPTIVE))
        if frames:
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=[450, 450, 450, 1400], loop=0)
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Agent Ready demo assets.")
    parser.add_argument("--require-images", action="store_true", help="Fail if PNG/GIF assets cannot be generated.")
    args = parser.parse_args(argv)
    if not DEMO_SOURCE.exists():
        raise SystemExit(f"Demo source missing: {DEMO_SOURCE}")
    if (DEMO_SOURCE / ".agent-ready").exists():
        raise SystemExit("Demo source must stay clean: remove examples/demo-repo/.agent-ready before rebuilding assets.")
    ASSETS.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agent-ready-demo-") as tmp:
        repo = Path(tmp) / "acme-workbench"
        shutil.copytree(DEMO_SOURCE, repo)
        before = run([sys.executable, "-B", str(CLI), "scan", str(repo)], ROOT).stdout
        run([sys.executable, "-B", str(CLI), "plan", str(repo), "--min-score", "80"], ROOT)
        after = run([sys.executable, "-B", str(CLI), str(repo), "--all", "--badge"], ROOT).stdout
        run([sys.executable, "-B", str(CLI), "check", str(repo), "--min-score", "80", "--format", "github", "--write-report", "--write-summary", "--write-comment", "--write-sarif"], ROOT)
        run([sys.executable, "-B", str(CLI), "validate", str(repo), "--dry-run"], ROOT)
        run([sys.executable, "-B", str(CLI), "pr", str(repo), "--force"], ROOT)
        run([sys.executable, "-B", str(CLI), "config", str(repo)], ROOT)
        run([sys.executable, "-B", str(CLI), "baseline", str(repo)], ROOT)
        with (repo / "README.md").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n<!-- Agent Ready demo seed: api_key = 'abcdefghijklmnopqrstuvwxyz' -->\n")
        run_expect([sys.executable, "-B", str(CLI), "diff", str(repo)], ROOT, {1})
        run([sys.executable, "-B", str(CLI), "snapshot", str(repo), "--baseline"], ROOT)
        copy_selected(repo)
    lines = [
        "$ python agent-ready.py plan examples/demo-repo --min-score 80",
        "+ Wrote a prioritized fix plan for the unprepared repo",
        "$ python agent-ready.py examples/demo-repo --all --badge",
        *[line for line in after.splitlines() if line.strip()][:14],
        "+ Generated AGENTS.md, companion instructions, summary, scorecard, badge, CI, PR kit",
        "$ python agent-ready.py check examples/demo-repo --format github --write-report --write-summary --write-comment --write-sarif",
        "+ Wrote CI-ready reports, PR comment, summary, SARIF, and annotation output",
        "$ python agent-ready.py config examples/demo-repo",
        "+ Wrote a reusable agent-ready.config.json policy template",
        "$ python agent-ready.py baseline examples/demo-repo",
        "+ Captured current findings for gradual CI adoption",
        "$ python agent-ready.py diff examples/demo-repo",
        "+ Reported new/resolved findings against the baseline",
        "$ python agent-ready.py snapshot examples/demo-repo --baseline",
        "+ Wrote one summary page with scorecard, top fixes, and diff",
        "$ python agent-ready.py validate examples/demo-repo --dry-run",
        "+ Planned validation commands without executing local scripts",
    ]
    (ASSETS / "terminal-demo.svg").write_text(terminal_svg(lines), encoding="utf-8", newline="\n")
    wrote_png = write_terminal_png(lines, ASSETS / "terminal-demo.png")
    wrote_gif = write_terminal_gif(lines, ASSETS / "terminal-demo.gif")
    if args.require_images and not (wrote_png and wrote_gif):
        raise SystemExit("Pillow is required to generate PNG/GIF demo assets. Install with `python -m pip install Pillow`.")
    (DEMO_OUTPUT / "scan-before.txt").write_text(sanitize_demo_text(before, DEMO_SOURCE), encoding="utf-8", newline="\n")
    (DEMO_OUTPUT / "ready-after.txt").write_text(sanitize_demo_text(after, DEMO_SOURCE), encoding="utf-8", newline="\n")
    print(f"Wrote {DEMO_OUTPUT}")
    print(f"Wrote {ASSETS / 'terminal-demo.svg'}")
    if (ASSETS / "terminal-demo.png").exists():
        print(f"Wrote {ASSETS / 'terminal-demo.png'}")
    if (ASSETS / "terminal-demo.gif").exists():
        print(f"Wrote {ASSETS / 'terminal-demo.gif'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
