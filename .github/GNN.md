# GNN conformance

`gnn conformance (pinned)` is the display name of the job keyed
`gnn-conformance` in `.github/workflows/ci.yml`. It reads the canonical pin file
`.github/gnn-pin.json` (schema `gnn-importer-pin/v1`), which pins
`ActiveInferenceInstitute/Generalized_Notation_Notation` at `v5.1.0`
(`75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf`).

The job fetches that revision into its own checkout with its own interpreter,
exports its `src` tree, and then runs the shared `gnn.importers` reader shipped
in that revision against this checkout:

```bash
python -m gnn.importers check --repo . --require-pointer \
  --workflow .github/workflows/ci.yml --job gnn-conformance
```

The reader validates the pin's shape and repository, checks that this pointer
names the pin, the revision, the workflow and the job key, and validates the
specification selected by `.github/gnn-pin.json`
(`models/biofirm_ecosystem_variable.gnn.md`) with the pinned parser.
`tests/test_gnn.py` then checks the declared matrices against the
implementation and re-validates the specification file with the pinned upstream
`gnn.cli validate --strict`. It does not scan every repository `*.gnn.md`; this
is a pin and model conformance baseline for the selected specification, not a
claim that every sketch is covered.

The job body is the `gnn` arm of [`../run.sh`](../run.sh), so the local command
is the CI command:

```bash
./run.sh gnn
```

See [`../docs/gnn.md`](../docs/gnn.md) for the loader and editing rules, and
[`../docs/gate.md`](../docs/gate.md) for the measured arm times.
