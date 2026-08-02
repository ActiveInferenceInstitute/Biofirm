# Biofirm docs review log — 2026-08-02

Docs-deep review pass over the Biofirm repository. Scope: documentation
structure, accuracy, consistency, and code-adjacent docs. No private material
is referenced in this log or in any committed change.

## Phase 0 — Preflight

- Branch: `main` (origin/main), fast-forward pull clean, no pre-existing
  uncommitted changes.
- HEAD before the pass: `29849e9` ("Implement roadmap features:
  observation/evidence models, research pipeline, graph contract").
- Inventory: root-level docs (`README.md`, `DOCUMENTATION_INDEX.md`,
  `Biofirm_Generative_Model.md`, `GNN.md`, `TODO.md`), `One_Earth/` (7
  historical docs + 2 JSON sources), `Bio_Perplexity/` (3 JSON sources +
  `DATA_PROVENANCE.md`), `Stream/` (3 historical/speculative docs),
  `Documentation/Notebooks/ActInf_BioFirm_v_011.ipynb`, `tools/verify_repository.py`,
  `.github/workflows/ci.yml`, `.aii/config.yaml`, `LICENSE`, `.env.example`.
- Baseline: `pytest` green (102 passed), `tools/verify_repository.py` green,
  working tree clean.

## Phase 1 — Findings

Verified accurate (no change needed):

- All 16 existing markdown files pass a scripted local-link and in-file
  anchor check; zero broken links or anchors.
- Every README command exists in the CLI (`biofirm --help`); flags match
  (`graph --regions`, `research --persona/--source/--output`, `scenarios
  --config` repeatable, etc.).
- Transition equation in README and the generative-model contract matches
  `simulation._transition` exactly, including bounded noise (±3 sigma clip).
- Schema claims are real: `RESULT_SCHEMA_VERSION = 1`, config snapshot +
  SHA-256 hash, `posterior_entropy` metric, controller identity, package
  version.
- Observation model claims are real: `observation_bins` odd >= 3, default 3
  (`config.observation_edges`), applied across observation and PyMDP matrices.
- `validate-data` really enforces 185 One Earth leaf bioregions
  (`data_validation.py`).
- Historical reconciliation is consistent: One_Earth/Stream docs carry status
  blocks and are listed as historical in the index.
- `.env.example` holds only a placeholder; `verify_repository.py` scans for
  credential patterns; no secrets in tracked files.
- Notebook uses current APIs (`load_config`, `simulate`) and is executed in
  the test suite.

### Minor (typos, formatting, stale notes)

1. Malformed nested code fence in `One_Earth/CONTRIBUTING.md` (Mermaid
   Diagrams section) — the fence opened twice and closed once.
2. `DOCUMENTATION_INDEX.md` title used sentence case while every other doc
   title uses Title Case.
3. `Stream/DPSIR.md` status note claimed DPSIR was deferred "until the
   bounded-state model … is complete", but the observation model now exists
   and DPSIR is not tracked in `TODO.md` at all.
4. `TODO.md` "Last reviewed" date was a day stale (refreshed to 2026-08-02).

### Medium (stale sections, missing docs)

5. README "Development checks" did not mirror CI: missing the 90% coverage
   floor and `ruff format --check`.
6. No current contribution guide existed; the only `CONTRIBUTING.md` is the
   historical One Earth guide. Added root-level `CONTRIBUTING.md`.
7. No configuration reference; README's Configuration section is a summary
   while the schema (`config.py`, `src/biofirm/data/ecosystem.json`) is rich.
   Added `CONFIGURATION.md` and wired it into README, the index, and the
   repository verification contract.
8. No `SECURITY.md` despite a documented security posture (offline-by-default,
   `--live` opt-in, HTTPS-only, no keys in artifacts). Added one.
9. No citation metadata. Added `CITATION.cff` grounded in the `.aii`
   manifest citation and `pyproject.toml` description.

### Major (system-level)

10. Documentation-system coherence: the index previously omitted several
    existing documents (notably `CONTRIBUTING.md` under One_Earth and the
    notebook), and the historical/current boundary, while sound, was not
    cross-linked from the new documents. Completed: index now covers every
    tracked document, README links the new docs, GNN/TODO cross-references
    verified. Historical One_Earth/Stream files were left in place and
    labelled rather than rewritten (proportionate change).

## Phase 2 — Scope

Scoped into the new "Documentation review (2026-08-02)" section of
`TODO.md` (Minor / Medium / Major tiers, each item with paths and status).

## Phase 3 — Implementation (commits)

- `118a0d0` docs: align dev checks with CI and refresh index and historical
  notes (findings 1, 2, 3).
- `222a50b` docs: add configuration reference, contributing guide, security
  policy, citation (findings 5, 6, 7, 8, 9).
- `880de08` chore: enforce CONFIGURATION.md in repository verification
  contract (finding 7 contract wiring).
- (this commit) docs: record docs review scope and log (finding 4; log).

Validation during the pass: `ruff check tools/verify_repository.py` clean;
`python tools/verify_repository.py` passes (now with the new required
document); link/anchor audit green over all 19 markdown files; `pytest`
re-run green (102 passed).

## Phase 4 — Verification and deferred items

- Full CI (Python 3.11/3.12 matrix, bandit, wheel clean-install) was not
  re-run locally; the local suite plus `verify_repository.py` passed and CI
  exercises the remainder on push. No code beyond the verification contract
  was touched.
- Deferred (scoped in TODO.md): trailing whitespace inside historical
  One_Earth mermaid diagram fences (not user-visible; churn disproportionate
  to benefit) and rewriting the speculative Stream/One_Earth prose (intended
  historical material).
