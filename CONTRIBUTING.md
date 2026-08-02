# Contributing to Biofirm

Thanks for contributing to Biofirm. This guide covers the current package.
Historical design material lives under `One_Earth/` and `Stream/` and is
marked as such; do not treat it as an implementation contract.

## Development setup

Biofirm supports Python 3.11 and 3.12. The committed `uv.lock` and
`requirements.lock` provide a hash-locked environment:

```bash
uv sync --frozen --all-extras
uv run biofirm validate
uv run biofirm validate-data
```

Without `uv`, install the package editable with the extras you need:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,analysis,visualization,documents]"
```

## Checks

Run the same checks as CI before pushing:

```bash
pytest --cov=biofirm --cov-fail-under=90
ruff check src tests tools
ruff format --check src tests tools
mypy --python-version 3.12 src/biofirm
bandit -q -r src tools
python tools/verify_repository.py
uv lock --check
python -m build
```

`tools/verify_repository.py` enforces the documentation contract: required
documents exist and are non-empty, local markdown links resolve, source data
validates, notebooks contain no shell or magic commands, and no credential
patterns appear in tracked files.

## Conventions

- **Commits**: use conventional commit prefixes (`docs:`, `fix:`, `chore:`,
  `feat:`), keep commits scoped, and reference backlog IDs from `TODO.md`
  where applicable.
- **Behavior changes need tests**: every implemented backlog item lands with
  tests, documentation, and an explicit acceptance check. The suite must
  remain at zero failures with the 90% coverage floor.
- **Docs travel with code**: update the README, the generative-model contract,
  and `DOCUMENTATION_INDEX.md` when commands, the schema, or artifact
  contracts change. Add new documents to the index.
- **Never commit credentials**: live research is the only network-enabled
  path and requires an explicit `--live` flag plus `PERPLEXITY_API_KEY` in
  the environment. `.env.example` is a placeholder; a real key never belongs
  in a tracked file.
- **Historical material stays labelled**: anything describing an unimplemented
  or superseded system carries a status block and is listed as historical in
  `DOCUMENTATION_INDEX.md`.
- **Artifacts are not source**: generated research, simulation, report, plot,
  log, and cache files belong under `artifacts/` or another ignored runtime
  directory. Authoritative data under `One_Earth/` and `Bio_Perplexity/`
  remains input, not generated output.

## Work tracking

`TODO.md` is the sole current backlog. Completed items are recorded there and
kept in Git history; the "Scoped (deferred)" section holds large-scale work
that is intentionally not implemented yet. If you pick up a scoped item,
update the backlog in the same change.

## Asking questions

Open a GitHub issue for bug reports and feature requests. For suspected
security issues, follow [SECURITY.md](SECURITY.md) instead.
