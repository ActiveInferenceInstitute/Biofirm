# AGENTS.md — Biofirm repository root

Read [README.md](README.md) first: it defines the package, the commands and the
safety boundaries. This file is the editing contract. It does not restate the
README; it lists what must pass and what breaks.

## Checks that must pass before you push

CI is `.github/workflows/ci.yml` (workflow `biofirm-ci`). The `quality` job runs
on Python 3.11 and 3.12. From the repository root:

```bash
uv sync --frozen --all-extras
uv lock --check
uv run pytest --cov=biofirm --cov-report=term-missing --cov-fail-under=90
uv run ruff check src tests tools
uv run ruff format --check src tests tools
uv run mypy --python-version 3.12 src/biofirm
uv run bandit -q -r src tools
uv run python tools/verify_repository.py
uv run biofirm validate
uv run biofirm validate-data
uv run python -m build
```

The second job is keyed `gnn-conformance` and its display name is exactly
`gnn conformance (pinned)`. Keep both. It fetches the parser revision
recorded in [.github/gnn-pin.json](.github/gnn-pin.json) and runs
`tests/test_gnn.py`; [models/README.md](models/README.md) names that job. The
job also reports the resolved version in its step summary, and the pin remains
the source of truth.

`tools/verify_repository.py` is part of the gate. It compiles `src`, imports the
package, requires a non-empty version, requires the nine documents named in
`tools/verify_repository.py` to exist and be non-empty, resolves every
relative markdown link, validates the source JSON under `One_Earth/` and
`Bio_Perplexity/`, rejects shell or magic commands in notebooks, and scans
tracked text files for credential patterns. A broken relative link in any
markdown file fails CI. Do not link outside this repository from committed
markdown; the check resolves targets against the file's own directory and a
link that escapes the checkout has no target on the CI runner.

## Generated versus hand-written

Nothing in this repository is generated navigation. Every markdown file is
hand-written and must change in the same commit as the behavior it describes.
[CONTRIBUTING.md](CONTRIBUTING.md) makes docs part of the change and asks you to
add new contract documents to [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md).

Generated or derived artefacts are never committed:

- `requirements.lock` is git-ignored. CI derives the hashed requirements export
  from `uv.lock` into `$RUNNER_TEMP` at run time. A committed copy would be a
  second source of truth. Do not create one.
- `dist/`, `.venv/`, `.coverage`, `.mypy_cache/`, `.pytest_cache/`,
  `__pycache__/`, and anything under `artifacts/`, `outputs/`, or the ignored
  `Outputs/` and `Visualizations/` subdirectories are outputs.
- `.coverage` in the working tree is a local pytest artefact; it is ignored.

## Custody-critical files

- [models/biofirm_ecosystem_variable.gnn.md](models/biofirm_ecosystem_variable.gnn.md)
  is the single source of truth for controller model structure. `src/biofirm/gnn.py`
  parses it without the upstream `gnn` package; `tests/test_gnn.py` asserts the
  declared `A`, `B`, `C`, `D` matrices equal what
  `build_active_inference_matrices(3)` builds and that the invariants hold for
  odd bin counts 3, 5, 7 and 9. Editing the spec or the matrices without the
  other fails the suite. See [models/AGENTS.md](models/AGENTS.md).
- [.github/gnn-pin.json](.github/gnn-pin.json) records tag `v5.0.3` and revision
  `8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`. `tests/test_gnn.py`
  checks the pin still dereferences upstream.
- [.gitleaksignore](.gitleaksignore) holds exact historical findings only. CI
  proves with a synthetic control that a new commit at an old path is not
  exempt. Do not add a pattern or a path, only a full finding.
- [src/biofirm/_version.py](src/biofirm/_version.py) is the only version source;
  `pyproject.toml` reads it through `tool.hatch.version`. Bump it there.
- [src/biofirm/data/ecosystem.json](src/biofirm/data/ecosystem.json) is the
  packaged default configuration. Schema changes must keep the versioned
  artifact contract valid.

## Traps

- A dependency change that edits `pyproject.toml` without regenerating and
  committing `uv.lock` fails `uv lock --check` in the install step. Run
  `uv lock` after every pin change. Never commit `requirements.lock`.
- `mypy` is strict and scoped to `src/biofirm`; `ruff` covers `src`, `tests` and
  `tools`; `bandit` excludes `tests` and `Documentation/Notebooks`.
- The coverage floor is 90%. New behavior lands with tests.
- Source data under `One_Earth/` and `Bio_Perplexity/` is authoritative input,
  not generated output. Regenerating or editing it changes what
  `biofirm validate-data` checks.
- Historical material in `One_Earth/`, `Stream/` and
  [GRAPH_MODELING.md](GRAPH_MODELING.md) carries status blocks. Do not restate
  it as implemented behavior or as evidence.
- Live research is the only network path. It needs both `--live` and
  `PERPLEXITY_API_KEY` in the environment. Never put a key in a tracked file.

## Directory guide

Each directory carries its own `README.md` and `AGENTS.md`. Read them before
editing inside one: [.github/](.github/README.md), [.github/workflows/](.github/workflows/README.md),
[.aii/](.aii/README.md), [src/](src/README.md), [src/biofirm/](src/biofirm/README.md),
[src/biofirm/data/](src/biofirm/data/README.md), [tests/](tests/README.md),
[tools/](tools/README.md), [models/](models/README.md), [docs/](docs/README.md),
[Documentation/](Documentation/README.md),
[Documentation/Notebooks/](Documentation/Notebooks/README.md),
[Bio_Perplexity/](Bio_Perplexity/README.md), [One_Earth/](One_Earth/README.md),
[Stream/](Stream/README.md).
