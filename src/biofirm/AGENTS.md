# AGENTS.md — `src/biofirm/`

Rules for changing the package. Root commands and the full gate are in
[../../AGENTS.md](../../AGENTS.md).

## Checks that must pass

```bash
uv run pytest --cov=biofirm --cov-report=term-missing --cov-fail-under=90
uv run ruff check src tests tools
uv run ruff format --check src tests tools
uv run mypy --python-version 3.12 src/biofirm
uv run bandit -q -r src tools
```

mypy is strict for this package only. Ruff covers `src tests tools`.

## Generated versus hand-written

Every module here is hand-written. There is no code generation step. The only
generated artefact connected to the package is the hashed requirements export,
which is derived from `uv.lock` at run time and never committed. See the root
[AGENTS.md](../../AGENTS.md).

## Custody-critical

- [__init__.py](__init__.py) defines the public API in `__all__`. Adding or
  removing a name is a public interface change; update
  [../../README.md](../../README.md) and [../../DOCUMENTATION_INDEX.md](../../DOCUMENTATION_INDEX.md)
  when the contract changes.
- [_version.py](_version.py) is the single version source. Bump it here, not in
  `pyproject.toml`, which reads it through `tool.hatch.version`.
- [pymdp.py](pymdp.py) builds the `A`, `B`, `C` and `D` matrices and
  [gnn.py](gnn.py) parses the GNN spec. Both are tied to
  [../../models/biofirm_ecosystem_variable.gnn.md](../../models/biofirm_ecosystem_variable.gnn.md);
  changing a matrix without the spec fails `tests/test_gnn.py`.
- [io.py](io.py) writes artifacts atomically and refuses empty documents. Keep
  that guarantee: callers rely on "no empty success artifact".
- [simulation.py](simulation.py) owns the versioned artifact contract. A change
  to keys or schema requires a new schema version and migration notes.

## Traps

- Do not import optional dependencies at module import time. `analysis`,
  `visualization` and `documents` extras are optional; import them inside the
  function that needs them and raise the typed dependency error on failure.
- The active-inference controller needs JAX and PyMDP. Keep JAX-specific
  handling behind [pymdp.py](pymdp.py) and [controllers.py](controllers.py).
- Anything network-capable belongs in [research.py](research.py) only. Other
  modules must stay offline.
- Public result objects are frozen through [immutability.py](immutability.py).
  Do not return mutable internals from a public function.
- Do not add a module to `__all__` without a test that exercises the exported
  name.
- `src/biofirm/data/` is package data. Read its [AGENTS.md](data/AGENTS.md)
  before editing the packaged configuration.
