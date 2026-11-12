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
  and re-validates with the pinned upstream parser from the export the `gnn` arm
  writes. It does not read the pin; the shared reader does.
- [`../models/AGENTS.md`](../models/AGENTS.md) — the editing contract.
- [`../models/README.md`](../models/README.md) — the full model reference.

## Pin

The canonical pin file is
[`../.github/gnn-pin.json`](../.github/gnn-pin.json), schema
`gnn-importer-pin/v1`:

- Repository: `ActiveInferenceInstitute/Generalized_Notation_Notation`
- Tag: `v5.1.0`
- Revision: `75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf`
- Schema: `gnn-importer-pin/v1`
- Recorded: `2026-11-12`
- Specification files: `models/biofirm_ecosystem_variable.gnn.md`

The pin is read by the shared reader — `gnn.importers`, shipped in the pinned
revision — which the `gnn` arm runs from a clean export of that revision:

```bash
./run.sh gnn
```

The arm materializes the pinned revision in a checkout with its own
interpreter, exports the revision's `src` tree with `git archive` (never the GNN
checkout's working tree, so in-progress edits in a sibling checkout cannot
contaminate the result), and runs

```bash
python -m gnn.importers check --repo . --require-pointer \
  --workflow .github/workflows/ci.yml --job gnn-conformance
```

That validates the pin's shape and repository, the pointer
[`../.github/GNN.md`](../.github/GNN.md) and the selected specification's
syntax, with the parser the pin names. `tests/test_gnn.py` then runs in the same
export.

CI runs this in the job keyed `gnn-conformance`, displayed as
`gnn conformance (pinned)`, so the pin is re-checked on every push and pull
request. The pointer is the short record of what that job parses and what it
does not cover.

Measured arm times, the test count and the coverage total live in
[gate.md](gate.md), which [`../tools/gate_report.py`](../tools/gate_report.py)
refreshes.

## GNN–FEP member cutover: adopted

The [GNN–FEP workflow contract](https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/blob/75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf/docs/workflows/gnn-fep.md)
binds this repository to one reader for its pin, its pointer and its
specification. Biofirm's pin moved from `v5.0.3` at
`8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1` — a revision that predates
`src/gnn/importers.py`, added upstream in `e6a9d3917` — to `v5.1.0` at
`75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf`, which ships it. The cutover
completed in that change:

- The local pin reader in `tests/test_gnn.py` (`PIN_PATH`, `_pin()`, the
  field-by-field pin assertions and the tag-resolution test that used them) is
  deleted. The shared reader reports `pin-missing`, `pin-unreadable`,
  `pin-commit-shape`, `pin-tag-mismatch`, `pin-repository-mismatch`,
  `pin-schema-unversioned`, `spec-missing`, `spec-invalid` and the pointer codes
  itself, so the deleted copy carried no unique coverage.
- `./run.sh gnn` runs `python -m gnn.importers check --repo . --require-pointer
  --workflow .github/workflows/ci.yml --job gnn-conformance` from the pinned
  revision's export, before `tests/test_gnn.py`.
- Provisioning fails when the pinned tag does not dereference to the pinned
  revision; that is the one check the reader does not make, because it does not
  read git.
- Nothing is vendored: no copy of `importers.py`, no newer reader overlaid on an
  older parser.

This repository has no manuscript producer, so the contract's
`gnn.importers.importer_variables` step does not apply here.

## Editing rules

Editing the specification or the matrices without the other fails
`tests/test_gnn.py`. A spec change requires the matching change in
[`../src/biofirm/gnn.py`](../src/biofirm/gnn.py) invariants and the
[`../src/biofirm/pymdp.py`](../src/biofirm/pymdp.py) matrices, and the pin must
stay at the newest GNN release. Re-validate with the pinned parser:

```bash
# from this repository; <gnn-checkout> is the sibling checkout or $GNN_CHECKOUT
export_dir=$(mktemp -d)
git -C <gnn-checkout> archive 75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf src/gnn pyproject.toml \
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
