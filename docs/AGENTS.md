# AGENTS.md — `docs/`

Read [`README.md`](README.md) first; it is the index for this folder. This file
is the editing contract for Biofirm's modular documentation.

## Purpose

`docs/` is the topical entry point for the repository's documentation. Each page
covers one subject — configuration, I/O and artifacts, the GNN specification, the
gate — and links to the authoritative document it summarizes. It does not
replace or duplicate [`documentation-index.md`](documentation-index.md)
(the repository-wide index, including historical and source-data material),
[`../CONFIGURATION.md`](../CONFIGURATION.md), or
[`../models/README.md`](../models/README.md).

## Rules

- Every markdown file here is hand-written except [`gate.md`](gate.md), which
  [`../tools/gate_report.py`](../tools/gate_report.py) generates from a real run
  of [`../run.sh`](../run.sh). Never hand-edit a measured number: refresh the
  document with `uv run python tools/gate_report.py`, and `./run.sh gate` fails
  when it no longer matches the arm list or `uv.lock`.
- Register a new page in [`documentation-index.md`](documentation-index.md)
  and link it from [`README.md`](README.md); keep the topic-per-file split (do
  not grow a single large document).
- [`../tools/verify_repository.py`](../tools/verify_repository.py) resolves every
  relative link from the file that contains it and fails CI on a broken target.
  A link that escapes the checkout has no target on the CI runner, so keep
  targets inside the repository.
- Do not restate an authoritative contract as if it were new; summarize it and
  link to it, and keep the claim boundary intact (structural validation does not
  certify calibrated ecological evidence).
- Do not add credentials, private URLs, or personal data.
- Changing a contract document at the repository root (for example
  [`../CONFIGURATION.md`](../CONFIGURATION.md) or
  [`../Biofirm_Generative_Model.md`](../Biofirm_Generative_Model.md)) means
  updating the page here that summarizes it in the same commit.

## Check before pushing

```bash
uv run python tools/verify_repository.py
```

Run it from the repository root. There is no separate test for this folder.
