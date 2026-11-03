# `src/biofirm/`

The installable `biofirm` package. Eighteen modules plus the packaged default
configuration in [data/](data/README.md).

## Modules

| Module | Responsibility |
| --- | --- |
| `__init__.py` | Public API surface; `__all__` is the stable export list. |
| `__main__.py` | `python -m biofirm` entry point. |
| `_version.py` | The only version source; read by `pyproject.toml`. |
| `config.py` | Typed configuration, strict validation, canonical JSON and hashing. |
| `simulation.py` | Transition dynamics, immutable run history, comparison and scenarios. |
| `controllers.py` | Slide-rule, random, active-inference and business controllers behind one decision contract. |
| `pymdp.py` | Validated generative matrices for the installed PyMDP API. |
| `gnn.py` | GNN specification loader, declared-matrix reader and conformance checks. |
| `analysis.py` | Free-energy, surprise and token-allocation analysis. |
| `business.py` | Auditable committee decisions and action definitions. |
| `graph.py` | Experimental regional interaction graph with provenance. |
| `data_validation.py` | Validation and provenance summaries for source data. |
| `text.py` | Deterministic bioregion text extraction and optional document parsing. |
| `visualization.py` | Deterministic plotting with explicit optional-dependency errors. |
| `research.py` | The single network-enabled live research path with provenance. |
| `io.py` | Atomic JSON and text writers. |
| `immutability.py` | Recursive freeze/thaw for public result contracts. |
| `cli.py` | The `biofirm` console script and its subcommands. |

## Contracts worth knowing

- `__all__` in [__init__.py](__init__.py) exports configuration, simulation,
  comparison, data validation and graph entry points. Modules outside that list
  are implementation details even when the CLI imports them.
- Simulation artifacts carry a schema version and are validated on read. See
  [Biofirm_Generative_Model.md](../../Biofirm_Generative_Model.md).
- Optional dependencies are grouped in `pyproject.toml` as `analysis`,
  `visualization` and `documents`. Missing optional extras raise typed errors
  rather than degrading silently.

## Check it

```bash
uv run pytest --cov=biofirm --cov-fail-under=90
uv run ruff check src tests tools
uv run mypy --python-version 3.12 src/biofirm
uv run bandit -q -r src tools
```

Package layout and install instructions are in [../README.md](../README.md) and
the repository [README.md](../../README.md).
