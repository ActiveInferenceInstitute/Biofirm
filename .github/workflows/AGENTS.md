# AGENTS.md — `.github/workflows/`

- `ci.yml` is the only workflow file. Do not add a second workflow that
  duplicates the gate; extend the existing jobs instead.
- The `gnn conformance (pinned v5.0.3)` display name and the `gnn-conformance`
  job key are referenced by [../../models/README.md](../../models/README.md) and
  by the repository [AGENTS.md](../../AGENTS.md). Keep both unchanged.
- The requirements export is written to `$RUNNER_TEMP`, never to the checkout.
  If you edit the install step, keep the export out of the working tree: the
  file is git-ignored and a committed copy is forbidden.
- The clean-environment step runs `biofirm validate`, `simulate`, `sweep`,
  `analyze`, `visualize`, `parse-description` and `business-evaluate` from a
  temporary directory. Removing a command from that step reduces coverage of
  the installed wheel, so keep the set complete when the CLI gains a command.
- The secret-scan step must keep its SHA-256 verification of the gitleaks
  archive and both negative controls. A weakened scan is a security change, not
  a CI cleanup.
- Verify a workflow edit by running the equivalent commands locally from the
  repository root before pushing; this workflow has no separate self-test.
