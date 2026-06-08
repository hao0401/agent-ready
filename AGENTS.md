# Agent Ready Contributor Notes

## Project Map

- `agent_ready/cli.py` contains the CLI, repository scanner, file generators, reports, scorecards, and GitHub output helpers.
- `agent-ready.py` is the source-tree launcher.
- `scripts/test_agent_ready.py` contains the regression test suite.
- `scripts/build_demo_assets.py` regenerates `examples/demo-output/` and terminal assets.
- `scripts/release_check.py` is the release gate and should pass before packaging.
- `examples/demo-repo/` is the clean demo input repository. Keep generated output out of this folder.
- `examples/demo-output/` and `assets/terminal-demo.*` are reproducible showcase artifacts.

## Commands

Use these from the repository root:

```powershell
python -B -m unittest scripts.test_agent_ready
python -B scripts\build_demo_assets.py --require-images
python -B scripts\release_check.py
python -B agent-ready.py check examples\demo-repo --min-score 80 --no-require-agents
python -B scripts\dev.py test check release clean
python -B scripts\dev.py publish-check
```

If `make` is available:

```sh
make test
make check
make build
make run
make clean
make publish-check
```

## Editing Rules

- Keep the CLI dependency-free at runtime. Optional demo dependencies belong in `pyproject.toml` extras.
- Preserve safe defaults: generation must not overwrite user files unless `--force` is passed.
- Add or update tests for command behavior, generated files, scoring, safety checks, and GitHub output changes.
- Regenerate demo assets when CLI output, README examples, reports, or showcase files change.
- Keep `examples/demo-repo/` clean: do not leave `.agent-ready/` or `agent-ready.config.json` there.
- Do not commit local temp paths, credentials, `.agent-ready/`, build artifacts, egg-info, caches, or bytecode.
