# Agent Ready Demo

Repository: `acme-workbench`

## Before

- Agent must infer package manager from scattered files.
- Test/build commands may be guessed or skipped.
- Tool-specific instruction files can conflict silently.
- Prompt-injection and secret-looking text may be read without warning.

## After

- Agent readiness score: **100/100**.
- Primary and companion instruction files are generated.
- Detected commands, project map, and package-level projects are documented.
- Prompt-injection, secret-looking values, and package-manager conflicts are reported.

## Badge

![Agent Ready](https://img.shields.io/badge/Agent%20Ready-100%2F100-brightgreen)

## Top Commands

- Install: `pnpm install`
- Run locally: `pnpm dev`
- Test: `pnpm test`
- Build: `pnpm build`
- Lint: `pnpm lint`
- Typecheck: `pnpm typecheck`

## Package-Level Projects

- `apps/web` - React, Vite; pnpm; run: `pnpm dev`; test: `pnpm test`; build: `pnpm build`; lint: `pnpm lint`; typecheck: `pnpm typecheck`
- `services/api` - FastAPI, pytest; pip/uv/poetry; test: `python -m pytest`
