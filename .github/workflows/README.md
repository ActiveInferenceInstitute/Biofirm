# `.github/workflows/`

One workflow: [ci.yml](ci.yml), named `biofirm-ci`. It runs on every push and
every pull request and has two jobs.

## `quality`

Matrix Python 3.11 and 3.12. Installs `uv==0.13.6`, runs `uv lock --check`,
exports the hashed requirements to `$RUNNER_TEMP/requirements.lock` and syncs
frozen. Then the test suite with a 90% coverage floor, ruff check and format
check on `src tests tools`, strict mypy on `src/biofirm`, bandit on `src tools`,
`tools/verify_repository.py`, `biofirm validate` and `biofirm validate-data`,
`python -m build`, a clean-venv install of the wheel that exercises the CLI
commands outside the checkout, and a gitleaks scan with a synthetic negative
control.

## `gnn conformance (pinned v5.0.3)`

Job key `gnn-conformance`. Fetches the revision and tag from
[../gnn-pin.json](../gnn-pin.json) out of the public upstream repository into a
fresh checkout, installs numpy, defusedxml and psutil into its own venv, and
runs `tests/test_gnn.py`. A pin that no longer resolves fails the run; the test
never silently skips when a selected checkout is missing or unusable.

Run the same steps locally as described in [../README.md](../README.md) and the
repository [AGENTS.md](../../AGENTS.md).
