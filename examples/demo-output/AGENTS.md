# AGENTS.md

Instructions for AI coding agents working in this repository.

## Repository Snapshot

- Repository: `acme-workbench`
- Main languages: TypeScript (2), Python (2)
- Frameworks/libraries detected: React, Vite
- Package managers/build tools: pnpm

## Project Map

Entry points:

- `src/main.ts`

Important directories:

- `src`

Configuration files:

- `package.json`
- `pnpm-lock.yaml`
- `.github/workflows`

Generated or dependency directories agents should avoid editing:

- `.agent-ready`

Monorepo signals:

- package.json workspaces
- pnpm-workspace.yaml
- apps/ contains package configs

Package-level projects:

- `apps/web` - React, Vite; pnpm; run: `pnpm dev`; test: `pnpm test`; build: `pnpm build`; lint: `pnpm lint`; typecheck: `pnpm typecheck`
- `services/api` - FastAPI, pytest; pip/uv/poetry; test: `python -m pytest`

## Commands

- Install: `pnpm install`
- Run locally: `pnpm dev`
- Test: `pnpm test`
- Build: `pnpm build`
- Lint: `pnpm lint`
- Typecheck: `pnpm typecheck`

If a command is marked "Not detected", inspect package metadata or CI config before
claiming it works.

## Agent Workflow

1. Read this file before editing.
2. Inspect the smallest relevant module before changing code.
3. Prefer existing patterns, helpers, and framework conventions.
4. Keep edits scoped to the requested behavior.
5. Run the most specific detected validation command before finishing.
6. Report any command that could not be run, including the reason.

## Safety Rules

- Do not edit generated output, dependency folders, caches, or build artifacts.
- Do not expose secrets. If a secret-looking value is found, report only the file
  and line with the value redacted.
- Do not invent test/build commands. Use detected commands or explain what needs
  manual verification.
- For broad changes, check CI workflow files and package metadata before editing.
- If repository facts conflict with these instructions, trust current files and
  update this instruction file in the same change.
