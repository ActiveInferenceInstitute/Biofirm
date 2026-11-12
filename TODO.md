# Biofirm current backlog

Status: Open — maintained
Owner: Active Inference Institute
Last reviewed: 2026-11-12

This is the sole current backlog for the repository. Completed work is recorded
in an explicit "Completed/Closed" section below; the "Scoped (deferred)"
section holds the remaining large-scale work that is intentionally not
implemented yet. Ignored local directories are outside the project scope.

Priority framing: P0 release and correctness gates, P1 architecture and usable
workflows, P2 documentation and repository coherence, P3 experimental
scientific and product expansion. Every item lands with tests, documentation,
and an explicit acceptance check before it is marked complete.

## Completed/Closed

Implemented in source, tests, and CI. Preserved here for auditability; do not
re-open without evidence that their acceptance criteria regressed.

- **BF-001 — Versioned simulation artifact contract** — Implemented.
  `schema_version`, canonical configuration hash + snapshot, controller
  identity, package version, seed, validated summary; exact key sets,
  contiguous timesteps, finite values, recomputed summaries, valid
  observations/actions, and consistent diagnostics are enforced.
- **BF-002 — Research safety and provenance** — Implemented. Single
  `<bioregion>` payload; prompt/source/configuration hashing with
  prompt-version metadata; official HTTPS endpoint only, custom endpoints and
  insecure transport require explicit opt-in; citation-URL, usage, retry-bound,
  and provider-schema validation; JSON/Markdown pairs resumable only when both
  files and hashes agree, backed by a manifest. API keys never written into
  artifacts.
- **BF-003 — Strict configuration and policy invariants** — Implemented.
  Direct construction validates as strictly as `from_dict`; alias collisions,
  duplicate normalized names, incomplete action vectors, invalid effects,
  unsafe committees, and cycles rejected; canonical JSON serialization;
  consolidated public error types and documented stable exports.
- **BF-004 — Packaging and CI reliability** — Implemented. Single-sourced
  version; clean-environment wheel install + offline command exercise; a
  hash-locked requirements export derived at run time instead of a committed
  copy (`dc7967d`); 90% coverage floor; Python 3.11/3.12 matrix.
- **BF-005 — Boundary and regression test expansion** — Implemented and
  extended this pass with committee tie-breaking, action-ID contract, graph
  boundary, observation-bin, scenario, and evidence-pipeline coverage (117
  collected: 115 passed and 2 skipped without the GNN export, at 90.58%
  coverage — `docs/gate.md`). The JAX static-array warning is suppressed at the
  active-inference boundary as explicit compatibility handling.
- **BF-006 — Controller and model contract** — Implemented. PyMDP/JAX behind
  the tested `pymdp` boundary; deterministic/stochastic runs, matrix
  dimensions, normalized beliefs/policies, seed behavior validated;
  `biofirm compare` across active-inference, slide-rule, random, business.
  Raw controllers report their actual identity.
- **BF-007 — Source-data validation and provenance** — Implemented.
  `validate-data` validates the 185 One Earth leaves, unique IDs/names, region
  schemas, prompt structure, and source hashes; `NE_Biofirm_Regions.json`
  removed and recorded in `DATA_PROVENANCE.md`; structural validation is
  documented as not certifying factual quality.
- **BF-008 — Text, business, and analysis semantics** — Implemented.
  `BioregionTextProcessor` now attributes each numeric range to a single
  nearest variable, computes proximity-based confidence, and reports
  ambiguous (near-equidistant) ranges instead of guessing; negative values,
  units, aliases, and sentence-local evidence preserved. `TokenLedger` field
  semantics and the before/after posterior-update timing of `SurpriseTracker`
  empirical surprise are documented and explicitly tested.
- **BF-009 — CLI and API ergonomics** — Implemented and extended with
  `biofirm scenarios` and `biofirm graph` this pass. Structured `--help`,
  consistent JSON output/error contract (exit code 2 on failure),
  atomic non-empty artifacts, documented stable exports.
- **BF-010 — Canonical documentation** — Implemented. README, generative-model
  contract, installation guide, and graph/network status documents are
  maintained and refreshed this pass.
- **BF-011 — Legacy-document reconciliation** — Implemented. One Earth and
  Stream documents marked historical in the canonical index
  (`docs/documentation-index.md`, moved from the root `DOCUMENTATION_INDEX.md`
  in `d37852b`); the index distinguishes implemented behavior, source data,
  historical notes, and
  speculative research; `tools/verify_repository.py` checks broken local links,
  empty required documents, stale commands, and credential patterns.
- **BF-012 — Executable examples and notebook validation** — Implemented.
  Walkthrough notebook uses current APIs and executes offline in the test
  suite; the `install` arm builds the wheel and exercises the CLI in a clean
  venv outside the checkout; live research stays out of normal tests.
- **BF-013 (delivered parts) — Richer ecological model** — Implemented:
  configurable symmetric `observation_bins` (odd >= 3, default 3) generalized
  across observation, result validation, and the active-inference PyMDP
  matrices; a `posterior_entropy` uncertainty metric on every transition record;
  `run_scenarios` + `biofirm scenarios` for scenario comparison.
- **BF-014 — Evidence-aware research pipeline** — Implemented. Structured
  verbatim `ResearchFinding` claims with hedge-aware confidence; provider-cost
  estimation and per-run `cost_usd_total` in the manifest; human review states
  (`set_review_status`); independently rerunnable
  prepare/execute/build/parse/render stages. Raw provider responses are
  preserved; no synthetic or fallback evidence is introduced.
- **BF-015 (delivered part) — Network/graph data model** — Implemented the
  experimental interface: `RegionalNode`/`RegionalEdge`/`RegionalGraph` with
  per-node/per-edge provenance, uncertainty, and a `calibrated` flag;
  `nodes_from_json`; `empty_regional_graph`/`with_candidate_edge`;
  `descriptive_summary` (explicitly descriptive-only); `acceptance_report`;
  `biofirm graph`. Every output is labelled experimental and never framed as
  validated ecological evidence.
- **BF-019 — Generalized Notation Notation generative-model specification** —
  Implemented. `models/biofirm_ecosystem_variable.gnn.md` is the structural
  source of truth for the active-inference controller's generative model (one
  bounded factor, one identity-likelihood modality, the three
  decrease/hold/increase controls, target-peaked preferences, uniform prior,
  clipped shift transition); `src/biofirm/gnn.py` parses it without upstream
  dependencies and reports conformance; `tests/test_gnn.py` compares the
  declared matrices with `build_active_inference_matrices` for the default and
  generalized bin counts and re-validates the file with the pinned upstream
  parser (`--strict`) from a clean export of the pinned revision. The pin
  (v5.1.0, `75c834bd8519dc7b5adc4d24f16bf393cfd1ecdf`) is recorded in
  `.github/gnn-pin.json` and read by the shared `gnn.importers` reader in
  `./run.sh gnn`; the former `GNN.md` graph/network document is renamed
  `GRAPH_MODELING.md` so "GNN" unambiguously means Generalized Notation
  Notation in this repository.
- **BF-020 — Dependency currency review** — Implemented. Each runtime pin in
  `pyproject.toml` is the newest release that satisfies both supported Python
  versions (3.11 and 3.12) together with `inferactively-pymdp==1.0.5`, so the
  pins are qualified values rather than stale freezes: `numpy` 2.5.x and `jax`
  0.11.0 both require Python >= 3.12. The
  rationale and the recheck commands are documented in `CONTRIBUTING.md`.
  `pytest` moved from 9.1.1 to 9.2.0, and the CI tool pin moved from
  `uv==0.11.6` to `uv==0.13.6` after the regenerated `requirements.lock` diffed
  identical under the newer tool; that export is now git-ignored and produced
  by the `install` arm (`dc7967d`). `inferactively-pymdp` moved from 1.0.4 to
  1.0.5 in #38 (`27e7e40`), which also removed the `jax<0.11.1` cap from the
  rationale. Acceptance: the documented check list passes (`./run.sh test`
  with the 90% coverage floor, `./run.sh lint`, `./run.sh types`,
  `./run.sh bandit`, `./run.sh links`, `uv lock --check`, the `install` arm's
  hashed export, and `python -m build`).
- **BF-021 — Single gate entry point and measured arms** — Implemented.
  `run.sh` is the only entry point: `ci.yml` calls its arms and nothing else,
  and each arm is independent. `docs/gate.md` records the arms, their measured
  wall times, the full-suite test count and coverage, and the environment; it
  is generated by `tools/gate_report.py` and checked by `./run.sh gate`. The
  pre-gate CI commands are preserved as a receipt in
  `tools/gate_baseline.json` at `c88b5d3` and rendered before/after (#34, #35).
- **BF-022 — Pinned GNN conformance in CI and the canonical pin schema** —
  Implemented. A dedicated `gnn conformance (pinned)` job (renamed to a stable
  name in #24) runs `./run.sh gnn` on every push and pull request (#15); the
  arm runs the shared `gnn.importers` reader with `--require-pointer` (#36),
  which validates the conformance pointer added in #26, and the revision's
  parser against a clean export. `.github/gnn-pin.json` uses the
  shared `gnn-importer-pin/v1` schema (#33), and the arm refuses a pinned tag
  that does not dereference to the pinned revision (#37).
- **BF-023 — Documentation hub and folder guides** — Implemented. `docs/`
  is the topical entry point: `README`, `configuration.md`, `io.md`, and
  `gnn.md` (`1d3f2bc`), `gate.md` (#34), and `documentation-index.md`
  (`d37852b`). Folder-level `README`/`AGENTS` guides cover the tracked source,
  data, documentation, and test directories (#22). The canonical index moved
  from the root `DOCUMENTATION_INDEX.md` to `docs/documentation-index.md`, and
  `tools/verify_repository.py` now requires the new path (`d37852b`).
- **BF-024 — Dependency security and automation maintenance** — Implemented.
  Patched cryptography, Pillow, certifi, and urllib3 releases are resolved
  under qualified locks kept synchronized by `uv lock --check` and the
  `install` arm's hashed export (#9, #12); the secret-scan
  arm runs gitleaks directly instead of the licensed Action wrapper, with the
  four owner-confirmed revoked historical findings accounted for (`5bdccaf`,
  `143759f`); Actions are pinned to immutable SHAs and Dependabot watches the
  `uv` and `actions` ecosystems (#13, #14).

## Scoped (deferred) — future work

Substantial, intentionally unimplemented work. Any item that would assert
scientific validity requires benchmark fixtures and uncertainty reporting
before it is added.

- **BF-013 (deferred) — Multi-variable observation models and calibrated
  relationships.** Observation currently depends on one variable; relationships
  are illustrative linear coefficients. Extend observation models to depend on
  multiple variables and calibrate relationship coefficients only against an
  authoritative source with uncertainty, not as validated ecological claims.
  Blocked on an authoritative calibrated dataset with per-coefficient
  uncertainty; no such dataset, and no owner for it, is in this repository
  (external).
- **BF-016 — Richer action spaces.** The action space is the fixed three-step
  decrease/hold/increase contract. Add configurable fine-grained action spaces
  with the same typed controller/validator contract, keeping backward
  compatibility and full validation. Unblocked by a maintainer decision on the
  action-space schema; no external dependency.
- **BF-017 — Source-freshness and citation reachability.** Citation URLs are
  validated structurally (HTTP(S)); online freshness/reachability checking is
  not part of offline tests. Add an opt-in, clearly-labelled freshness check
  that never blocks or fabricates evidence. Blocked on an opt-in networking
  arm: the maintainer who adds that arm to `run.sh` owns it, and it must stay
  out of the offline gate.
- **BF-018 — Graph-neural-network / predictive graph analytics.** No graph
  neural network or predictive analytics
  until an authoritative edge dataset with per-edge provenance and acceptance
  criteria exists; the experimental `graph` interface already enforces the
  `experimental` label and descriptive-only framing. Blocked on that dataset
  (external); no owner in this repository.
- **BF-025 — Python 3.12-only floor.** `requires-python` is `>=3.11,<3.13`, so
  the newest `numpy` 2.5.x and `jax` >= 0.11.0 stay excluded and BF-020's pins
  are qualified rather than current. Adopting a 3.12-only floor would unlock
  them and drop the 3.11 matrix leg. Blocked on a maintainer decision about
  3.11 support; no external dependency.

## Documentation review (2026-08-02)

Scope from the 2026-08-02 docs-deep review; the full audit is in
`REVIEW_LOG_2026-08-02.md`. Tier definitions: Minor = typo, broken link,
formatting; Medium = stale section rewrite, doc restructure, added missing
guide; Major = large doc system overhaul or cross-cutting refactor.

### Minor

- ✓ Documentation index title capitalization for consistency —
  `DOCUMENTATION_INDEX.md` (118a0d0; now `docs/documentation-index.md` after
  `d37852b`).
- ✓ Malformed nested code fence in the historical contribution guide —
  `One_Earth/CONTRIBUTING.md` (118a0d0).
- ✓ Stale status note in the speculative DPSIR design note —
  `Stream/DPSIR.md` (118a0d0).

### Medium

- ✓ README development checks now mirror the CI quality job exactly
  (coverage floor plus `ruff format --check`) — `README.md` (118a0d0).
- ✓ Added a full field-by-field configuration reference (new) —
  `CONFIGURATION.md` (222a50b).
- ✓ Added a current contribution guide for the package (new; the only prior
  guide was historical) — `CONTRIBUTING.md` (222a50b).
- ✓ Added a concise security policy (new) — `SECURITY.md` (222a50b).
- ✓ Added machine-readable citation metadata (new) — `CITATION.cff`
  (222a50b).
- ✓ Wired the new documents into the index and the repository verification
  contract — `README.md`, `DOCUMENTATION_INDEX.md`,
  `tools/verify_repository.py` (118a0d0, 222a50b, 880de08; the index is now
  `docs/documentation-index.md`, required by `tools/verify_repository.py` since
  `d37852b`).

### Major

- ✓ Documentation-system coherence pass: the index now covers every tracked
  document, README links the new guides, the historical/current boundary is
  preserved, and a scripted link/anchor audit is green over all 19 markdown
  files (118a0d0, 222a50b, 880de08, and the review-log commit).

### Open / deferred

- Rewriting the speculative `Stream/` and historical `One_Earth/` prose —
  deferred by design; those documents are intentionally labelled historical
  (owner: maintainer; no external dependency).
- GitHub-hosted CI evidence — GitHub Actions is billing-locked org-wide, so no
  hosted run exists for any job in `ci.yml`; a hosted run must not be treated
  as evidence. Every gated check is reproducible locally as an arm of
  `./run.sh`, and that local evidence is the only current evidence. Not done
  until the org restores Actions billing (owner: Active Inference Institute
  org admin).

### Follow-up (2026-08-02) — previously deferred items closed

- ✓ Trailing whitespace stripped from historical/speculative markdown —
  `One_Earth/Next_Steps.md`, `Stream/DPSIR.md`, `Stream/InferAnt_Stream_006.md`
  (73e714d; verified whitespace-only diff).
- ✓ `Stream/Casey_At_Bat.md` labelled as historical creative material,
  matching the repo's historical-labelling convention (73e714d).
- ✓ The package walkthrough notebook is now listed in the documentation index
  so every tracked document is covered (73e714d).
- ✓ CI parity executed locally: `uv lock --check` and the `requirements.lock`
  export diff pass; `python -m build` produces the wheel; the CI
  clean-environment job (locked install + wheel install + offline command
  exercise) passes on Python 3.11.15 and 3.12.13; `pytest` passes 102/102
  under both interpreters; ruff check + format, mypy, bandit, and
  `tools/verify_repository.py` are green under the clean environment.
  Full detail in `REVIEW_LOG_2026-08-02.md`.
