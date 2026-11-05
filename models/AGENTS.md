# AGENTS.md — `models/`

Read [README.md](README.md) first; it documents the specification, the loader
and the pin. This file is the editing contract.

- [biofirm_ecosystem_variable.gnn.md](biofirm_ecosystem_variable.gnn.md) is the
  single source of truth for model structure: factors, modalities, `A`, `B`,
  `C`, `D`, controls and transition axis order. Do not edit it to match code and
  do not edit code to match it in separate changes.
- A spec change requires the matching change in
  [../src/biofirm/gnn.py](../src/biofirm/gnn.py) invariants and
  [../src/biofirm/pymdp.py](../src/biofirm/pymdp.py) matrices, plus a passing
  `tests/test_gnn.py` for bin counts 3, 5, 7 and 9.
- The spec must stay parseable by `src/biofirm/gnn.py` **without** the upstream
  `gnn` package. That loader is a deliberate second reader; breaking it breaks
  offline installs.
- The pin lives in [../.github/gnn-pin.json](../.github/gnn-pin.json) and is
  repeated in [README.md](README.md). Changing `tag` or `revision` requires both
  to change together and the `gnn conformance (pinned)` job to pass.
- Keep the claim boundary intact. The variables, targets and coefficients are
  illustrative configuration; structural validation never certifies calibrated
  ecological evidence. Do not add language that claims otherwise.
- Syntax authority is the pinned upstream `docs/gnn/reference/gnn_syntax.md`.
  Do not invent sections or flags; validate with the pinned parser.
- No generated files belong here. Every file is hand-written.
