# Biofirm

Biofirm is an installable Python package for reproducible ecological control,
bioregion research, deterministic text extraction, analysis, and auditable
business decisions.

## Install

Biofirm supports Python 3.11 and 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,analysis,visualization,documents]"
biofirm validate
```

For a hash-locked development environment, install `uv` and run
`uv sync --frozen --all-extras`; the committed `uv.lock` and
`requirements.lock` cover Python 3.11 and 3.12 with platform markers.

All offline commands use the packaged configuration unless `--config` is
provided. Live research is the only network-enabled path and requires both an
explicit `--live` flag and `PERPLEXITY_API_KEY` in the environment. Copy
`.env.example` as a reminder, but never put a key in a file tracked by git.

## Commands

```bash
biofirm validate
biofirm validate-data
biofirm simulate --steps 25 --seed 11 --controller active-inference --output run.json
biofirm sweep --steps 10 --seeds 1 2 3 --controller slide-rule
biofirm compare --steps 10 --seeds 1 2 3 --controllers slide-rule random
biofirm analyze --input run.json
biofirm visualize --input run.json --output artifacts/trajectory.png
biofirm parse-description --input region.txt
biofirm business-evaluate --state state.json
biofirm scenarios --config baseline.json --config disturbed.json --steps 10 --seeds 1 2 3
biofirm graph --regions Bio_Perplexity/Biofirm_Regions.json
biofirm research --live --source regions.json --persona ecologist --output artifacts/research
```

`simulate` records every transition: values, observations, controls, action
IDs, controller beliefs, variational free energy, expected free energy, policy
distributions, metrics (including a posterior-entropy uncertainty term), and
transition diagnostics. Variables can configure a symmetric observation
binning (`observation_bins`, an odd number >= 3; the default 3 preserves the
below/at/above model). Seeded runs are reproducible. New simulation artifacts
include a schema version, configuration snapshot, configuration hash,
controller identity, and package version. Invalid configuration, unavailable
optional dependencies, malformed provider responses, and failed controller
calls produce errors; they do not create empty success artifacts.

`scenarios` runs the same seeds across multiple validated ecosystem
configurations and reports per-scenario summaries plus a final-uncertainty
estimate, so scenario variants can be compared without asserting calibrated
ecological performance. `graph` builds an experimental regional interaction
graph from a region source; graph summaries and acceptance checks are
explicitly descriptive, not validated ecological evidence.

Live research writes a JSON/Markdown pair for each region/persona plus a
manifest containing integrity hashes. Every artifact records the request
hash, prompt version, source hash, a provider-cost estimate, a human review
state, and a set of structured findings extracted verbatim from the provider
response (with hedge-aware confidence). Resume is allowed only when both files,
their hashes, the prompt version/hash, and the source hash agree. Structural
validation establishes artifact integrity; it never certifies the factual
quality of citations or research claims. Research execution is split into
independently rerunnable acquire/prepare/execute/parse/render stages.

## Configuration

The packaged JSON schema is available at `src/biofirm/data/ecosystem.json`.
Each variable declares its initial and target values, physical limits, trend,
noise, control strength, and unit. Relationships are directed linear effects
between variables. Validation rejects unknown fields and dependencies,
non-finite values, invalid ranges, and cycles.

The transition equation is:

```text
next = clip(current + trend + relationship_effect + control + bounded_noise,
            minimum, maximum)
```

The active-inference controller uses the installed PyMDP 1.x API with JAX
arrays, explicit empirical priors, explicit policy inference, and deterministic
action selection unless stochastic selection is configured.

## Development checks

```bash
pytest
ruff check src tests tools
mypy --python-version 3.12 src/biofirm
bandit -q -r src tools
python tools/verify_repository.py
uv lock --check
python -m build
```

Generated research, simulation, report, plot, log, and cache files belong in
`artifacts/` or another ignored runtime directory. Authoritative source data
under `One_Earth/` and `Bio_Perplexity/` remains input data rather than a
generated output contract.

Live research requires both `--live` and `PERPLEXITY_API_KEY`. The default
endpoint is the official HTTPS provider endpoint. Custom endpoints require
`--allow-custom-endpoint` and are intended only for trusted HTTPS-compatible
providers; credentials are never sent over insecure HTTP by the CLI.

See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) for the boundary between
implemented contracts, source data, and historical design material. Current
work is scoped in [TODO.md](TODO.md); completed items remain in Git history.

Schema compatibility is explicit: consumers must validate simulation schema
version `1`, and future breaking changes require a new schema version and
migration notes. The public package exports stable configuration, simulation,
data-validation, and comparison entry points; internal modules remain
implementation details.
