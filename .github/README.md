# `.github/`

GitHub and CI configuration for this repository. No application code lives here.

- [workflows/ci.yml](workflows/ci.yml) — the only workflow; two jobs, `quality`
  and `gnn-conformance` (display name `gnn conformance (pinned)`).
- [gnn-pin.json](gnn-pin.json) — the pinned Generalized Notation Notation
  parser revision, tag `v5.0.3` at commit `8f293d9ba810e6eda5c09842d9c7ed9ffa5f92c1`.
- [dependabot.yml](dependabot.yml) — monthly `uv` updates and weekly grouped
  GitHub Actions updates.

See [workflows/README.md](workflows/README.md) for the job contents and the
repository [AGENTS.md](../AGENTS.md) for the checks that gate a merge.
