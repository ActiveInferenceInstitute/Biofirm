# GNN model specifications

This directory holds the Generalized Notation Notation (GNN) specifications for
the generative models declared by this repository. The GNN files are the
**single source of truth for model structure**: hidden-state factors and their
cardinalities, observation modalities, the `A` (likelihood) and `B`
(transition) factor-dependency structure, the control cardinalities, the
transition tensor axis order, and the declared parameterization of the default
instantiation.

GNN is the Active Inference Institute specification language and implementation
core; the pinned upstream revision for this repository is recorded in
[`.github/gnn-pin.json`](../.github/gnn-pin.json).

## Files

| File | Model | Scope |
| --- | --- | --- |
| `biofirm_ecosystem_variable.gnn.md` | `biofirm_ecosystem_variable` | One hidden factor (`s_bin`, 3 levels: below/at/above target) and one identity-likelihood modality (`o_level`, 3); controls (3) are the decrease/hold/increase contract that shifts the level by one bin and clips at the physical bounds; preferences peak at the target level; the prior is uniform. |

The specification declares the default three-bin instantiation and the
structural contract every odd `observation_bins` value preserves. The
per-variable bin count is configuration (`CONFIGURATION.md`), and
`tests/test_gnn.py` checks the declared structure against
`build_active_inference_matrices` for the default and for the generalized bin
counts.

## Loader and drift guard

`src/biofirm/gnn.py` parses the specification without depending on the upstream
`gnn` package and exposes `load_spec`, `declared_matrix`, and
`conformance_issues`. `tests/test_gnn.py` asserts that:

- the declared factor, modality, control, and connection structure matches the
  expected dependency graph;
- the declared `A`/`B`/`C`/`D` values equal the matrices
  `build_active_inference_matrices(3)` builds, element by element;
- the declared invariants (identity likelihood, uniform prior, target-peaked
  preferences, clipped shift transition, column-stochastic normalization) hold
  for other odd `observation_bins` values (3, 5, 7, 9);
- the recorded pin still dereferences to the recorded revision; and
- the pinned upstream parser accepts the specification under `--strict`.

Editing the specification or the matrices without the other side fails the test
suite. The upstream checks run against a clean export of the pinned revision
(`git archive <revision> src/gnn`) with the GNN checkout's interpreter, so
in-progress edits in a sibling checkout cannot contaminate the result; they
skip with an explicit reason when no checkout was selected, and fail when
`GNN_CHECKOUT` selects a missing or unusable one. CI runs this file in the
`gnn conformance (pinned)` job, which fetches the pinned revision from
the public upstream repository and provisions its interpreter, so the pin is
re-checked on every push and pull request.

## Upstream pin

- Upstream repository:
  `https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation.git`
- Pinned tag: `v5.0.3`
- Pinned revision: `8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1` (the commit the
  `v5.0.3` tag dereferences to)
- Upstream version: `5.0.3`
- Pinned on: `2026-11-01`

Re-validation runs the pinned upstream validator against this specification:

```bash
# from this repository; <gnn-checkout> is the sibling checkout or $GNN_CHECKOUT
export_dir=$(mktemp -d)
git -C <gnn-checkout> archive 8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1 src/gnn pyproject.toml \
  | tar -x -C "$export_dir"
PYTHONPATH="$export_dir/src" <gnn-checkout>/.venv/bin/python -m gnn.cli validate \
  models/biofirm_ecosystem_variable.gnn.md --strict
```

`tests/test_gnn.py` performs exactly this validation, and the syntax authority
is `docs/gnn/reference/gnn_syntax.md` in that checkout. For new integrations,
start from the upstream [Framework Integration
Guide](https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/blob/8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1/docs/gnn/integration/framework_integration_guide.md)
and the [downstream adoption
guide](https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation/blob/1f3abb56e25886dfa6ddc49c76af7b723941485a/docs/gnn/integration/downstream_adoption.md).

## Claim boundary

The discretization, controller, and specification are implemented and tested.
The ecological variables, targets, and relationship coefficients are
illustrative configuration: structural validation establishes model structure
and matrix agreement, and never certifies calibrated ecological evidence.
