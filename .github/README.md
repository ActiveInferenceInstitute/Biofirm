# `.github/`

GitHub and CI configuration for this repository. No application code lives here.

- [workflows/ci.yml](workflows/ci.yml) — the only workflow; three jobs:
  `quality`, `tests`, and `gnn-conformance` (display name
  `gnn conformance (pinned)`). Every step is an arm of [../run.sh](../run.sh).
- [gnn-pin.json](gnn-pin.json) — the canonical Generalized Notation Notation
  parser pin (schema `gnn-importer-pin/v1`), tag `v5.1.0` at commit
  `75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf`.
- [GNN.md](GNN.md) — what `gnn conformance (pinned)` parses and does not cover.
- [dependabot.yml](dependabot.yml) — monthly `uv` updates and weekly grouped
  GitHub Actions updates.

See [workflows/README.md](workflows/README.md) for the job contents, the gate
document [../docs/gate.md](../docs/gate.md) for the measured arm times, and the
repository [AGENTS.md](../AGENTS.md) for the checks that gate a merge.
