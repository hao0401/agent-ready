# Contributing

Thanks for improving Agent Ready.

## Local Checks

Run these from the repository root before opening a PR:

```powershell
python -B scripts\dev.py test check release clean
python -B scripts\dev.py publish-check
```

If `make` is available, the equivalent targets are:

```powershell
make test
make check
make build
make clean
make publish-check
```

The direct commands behind those tasks are:

```powershell
python -B -m py_compile agent-ready.py agent_ready\cli.py agent_ready\__main__.py scripts\agent_ready.py scripts\test_agent_ready.py scripts\build_demo_assets.py scripts\release_check.py scripts\dev.py
python -B -m unittest scripts.test_agent_ready
python -B scripts\build_demo_assets.py --require-images
python -B agent-ready.py doctor examples\demo-repo
python -B agent-ready.py check examples\demo-repo --min-score 80 --no-require-agents
python -B scripts\release_check.py
```

## Change Guidelines

- Keep the CLI dependency-free unless the feature is optional.
- Preserve safe defaults: do not overwrite user files unless `--force` is passed.
- Add tests for new command behavior, generated file behavior, or safety checks.
- Regenerate demo assets when CLI output or README examples change.
- Do not commit local temp paths, secrets, caches, or generated Python bytecode.

## PR Checklist

- [ ] Unit tests pass.
- [ ] Demo assets were regenerated when relevant.
- [ ] README examples match real CLI output.
- [ ] New checks are documented in README and `--help`.
