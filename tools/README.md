# `tools/`

Two scripts: [verify_repository.py](verify_repository.py), the repository-level
contract check, and [gate_report.py](gate_report.py), the producer for
[../docs/gate.md](../docs/gate.md). Both run as arms of [`../run.sh`](../run.sh)
from the repository root.

## `verify_repository.py`

The `links` arm:

```bash
./run.sh links   # uv run python tools/verify_repository.py
```

It fails, with a message naming the file, when any of these do not hold:

- `src` compiles with `compileall`.
- `biofirm` imports and `biofirm.__version__` is non-empty.
- The nine required documents exist and are non-empty: `README.md`,
  `Biofirm_Generative_Model.md`, `CONFIGURATION.md`, `TODO.md`,
  `DOCUMENTATION_INDEX.md`, `One_Earth/INSTALLATION_GUIDE.md`,
  `GRAPH_MODELING.md`, `models/README.md`, and
  `models/biofirm_ecosystem_variable.gnn.md`.
- Every relative markdown link under the repository resolves.
- `One_Earth/oneearth_bioregion_ecoregions.json` has exactly 185 leaf regions
  with unique non-empty IDs and names, and the region and prompt files match
  their schemas.
- No notebook code cell starts a line with `!` or `%`.
- No text file outside the skipped directories matches a credential pattern.

It skips `.git`, `.venv`, `artifacts`, `Outputs`, `Visualizations` and
`__pycache__`.

## `gate_report.py`

The producer for the one generated document, and the `gate` arm that checks it:

```bash
uv run python tools/gate_report.py           # run every arm, rewrite docs/gate.md
./run.sh gate                                # uv run python tools/gate_report.py --check
```

`--write` (the default) runs each arm of `../run.sh`, records one wall time per
arm as the **After** column, and parses the full-suite pass count and coverage
total out of the test output. It also reads
[gate_baseline.json](gate_baseline.json) for the **Before** column. The arm
descriptions in the document are read from `run.sh`'s own header table, so prose
cannot drift from the commands.

[`gate_baseline.json`](gate_baseline.json) (`biofirm-gate-baseline/v1`) is the
preserved receipt for the pre-change gate: the commands CI ran directly, one run
each, at commit `c88b5d3`. The pre-change tree no longer exists, so those numbers
cannot be re-measured and must not be regenerated; the script only reads the
file and records its schema, commit and environment in the document receipt.

`--check` re-times nothing. It proves the document still describes the gate that
exists: it has the Before/After table, the arm list equals `./run.sh list` (minus
the `all` and `gate` meta arms), the recorded `uv.lock` SHA-256 equals the current
file, every arm has a measured value, and every arm has a baseline entry with a
recorded command. A wall time is a receipt for one host, not a contract, which is
why CI checks the document's shape, the arm coverage and the baseline provenance
but never its numbers.
