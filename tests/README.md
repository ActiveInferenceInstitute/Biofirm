# `tests/`

The pytest suite. Fifteen `test_*.py` modules plus [conftest.py](conftest.py).

`conftest.py` inserts `<repository-root>/src` on `sys.path`, so the suite imports
the working tree rather than an installed copy. `pyproject.toml` sets
`testpaths = ["tests"]` and `addopts = "-ra"`.

| Module | Covers |
| --- | --- |
| `test_config.py` | Typed configuration, aliases, cycle and range rejection, canonical JSON. |
| `test_simulation.py` | Transition dynamics, artifact schema, reproducibility, comparisons, scenarios. |
| `test_pymdp.py` | Matrix validation and the active-inference boundary. |
| `test_gnn.py` | GNN spec against the built matrices; pinned parser when a checkout is selected. |
| `test_analysis.py` | Surprise, free energy and token allocation. |
| `test_business_contracts.py` | Committee configuration and auditable decisions. |
| `test_graph.py` | Regional graph validation and descriptive summaries. |
| `test_data_validation.py` | The 185 One Earth leaves, region maps and prompt files. |
| `test_text_business.py` | Text extraction plus business evaluation paths. |
| `test_visualization.py` | Deterministic plotting and optional-dependency errors. |
| `test_research.py` | Live-research provenance with a fake provider. |
| `test_io.py` | Atomic writers and empty-artifact refusal. |
| `test_cli.py`, `test_entrypoint.py` | Command surface and `python -m biofirm`. |
| `test_notebook.py` | Executes the walkthrough notebook offline. |

## Run it

```bash
uv run pytest --cov=biofirm --cov-report=term-missing --cov-fail-under=90
```

The 90% floor is enforced in CI. Bandit excludes this directory.
