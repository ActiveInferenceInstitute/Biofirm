# AGENTS.md — `src/`

- Nothing belongs at this level except the `biofirm/` package directory and
  these two guides. Do not add a second top-level package without updating
  [../pyproject.toml](../pyproject.toml) (`tool.hatch.build.targets.wheel`) and
  [../AGENTS.md](../AGENTS.md).
- The layout is `src`-based. `tests/conftest.py` inserts `<root>/src` on
  `sys.path`, so tests import the working tree directly; run them from the
  repository root with `uv run pytest`.
- Add new modules inside [biofirm/](biofirm/AGENTS.md) and follow its rules.
