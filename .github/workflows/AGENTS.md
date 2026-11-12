# AGENTS.md — `.github/workflows/`

- `ci.yml` is the only workflow file. Do not add a second workflow that
  duplicates the gate; extend [`../../run.sh`](../../run.sh) and call the new arm
  from the existing jobs.
- Every step is an arm of `../../run.sh`. Do not inline a command that an arm
  already owns: CI and the local gate would drift.
- The `gnn conformance (pinned)` display name and the `gnn-conformance`
  job key are referenced by [../../models/README.md](../../models/README.md),
  [../GNN.md](../GNN.md), [../../docs/gnn.md](../../docs/gnn.md) and the
  repository [AGENTS.md](../../AGENTS.md). Keep both unchanged.
- Keep `quality` single-version. Its arms are interpreter-independent; adding
  them to the `tests` matrix duplicates work without checking anything new.
- The requirements export stays out of the checkout: the `install` arm writes it
  to a temporary directory. A committed copy is forbidden, because it is a second
  source of truth a lock-only dependency update cannot regenerate.
- The `install` arm runs `biofirm validate`, `simulate`, `sweep`, `analyze`,
  `visualize`, `parse-description` and `business-evaluate` from a temporary
  directory. Removing a command from that arm reduces coverage of the installed
  wheel, so keep the set complete when the CLI gains a command.
- The `secret` arm must keep its per-platform SHA-256 verification of the
  gitleaks archive and both negative controls. A weakened scan is a security
  change, not a CI cleanup.
- Verify a workflow edit by running the equivalent arms locally from the
  repository root before pushing; this workflow has no separate self-test.
