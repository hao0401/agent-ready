# Agent Ready Report

Score: **100/100**

![Agent Ready](https://img.shields.io/badge/Agent%20Ready-100%2F100-brightgreen)

## Score Reasons

- Detected repository languages
- Detected config files
- Detected project map
- Detected test command
- Detected build command
- Detected run command
- Primary AGENTS.md exists
- AGENTS.md covers commands, project map, safety, and stays concise
- No obvious instruction conflicts
- No obvious prompt-injection findings
- No obvious secret findings

## Findings

- No findings

## Recommended Fixes

- No major fixes detected

## Detected Commands

- Install: `pnpm install`
- Run locally: `pnpm dev`
- Test: `pnpm test`
- Build: `pnpm build`
- Lint: `pnpm lint`
- Typecheck: `pnpm typecheck`

## Detected Project Map

- Languages: TypeScript (2), Python (2)
- Frameworks: React, Vite
- Package managers/build tools: pnpm

Entry points:

- `src/main.ts`

Important directories:

- `src`

Generated/dependency directories:

- `.agent-ready`

## Package-Level Projects

- `apps/web` - React, Vite; pnpm; run: `pnpm dev`; test: `pnpm test`; build: `pnpm build`; lint: `pnpm lint`; typecheck: `pnpm typecheck`
- `services/api` - FastAPI, pytest; pip/uv/poetry; test: `python -m pytest`
