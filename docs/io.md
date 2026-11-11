# I/O and artifacts

Biofirm writes only complete, non-empty files. Two artifact families exist: the
deterministic **simulation result document** and the **live-research artifacts**
(JSON/Markdown pairs plus a manifest). Generated files belong under `artifacts/`
or another ignored runtime directory; authoritative source data under
`../One_Earth/` and `../Bio_Perplexity/` is input, never output.

## Atomic writes

[`../src/biofirm/io.py`](../src/biofirm/io.py) provides the writers used
throughout the package:

- `atomic_write_text(path, value)` writes through a same-directory temporary
  file, `fsync`s it, and atomically replaces the destination. Empty or
  non-string values raise `ArtifactError`, and an empty file after writing is
  itself an error.
- `atomic_write_json(path, value)` serializes with `allow_nan=False` and calls
  `atomic_write_text`. Non-serializable or NaN values raise `ArtifactError`.

A failed write therefore leaves the previous complete version in place rather
than a truncated file.

## Simulation result document

`simulate`, `sweep`, and `scenarios` (via `run_scenarios`) produce a
`SimulationResult` serialized by `SimulationResult.to_dict()` and validated by
`validate_result_document()` before `analyze` or `visualize` reads it.

Top-level keys (exact set, no extras):

| Key | Meaning |
| --- | --- |
| `schema_version` | Currently `1`; breaking changes require a new version and migration notes. |
| `config_name` | Configuration name; must match the embedded snapshot. |
| `config_sha256` | SHA-256 of the canonical configuration snapshot. |
| `config` | The validated configuration snapshot that produced the run. |
| `controller` | The controller actually used (raw controllers report their real identity). |
| `package_version` | Biofirm version that wrote the artifact. |
| `seed` | The integer seed. |
| `summary` | `steps`, `mean_free_energy`, `final_homeostatic_error`, `total_control_effort`. |
| `records` | One transition record per contiguous timestep. |

Each record carries the exact keys `timestep`, `values`, `observations`,
`controls`, `action_ids`, `metrics`, `beliefs`, `variational_free_energy`,
`expected_free_energy`, `policy_distributions`, and `diagnostics`. Keys are
checked against the configuration's variable set, `metrics` is exactly
`homeostatic_error`, `homeostatic_score`, `control_effort`, `bounded`, and
`posterior_entropy`, and every value must be finite. Read or write this format
through `SimulationResult`/`validate_result_document` rather than by hand.

Use it as:

```bash
biofirm simulate --steps 25 --seed 11 --controller active-inference --output run.json
biofirm analyze --input run.json
biofirm visualize --input run.json --output artifacts/trajectory.png
```

## Live-research artifacts

`biofirm research --live` writes, per region/persona, a JSON document and its
rendered Markdown companion, plus a manifest that records integrity hashes.
Each artifact records the request hash, prompt version, source hash, a
provider-cost estimate, a human review state, and structured findings extracted
verbatim from the provider response (with hedge-aware confidence).

Resume is allowed only when both files, their hashes, the prompt version and
hash, and the source hash agree. Structural validation establishes artifact
integrity; it never certifies the factual quality of citations or research
claims. Execution is split into independently rerunnable
acquire/prepare/execute/parse/render stages.

## Where outputs belong

- `artifacts/` (configurable through `output.directory`) is the default target.
- `.gitignore` excludes `artifacts/`, `outputs/`, the ignored `Outputs/` and
  `Visualizations/` subdirectories, `dist/`, caches, and `.coverage`. Do not
  commit generated output.
- The authoritative data contracts live in
  [`../CONFIGURATION.md`](../CONFIGURATION.md) (configuration) and
  [`../Biofirm_Generative_Model.md`](../Biofirm_Generative_Model.md)
  (transition/observation/controller semantics).

## Related

- [Configuration](configuration.md) — how a run is configured.
- [Generative model](../Biofirm_Generative_Model.md) — record semantics.
- [`../src/biofirm/io.py`](../src/biofirm/io.py) — the atomic writers.
