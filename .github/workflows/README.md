# `.github/workflows/`

One workflow: [ci.yml](ci.yml), named `biofirm-ci`. It runs on every push and
every pull request and calls arms of [`../../run.sh`](../../run.sh); no command
is written twice, and a local `./run.sh ...` run executes what CI executes.

Every job sets `BIOFIRM_PYTHON`, installs uv and CPython through the pinned
composite action
`ActiveInferenceInstitute/.github/.github/actions/setup-python-uv@7159e67315330aac8e414aebae0ad1e999a41448`,
then runs `./run.sh sync` once. The composite action installs uv `0.13.7` from
`astral-sh/setup-uv` and `uv python install`s the requested interpreter, so
there is no `pip install uv` step anywhere.

## `quality`

Runs once, on Python 3.12. The arms are interpreter-independent, so running them
per version would only duplicate work. In order: `sync`, `deps`, `lint`,
`types`, `links`, `docs`, `gate`, `bandit`, `build`, `install`, `secret`.

`install` derives the hashed requirements export from `uv.lock` at run time into
a temporary directory, installs the wheel into a clean venv, and exercises the
CLI commands outside the checkout. The export is never committed: a committed
copy would be a second source of truth that a lock-only dependency update cannot
regenerate. `secret` downloads a pinned gitleaks build, verifies its SHA-256,
and runs two negative controls (a synthetic credential, and a synthetic
credential at a path with an exact historical exception).

## `tests`

Matrix Python 3.11 and 3.12. Each leg runs `sync` and `test`, the full suite
with the 90% coverage floor. This is the only work duplicated per version.

## `gnn conformance (pinned)`

Job key `gnn-conformance`, display name `gnn conformance (pinned)`. Runs `sync`
and the `gnn` arm. The arm materializes the revision recorded in
[../gnn-pin.json](../gnn-pin.json) — it reuses a usable `GNN_CHECKOUT`, else a
sibling checkout that contains the pinned commit, else it fetches the pin and
provisions a temporary interpreter with numpy, defusedxml and psutil — exports
that revision's `src` tree with `git archive`, and runs the shared
`gnn.importers` reader shipped in it against this checkout. A pin that no longer
resolves, a tag that does not dereference to the recorded revision, or a pointer
that omits the pin, revision, workflow or job key fails the run. The arm then
runs `tests/test_gnn.py` from the same export; the test never silently skips
when a selected checkout or export is missing or unusable. The arm also writes
the resolved parser version to the job summary.

Measured arm times for this host live in
[../../docs/gate.md](../../docs/gate.md), refreshed by
[../../tools/gate_report.py](../../tools/gate_report.py) and checked in the
`gate` arm.
