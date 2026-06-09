"""Repository scanning and Agent Ready score calculation."""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".turbo",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "bower_components",
    "dist",
    "build",
    "out",
    "coverage",
    "target",
    "bin",
    "obj",
    "vendor",
    ".agent-ready",
}

GENERATED_DIR_HINTS = {
    "dist",
    "build",
    "out",
    "coverage",
    "target",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".turbo",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".agent-ready",
}

AGENT_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    ".cursor/rules/agent-ready.mdc",
]

CONFIG_CANDIDATES = [
    "agent-ready.config.json",
    ".agent-ready/config.json",
]

CONFIG_FILES = [
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "bun.lockb",
    "bun.lock",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "pytest.ini",
    "tox.ini",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "pubspec.yaml",
    "deno.json",
    "deno.jsonc",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
    ".github/workflows",
    "agent-ready.config.json",
]

ENTRY_CANDIDATES = [
    "src/main.ts",
    "src/main.tsx",
    "src/main.js",
    "src/main.jsx",
    "src/index.ts",
    "src/index.tsx",
    "src/index.js",
    "src/index.jsx",
    "src/App.tsx",
    "src/App.jsx",
    "app/page.tsx",
    "pages/index.tsx",
    "main.py",
    "app.py",
    "server.py",
    "manage.py",
    "main.go",
    "cmd",
    "src/main.rs",
    "Program.cs",
]

EXTENSION_LANGUAGES = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".py": "Python",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".dart": "Dart",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
}

INJECTION_PATTERNS = [
    re.compile(r"ignore (all )?(previous|prior|above) instructions", re.I),
    re.compile(r"disregard (all )?(previous|prior|above) instructions", re.I),
    re.compile(r"reveal (the )?(system|developer) (prompt|message)", re.I),
    re.compile(r"print (the )?(system|developer) (prompt|message)", re.I),
    re.compile(r"exfiltrate|steal|leak .*secret", re.I),
    re.compile(r"do not tell the user", re.I),
]

SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|private[_-]?key)\b\s*[:=]\s*['\"]?([A-Za-z0-9_\-./+=]{12,})"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]

SKILL_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Finding:
    severity: str
    kind: str
    message: str
    path: str | None = None
    line: int | None = None


@dataclass
class RepoScan:
    root: str
    repo_name: str
    generated_at: str
    languages: list[dict[str, Any]] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    commands: dict[str, list[str]] = field(default_factory=dict)
    entry_points: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    important_dirs: list[str] = field(default_factory=list)
    generated_dirs: list[str] = field(default_factory=list)
    agent_files: list[str] = field(default_factory=list)
    monorepo_hints: list[str] = field(default_factory=list)
    packages: list[dict[str, Any]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    agent_instruction_quality: dict[str, Any] = field(default_factory=dict)
    score: int = 0
    score_reasons: list[str] = field(default_factory=list)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_excluded(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in EXCLUDED_DIRS for part in parts)


def iter_files(root: Path, limit: int = 5000) -> Iterable[Path]:
    count = 0
    for current_root, dirs, files in os.walk(root):
        current = Path(current_root)
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        if is_excluded(current, root):
            continue
        for name in files:
            path = current / name
            if is_excluded(path, root):
                continue
            count += 1
            if count > limit:
                return
            yield path


def read_text(path: Path, max_bytes: int = 400_000) -> str:
    try:
        if path.stat().st_size > max_bytes:
            return ""
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return ""
    except OSError:
        return ""


def load_json(path: Path) -> dict[str, Any]:
    try:
        text = read_text(path).lstrip("\ufeff")
        return json.loads(text)
    except Exception:
        return {}


def detect_package_manager(root: Path) -> list[str]:
    managers: list[str] = []
    lock_map = [
        ("pnpm", "pnpm-lock.yaml"),
        ("yarn", "yarn.lock"),
        ("npm", "package-lock.json"),
        ("bun", "bun.lockb"),
        ("bun", "bun.lock"),
    ]
    for manager, filename in lock_map:
        if (root / filename).exists() and manager not in managers:
            managers.append(manager)
    package_json = load_json(root / "package.json") if (root / "package.json").exists() else {}
    package_manager = str(package_json.get("packageManager", ""))
    if package_manager:
        manager = package_manager.split("@", 1)[0].strip()
        if manager and manager not in managers:
            managers.insert(0, manager)
    if (root / "package.json").exists() and not managers:
        managers.append("npm")
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        managers.append("pip/uv/poetry")
    if (root / "go.mod").exists():
        managers.append("go")
    if (root / "Cargo.toml").exists():
        managers.append("cargo")
    if (root / "pom.xml").exists():
        managers.append("maven")
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        managers.append("gradle")
    if (root / "composer.json").exists():
        managers.append("composer")
    if (root / "pubspec.yaml").exists():
        managers.append("dart/flutter")
    return unique(managers)


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def script_command(manager: str, script_name: str) -> str:
    if manager == "pnpm":
        return f"pnpm {script_name}"
    if manager == "yarn":
        return f"yarn {script_name}"
    if manager == "bun":
        return f"bun run {script_name}"
    return f"npm run {script_name}"


def detect_commands(root: Path, managers: list[str]) -> dict[str, list[str]]:
    commands: dict[str, list[str]] = {"install": [], "run": [], "test": [], "build": [], "lint": [], "typecheck": []}
    package_json_path = root / "package.json"
    js_manager = next((m for m in managers if m in {"pnpm", "yarn", "npm", "bun"}), "npm")
    if package_json_path.exists():
        package_json = load_json(package_json_path)
        scripts = package_json.get("scripts", {}) if isinstance(package_json, dict) else {}
        if isinstance(scripts, dict):
            if js_manager == "pnpm":
                commands["install"].append("pnpm install")
            elif js_manager == "yarn":
                commands["install"].append("yarn install")
            elif js_manager == "bun":
                commands["install"].append("bun install")
            else:
                commands["install"].append("npm install")
            for name in scripts:
                lower = str(name).lower()
                if lower in {"dev", "start", "serve"}:
                    commands["run"].append(script_command(js_manager, str(name)))
                elif "test" in lower:
                    commands["test"].append(script_command(js_manager, str(name)))
                elif lower in {"build", "compile"} or "build" in lower:
                    commands["build"].append(script_command(js_manager, str(name)))
                elif "lint" in lower:
                    commands["lint"].append(script_command(js_manager, str(name)))
                elif "type" in lower and "check" in lower:
                    commands["typecheck"].append(script_command(js_manager, str(name)))
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or (root / "setup.py").exists():
        if (root / "requirements.txt").exists():
            commands["install"].append("python -m pip install -r requirements.txt")
        elif (root / "pyproject.toml").exists():
            commands["install"].append("python -m pip install -e .")
        if (root / "pytest.ini").exists() or any(root.glob("test*.py")) or (root / "tests").exists():
            commands["test"].append("python -m pytest")
        if (root / "manage.py").exists():
            commands["run"].append("python manage.py runserver")
    if (root / "go.mod").exists():
        commands["test"].append("go test ./...")
        commands["build"].append("go build ./...")
    if (root / "Cargo.toml").exists():
        commands["test"].append("cargo test")
        commands["build"].append("cargo build")
        commands["lint"].append("cargo clippy")
    if (root / "pom.xml").exists():
        commands["test"].append("mvn test")
        commands["build"].append("mvn package")
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        commands["test"].append("./gradlew test")
        commands["build"].append("./gradlew build")
    if (root / "Makefile").exists():
        make_text = read_text(root / "Makefile")
        for target in ["test", "build", "lint", "run"]:
            if re.search(rf"^{target}\s*:", make_text, re.M):
                commands[target].append(f"make {target}")
    return {key: unique(value) for key, value in commands.items() if unique(value)}


def detect_frameworks(root: Path) -> list[str]:
    frameworks: list[str] = []
    package_json = load_json(root / "package.json") if (root / "package.json").exists() else {}
    deps: dict[str, Any] = {}
    if isinstance(package_json, dict):
        for key in ["dependencies", "devDependencies", "peerDependencies"]:
            value = package_json.get(key)
            if isinstance(value, dict):
                deps.update(value)
    dep_names = set(deps)
    js_frameworks = {
        "next": "Next.js",
        "react": "React",
        "vue": "Vue",
        "vite": "Vite",
        "svelte": "Svelte",
        "@angular/core": "Angular",
        "express": "Express",
        "@nestjs/core": "NestJS",
        "astro": "Astro",
        "tailwindcss": "Tailwind CSS",
        "electron": "Electron",
    }
    for dep, label in js_frameworks.items():
        if dep in dep_names:
            frameworks.append(label)
    text_blobs = []
    for name in ["pyproject.toml", "requirements.txt", "setup.py"]:
        path = root / name
        if path.exists():
            text_blobs.append(read_text(path).lower())
    py_blob = "\n".join(text_blobs)
    py_frameworks = {
        "django": "Django",
        "fastapi": "FastAPI",
        "flask": "Flask",
        "pytest": "pytest",
        "pydantic": "Pydantic",
        "streamlit": "Streamlit",
    }
    for token, label in py_frameworks.items():
        if token in py_blob:
            frameworks.append(label)
    if (root / "go.mod").exists():
        go_mod = read_text(root / "go.mod").lower()
        if "gin-gonic/gin" in go_mod:
            frameworks.append("Gin")
        if "gofiber/fiber" in go_mod:
            frameworks.append("Fiber")
    return unique(frameworks)


def detect_languages(files: list[Path]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for path in files:
        language = EXTENSION_LANGUAGES.get(path.suffix.lower())
        if language:
            counter[language] += 1
    total = sum(counter.values()) or 1
    return [
        {"language": language, "files": count, "share": round(count / total, 3)}
        for language, count in counter.most_common(8)
    ]


def detect_entry_points(root: Path) -> list[str]:
    entries: list[str] = []
    for candidate in ENTRY_CANDIDATES:
        path = root / candidate
        if path.exists():
            entries.append(candidate)
    return unique(entries[:20])


def detect_config_files(root: Path) -> list[str]:
    found: list[str] = []
    for item in CONFIG_FILES:
        path = root / item
        if path.exists():
            found.append(item)
    for pattern in ["*.sln", "*.csproj", "*.fsproj", "*.xcodeproj", "*.xcworkspace"]:
        for path in root.glob(pattern):
            found.append(rel(path, root))
    return unique(found[:40])


def detect_dirs(root: Path) -> tuple[list[str], list[str]]:
    important: list[str] = []
    generated: list[str] = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        name = path.name
        if name in EXCLUDED_DIRS or name.startswith(".git"):
            continue
        if name in GENERATED_DIR_HINTS:
            generated.append(name)
        elif name in {"src", "app", "pages", "components", "lib", "server", "api", "tests", "test", "docs", "cmd", "pkg", "internal", "public", "scripts"}:
            important.append(name)
    for hint in GENERATED_DIR_HINTS:
        if (root / hint).exists() and hint not in generated:
            generated.append(hint)
    return unique(important), unique(generated)


def detect_agent_files(root: Path) -> list[str]:
    return [path for path in AGENT_FILES if (root / path).exists()]


def detect_monorepo(root: Path) -> list[str]:
    hints: list[str] = []
    package_json = load_json(root / "package.json") if (root / "package.json").exists() else {}
    workspaces = package_json.get("workspaces") if isinstance(package_json, dict) else None
    if workspaces:
        hints.append("package.json workspaces")
    if (root / "pnpm-workspace.yaml").exists():
        hints.append("pnpm-workspace.yaml")
    if (root / "turbo.json").exists():
        hints.append("turbo.json")
    if (root / "nx.json").exists():
        hints.append("nx.json")
    for dirname in ["apps", "packages", "services"]:
        if (root / dirname).is_dir():
            child_configs = list((root / dirname).glob("*/package.json")) + list((root / dirname).glob("*/pyproject.toml"))
            if child_configs:
                hints.append(f"{dirname}/ contains package configs")
    return unique(hints)


def is_package_root(path: Path) -> bool:
    markers = [
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "composer.json",
        "pubspec.yaml",
    ]
    return any((path / marker).exists() for marker in markers)


def detect_packages(root: Path) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for dirname in ["apps", "packages", "services", "libs"]:
        base = root / dirname
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name in EXCLUDED_DIRS:
                continue
            if not is_package_root(child):
                continue
            files = list(iter_files(child, limit=1500))
            managers = detect_package_manager(child)
            packages.append(
                {
                    "path": rel(child, root),
                    "languages": detect_languages(files),
                    "frameworks": detect_frameworks(child),
                    "package_managers": managers,
                    "commands": detect_commands(child, managers),
                    "entry_points": [rel(child / entry, root) for entry in detect_entry_points(child)],
                    "config_files": [rel(child / config, root) for config in detect_config_files(child) if (child / config).exists()],
                }
            )
    return packages[:40]


def scan_text_findings(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    readable_candidates: list[Path] = []
    for path in files:
        relative = rel(path, root)
        name = path.name.lower()
        if (
            relative in AGENT_FILES
            or name in {"readme.md", "contributing.md", "security.md"}
            or relative.startswith("docs/")
            or relative.startswith(".github/")
            or path.suffix.lower() in {".md", ".mdc", ".txt", ".env", ".yml", ".yaml", ".json", ".toml"}
        ):
            readable_candidates.append(path)
    for path in readable_candidates[:1000]:
        text = read_text(path, max_bytes=120_000)
        if not text:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            for pattern in INJECTION_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding("high", "prompt-injection", "Prompt-injection-like instruction found", rel(path, root), idx))
                    break
            for pattern in SECRET_PATTERNS:
                match = pattern.search(line)
                if match and not is_redacted_secret_report_line(line, match):
                    findings.append(Finding("critical", "secret", "Secret-looking value found; value redacted", rel(path, root), idx))
                    break
    return findings


def is_redacted_secret_report_line(line: str, match: re.Match[str]) -> bool:
    """Avoid flagging Agent Ready's own redacted finding text as a new secret."""
    if len(match.groups()) < 2:
        return False
    value = match.group(2).lower()
    lowered = line.lower()
    return value.startswith("secret-looking") and "value redacted" in lowered


def lint_agent_conflicts(root: Path, package_managers: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    manager_mentions: dict[str, set[str]] = {}
    manager_tokens = ["npm", "pnpm", "yarn", "bun"]
    for agent_file in AGENT_FILES:
        path = root / agent_file
        if not path.exists():
            continue
        text = read_text(path, max_bytes=200_000).lower()
        mentions = {token for token in manager_tokens if re.search(rf"\b{re.escape(token)}\b", text)}
        if mentions:
            manager_mentions[agent_file] = mentions
        if len(text.split()) > 2500:
            findings.append(Finding("medium", "length", "Agent instruction file is long; consider tightening it", agent_file))
    all_mentions = set().union(*manager_mentions.values()) if manager_mentions else set()
    detected_js_managers = [m for m in package_managers if m in manager_tokens]
    if len(all_mentions) > 1:
        findings.append(Finding("high", "conflict", f"Multiple JS package managers mentioned across agent files: {', '.join(sorted(all_mentions))}"))
    if detected_js_managers and all_mentions:
        detected = detected_js_managers[0]
        unexpected = sorted(m for m in all_mentions if m != detected)
        if unexpected:
            findings.append(Finding("high", "conflict", f"Agent files mention {', '.join(unexpected)} but detected package manager is {detected}"))
    return findings


def evaluate_agent_instruction_quality(root: Path, scan: RepoScan) -> dict[str, Any]:
    path = root / "AGENTS.md"
    checks: list[dict[str, Any]] = []
    if not path.exists():
        return {
            "score": 0,
            "max_score": 8,
            "checks": [
                {
                    "name": "AGENTS.md exists",
                    "passed": False,
                    "reason": "Primary agent instruction file is missing.",
                }
            ],
        }
    text = read_text(path, max_bytes=200_000)
    lower = text.lower()
    detected_commands = [
        command
        for name in ["install", "run", "test", "build", "lint", "typecheck"]
        for command in scan.commands.get(name, [])[:2]
    ]
    mentioned_commands = [command for command in detected_commands if command.lower() in lower]
    check_specs = [
        (
            "Detected commands are documented",
            bool(detected_commands) and len(mentioned_commands) >= min(2, len(detected_commands)),
            "Mention at least the primary detected validation/setup commands in AGENTS.md.",
        ),
        (
            "Project map is documented",
            "project map" in lower and ("entry point" in lower or "important directories" in lower),
            "Include entry points, important directories, and package-level project context.",
        ),
        (
            "Safety rules are documented",
            "safety" in lower and ("secret" in lower or "generated" in lower),
            "Document secret handling, generated directories, and validation expectations.",
        ),
        (
            "Instructions are concise enough to maintain",
            len(text.split()) <= 1200,
            "Keep AGENTS.md concise so it can be kept current as the repository changes.",
        ),
    ]
    for name, passed, fix in check_specs:
        checks.append({"name": name, "passed": passed, "reason": "Passed." if passed else fix})
    passed_count = sum(1 for check in checks if check["passed"])
    return {
        "score": passed_count * 2,
        "max_score": 8,
        "checks": checks,
        "documented_commands": mentioned_commands,
        "detected_commands": detected_commands,
    }


def scorecard_item(
    category: str,
    check: str,
    passed: bool,
    points: int,
    reason: str,
    fix: str,
    awarded: int | None = None,
) -> dict[str, Any]:
    earned = points if awarded is None and passed else int(awarded or 0)
    if earned >= points:
        status = "passed"
    elif earned > 0:
        status = "partial"
    else:
        status = "missing"
    next_step = fix
    if status == "passed" and not fix.lower().startswith("keep "):
        next_step = "No action needed."
    return {
        "category": category,
        "check": check,
        "status": status,
        "points": earned,
        "max_points": points,
        "reason": reason,
        "fix": next_step,
    }


def scorecard_items(scan: RepoScan) -> list[dict[str, Any]]:
    agent_points = 0
    agent_reason = "No agent instruction file detected"
    agent_fix = "Run `agent-ready . --all --badge` to generate AGENTS.md and companion instruction files."
    if "AGENTS.md" in scan.agent_files:
        agent_points = 12
        agent_reason = "Primary AGENTS.md exists"
        agent_fix = "Keep AGENTS.md current when commands or repo structure change."
    elif scan.agent_files:
        agent_points = 6
        agent_reason = "Some agent instruction file exists"
        agent_fix = "Add AGENTS.md as the primary cross-agent instruction file."
    quality = scan.agent_instruction_quality or {}
    quality_points = int(quality.get("score", 0) or 0)
    quality_max = int(quality.get("max_score", 8) or 8)
    quality_reason = "AGENTS.md covers commands, project map, safety, and stays concise"
    quality_fix = "Mention detected commands, project map, safety rules, and keep AGENTS.md maintainable."
    if quality_points <= 0:
        quality_reason = "AGENTS.md quality checks did not pass"
    elif quality_points < quality_max:
        quality_reason = "AGENTS.md passed some quality checks"
    return [
        scorecard_item(
            "project-map",
            "Languages detected",
            bool(scan.languages),
            10,
            "Detected repository languages" if scan.languages else "No source language signal detected",
            "Scan the repository root that contains real source files.",
        ),
        scorecard_item(
            "project-map",
            "Config files detected",
            bool(scan.config_files),
            10,
            "Detected config files" if scan.config_files else "No recognizable project config detected",
            "Add standard project metadata such as package.json, pyproject.toml, go.mod, Cargo.toml, or Makefile.",
        ),
        scorecard_item(
            "project-map",
            "Project map detected",
            bool(scan.entry_points or scan.important_dirs),
            10,
            "Detected project map" if scan.entry_points or scan.important_dirs else "No entry point or important directory detected",
            "Use conventional entry files or directories so agents can map the project quickly.",
        ),
        scorecard_item(
            "validation",
            "Test command detected",
            bool(scan.commands.get("test")),
            15,
            "Detected test command" if scan.commands.get("test") else "No test command detected",
            "Add a deterministic test command to package metadata, pytest config, Makefile, or equivalent.",
        ),
        scorecard_item(
            "validation",
            "Build command detected",
            bool(scan.commands.get("build")),
            10,
            "Detected build command" if scan.commands.get("build") else "No build command detected",
            "Add a build command that catches integration errors before agents finish work.",
        ),
        scorecard_item(
            "validation",
            "Run command detected",
            bool(scan.commands.get("run")),
            5,
            "Detected run command" if scan.commands.get("run") else "No local run command detected",
            "Add a conventional dev/start/run script or Makefile target.",
        ),
        scorecard_item(
            "agent-instructions",
            "Agent instruction coverage",
            agent_points == 12,
            12,
            agent_reason,
            agent_fix,
            awarded=agent_points,
        ),
        scorecard_item(
            "agent-instructions",
            "Agent instruction quality",
            quality_points >= quality_max,
            quality_max,
            quality_reason,
            quality_fix,
            awarded=quality_points,
        ),
        scorecard_item(
            "safety",
            "No instruction conflicts",
            not any(f.kind == "conflict" for f in scan.findings),
            6,
            "No obvious instruction conflicts" if not any(f.kind == "conflict" for f in scan.findings) else "Instruction conflicts detected",
            "Align agent files with detected package managers and validation commands.",
        ),
        scorecard_item(
            "safety",
            "No prompt-injection findings",
            not any(f.kind == "prompt-injection" for f in scan.findings),
            7,
            "No obvious prompt-injection findings" if not any(f.kind == "prompt-injection" for f in scan.findings) else "Prompt-injection-like text detected",
            "Rewrite or remove suspicious instructions from files agents may read.",
        ),
        scorecard_item(
            "safety",
            "No secret findings",
            not any(f.kind == "secret" for f in scan.findings),
            7,
            "No obvious secret findings" if not any(f.kind == "secret" for f in scan.findings) else "Secret-looking value detected",
            "Remove the value, rotate it if real, and keep only redacted examples.",
        ),
    ]


def compute_score(scan: RepoScan) -> tuple[int, list[str]]:
    items = scorecard_items(scan)
    raw_score = sum(int(item["points"]) for item in items)
    reasons = [str(item["reason"]) for item in items if int(item["points"]) > 0]
    return min(raw_score, 100), reasons


def scan_repo(root: Path) -> RepoScan:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Repository path does not exist or is not a directory: {root}")
    files = list(iter_files(root))
    managers = detect_package_manager(root)
    scan = RepoScan(
        root=str(root),
        repo_name=root.name,
        generated_at=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        languages=detect_languages(files),
        frameworks=detect_frameworks(root),
        package_managers=managers,
        commands=detect_commands(root, managers),
        entry_points=detect_entry_points(root),
        config_files=detect_config_files(root),
        important_dirs=[],
        generated_dirs=[],
        agent_files=detect_agent_files(root),
        monorepo_hints=detect_monorepo(root),
        packages=detect_packages(root),
        findings=[],
    )
    scan.important_dirs, scan.generated_dirs = detect_dirs(root)
    scan.findings.extend(scan_text_findings(root, files))
    scan.findings.extend(lint_agent_conflicts(root, scan.package_managers))
    scan.agent_instruction_quality = evaluate_agent_instruction_quality(root, scan)
    scan.score, scan.score_reasons = compute_score(scan)
    return scan

