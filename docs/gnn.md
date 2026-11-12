# GNN specification and pin

The active-inference controller's generative model is specified in
[Generalized Notation Notation](https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation)
(GNN). The specification is the single source of truth for model structure —
hidden-state factors and cardinalities, observation modalities, the `A`
(likelihood) and `B` (transition) dependency structure, control cardinalities,
transition-tensor axis order, and the declared parameterization of the default
instantiation.

## Files

- [`../models/biofirm_ecosystem_variable.gnn.md`](../models/biofirm_ecosystem_variable.gnn.md)
  — the specification: one hidden factor (`s_bin`, three levels
  below/at/above target), one identity-likelihood modality (`o_level`, three),
  the three decrease/hold/increase controls, target-peaked preferences, and a
  uniform prior.
- [`../src/biofirm/gnn.py`](../src/biofirm/gnn.py) — a loader that parses the
  specification **without** the upstream `gnn` package (`load_spec`,
  `declared_matrix`, `conformance_issues`).
- [`../src/biofirm/pymdp.py`](../src/biofirm/pymdp.py) — builds the PyMDP/JAX
  matrices the specification must match.
- [`../tests/test_gnn.py`](../tests/test_gnn.py) — checks the declared `A`, `B`,
  `C`, `D` matrices equal `build_active_inference_matrices(3)` for the default
  model and hold the invariants for odd `observation_bins` counts 3, 5, 7 and 9,
  and re-validates with the pinned upstream parser when a clean export is
  available.
- [`../models/AGENTS.md`](../models/AGENTS.md) — the editing contract.
- [`../models/README.md`](../models/README.md) — the full model reference.

## Pin

The canonical pin file is
[`../.github/gnn-pin.json`](../.github/gnn-pin.json), schema
`gnn-importer-pin/v1`:

- Repository: `ActiveInferenceInstitute/Generalized_Notation_Notation`
- Tag: `v5.0.3`
- Revision: `8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`
- Schema: `gnn-importer-pin/v1`
- Recorded: `2026-11-12`
- Specification files: `models/biofirm_ecosystem_variable.gnn.md`

`tests/test_gnn.py` reads the parser from a clean `git archive` of that revision
— never from the GNN checkout's working tree — so in-progress edits in a sibling
checkout cannot contaminate the result. When no checkout is selected the
upstream half skips with an explicit reason; when `GNN_CHECKOUT` selects a
missing or unusable checkout it fails.

CI runs this file in the job keyed `gnn-conformance`, displayed as
`gnn conformance (pinned)`, which fetches the pinned revision and provisions its
interpreter, so the pin is re-checked on every push and pull request.
[`../.github/GNN.md`](../.github/GNN.md) is the short pointer that records what
that job parses and what it does not cover. Locally the same check is one arm of
the gate:

```bash
./run.sh gnn
```

Measured arm times, the test count and the coverage total live in
[gate.md](gate.md), which [`../tools/gate_report.py`](../tools/gate_report.py)
refreshes.

## Editing rules

Editing the specification or the matrices without the other fails
`tests/test_gnn.py`. A spec change requires the matching change in
[`../src/biofirm/gnn.py`](../src/biofirm/gnn.py) invariants and the
[`../src/biofirm/pymdp.py`](../src/biofirm/pymdp.py) matrices, and the pin must
stay at the newest GNN release. Re-validate with the pinned parser:

```bash
# from this repository; <gnn-checkout> is the sibling checkout or $GNN_CHECKOUT
export_dir=$(mktemp -d)
git -C <gnn-checkout> archive 8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1 src/gnn pyproject.toml \
  | tar -x -C "$export_dir"
PYTHONPATH="$export_dir/src" <gnn-checkout>/.venv/bin/python -m gnn.cli validate \
  models/biofirm_ecosystem_variable.gnn.md --strict
```

## Claim boundary

The discretization, controller, and specification are implemented and tested.
The ecological variables, targets, and relationship coefficients are
illustrative configuration: structural validation establishes model structure
and matrix agreement and never certifies calibrated ecological evidence.

## Related

- [GNN model specifications](../models/README.md) — full reference.
- [Generative model](../Biofirm_Generative_Model.md) — the computational
  contract the specification describes.
