# Configuration

Biofirm runs are configured by a single JSON document. The full field-by-field
reference is [`../CONFIGURATION.md`](../CONFIGURATION.md); this page covers how
configuration flows through the CLI and what an operator must supply in the
environment.

## Where configuration comes from

- **Packaged default.** With no `--config`, every command loads
  [`../src/biofirm/data/ecosystem.json`](../src/biofirm/data/ecosystem.json),
  which is also the schema example.
- **Explicit file.** Pass `--config path.json` to any command to use a
  validated file instead.
- **Multiple files.** `biofirm scenarios` accepts several `--config` flags and
  runs the same seeds across each variant.

All commands validate the same schema before running, so
`biofirm validate --config path.json` is the fastest way to check a file.

## What validation rejects

Unknown fields, non-finite numbers, invalid ranges, duplicate or
alias-colliding variable names, dependency cycles, and incomplete action
vectors. A rejected configuration raises an error and produces no empty success
artifact.

## Environment prerequisites

Configuration files carry no secrets. The only environment prerequisite is the
live-research path:

- `biofirm research --live` additionally requires `PERPLEXITY_API_KEY` in the
  environment. The default endpoint is the official HTTPS provider endpoint;
  custom endpoints require `--allow-custom-endpoint` and are intended only for
  trusted HTTPS-compatible providers. Credentials are never written into
  artifacts and never sent over insecure HTTP by the CLI.

Copy [`../.env.example`](../.env.example) as a reminder of the variable name, but
never commit a key.

## Reproducibility and output

- `seed` selects the default seed; `simulate`, `sweep`, and `scenarios` take
  `--seed`/`--seeds` on the command line.
- The canonical JSON serialization of the validated configuration is hashed
  (SHA-256) and snapshotted into every simulation artifact, so a run can be
  audited against the exact configuration that produced it.
- `output.directory` (default `artifacts`) is the directory used when a command
  writes by default, and `output.write_by_default` controls whether
  `simulate`/`sweep` write without an explicit `--output`.

## Controller

The `controller.name` selects one of `active-inference`, `slide-rule`, `random`,
or `business`. The active-inference controller builds PyMDP `A`, `B`, `C`, and
`D` matrices with JAX-compatible arrays using each variable's
`observation_bins`; the action space is the fixed three-step
decrease/hold/increase contract. See [`../CONFIGURATION.md`](../CONFIGURATION.md)
for the parameter table.

## Related

- [Configuration reference](../CONFIGURATION.md) — every key, type, and default.
- [Generative model](../Biofirm_Generative_Model.md) — what the controller and
  transition equation compute.
- [I/O and artifacts](io.md) — what a run writes and where.
