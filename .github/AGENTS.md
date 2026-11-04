# AGENTS.md — `.github/`

Rules for editing CI and GitHub metadata.

- `ci.yml` is the whole gate. A change here changes what "green" means for every
  pull request, so keep the steps runnable locally as written in the root
  [AGENTS.md](../AGENTS.md) and [CONTRIBUTING.md](../CONTRIBUTING.md).
- Do not rename the job key `gnn-conformance` or its display name
  `gnn conformance (pinned)`. [models/README.md](../models/README.md)
  documents that name and the pin story depends on it.
- Keep action pins as full commit SHAs with a version comment. Dependabot
  updates them; review the SHA, not just the comment.
- `gnn-pin.json` is read by CI and by `tests/test_gnn.py`. Changing `revision`
  or `tag` requires a matching update in [models/README.md](../models/README.md)
  and a passing `gnn conformance (pinned)` run.
- The secret-scan step downloads gitleaks, verifies its SHA-256, and runs a
  synthetic negative control. Do not weaken it, and do not extend
  [.gitleaksignore](../.gitleaksignore) with a path or pattern; only a full
  finding is allowed.
- `dependabot.yml` changes are dependency policy. A dependency PR must still
  satisfy `uv lock --check` and the coverage floor.
