# GNN conformance

`gnn conformance (pinned)` is the display name of the job keyed
`gnn-conformance` in `.github/workflows/ci.yml`. It reads the canonical pin file
`.github/gnn-pin.json` (schema `gnn-importer-pin/v1`), which pins
`ActiveInferenceInstitute/Generalized_Notation_Notation` at `v5.0.3`
(`8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`).

The job fetches that revision into its own checkout with its own interpreter,
then runs `tests/test_gnn.py`. The test validates the specification selected by
`.github/gnn-pin.json` (`models/biofirm_ecosystem_variable.gnn.md`) with the
pinned upstream `gnn.cli validate --strict`, and checks the declared matrices
against the implementation. It does not scan every repository `*.gnn.md`; this
is a pin and model conformance baseline for the selected specification, not a
claim that every sketch is covered.

The job body is the `gnn` arm of [`../run.sh`](../run.sh), so the local command
is the CI command:

```bash
./run.sh gnn
```

See [`../docs/gnn.md`](../docs/gnn.md) for the loader and editing rules, and
[`../docs/gate.md`](../docs/gate.md) for the measured arm times.
