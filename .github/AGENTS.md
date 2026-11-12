# AGENTS.md — `.github/`

Rules for editing CI and GitHub metadata.

- [`../run.sh`](../run.sh) is the gate. Every workflow step calls one of its
  arms, so a change to a check is a change to `run.sh`, not to YAML. Keep the
  arm table in `run.sh`'s header, `../docs/gate.md` and the workflow in sync;
  `./run.sh gate` fails when the arm list and the document disagree.
- Do not rename the job key `gnn-conformance` or its display name
  `gnn conformance (pinned)`. [GNN.md](GNN.md), [../models/README.md](../models/README.md)
  and [../docs/gnn.md](../docs/gnn.md) document that name.
- Keep action pins as full commit SHAs with a version comment, including the
  composite action `ActiveInferenceInstitute/.github/.github/actions/setup-python-uv`.
  Dependabot updates them; review the SHA, not just the comment.
- `gnn-pin.json` is read by CI through the shared `gnn.importers` reader in the
  `gnn` arm, not by `tests/test_gnn.py`. It carries schema
  `gnn-importer-pin/v1`; changing `revision`, `tag` or `version` requires a
  matching update in [../models/README.md](../models/README.md),
  [../docs/gnn.md](../docs/gnn.md) and [GNN.md](GNN.md), and a passing
  `./run.sh gnn`.
- Do not re-add per-version lint, type, documentation, build or install steps to
  the `tests` matrix. Those arms are interpreter-independent and run once on
  3.12; duplicating them doubles work without checking anything new.
- The `secret` arm downloads gitleaks, verifies a per-platform SHA-256, and runs
  two synthetic negative controls. Do not weaken it, and do not extend
  [.gitleaksignore](../.gitleaksignore) with a path or pattern; only a full
  finding is allowed.
- `dependabot.yml` changes are dependency policy. A dependency PR must still
  satisfy `./run.sh deps` and the coverage floor in `./run.sh test`.
