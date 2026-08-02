# Biofirm current backlog

Status: Open — maintained
Owner: Active Inference Institute
Last reviewed: 2026-08-02

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
  version; clean-environment wheel install + offline command exercise; lock/
  export consistency; 90% coverage floor; Python 3.11/3.12 matrix.
- **BF-005 — Boundary and regression test expansion** — Implemented and
  extended this pass with committee tie-breaking, action-ID contract, graph
  boundary, observation-bin, scenario, and evidence-pipeline coverage (102
  tests; 90% coverage). The JAX static-array warning is suppressed at the
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
  contract, installation guide, and GNN status documents are maintained and
  refreshed this pass.
- **BF-011 — Legacy-document reconciliation** — Implemented. One Earth and
  Stream documents marked historical in `DOCUMENTATION_INDEX.md`; index
  distinguishes implemented behavior, source data, historical notes, and
  speculative research; `tools/verify_repository.py` checks broken local links,
  empty required documents, stale commands, and credential patterns.
- **BF-012 — Executable examples and notebook validation** — Implemented.
  Walkthrough notebook uses current APIs and executes offline in the test
  suite; CI clean-environment job runs deterministic offline examples; live
  research stays out of normal tests.
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
- **BF-015 (delivered part) — Network/GNN data model** — Implemented the
  experimental interface: `RegionalNode`/`RegionalEdge`/`RegionalGraph` with
  per-node/per-edge provenance, uncertainty, and a `calibrated` flag;
  `nodes_from_json`; `empty_regional_graph`/`with_candidate_edge`;
  `descriptive_summary` (explicitly descriptive-only); `acceptance_report`;
  `biofirm graph`. Every output is labelled experimental and never framed as
  validated ecological evidence.

## Scoped (deferred) — future work

Substantial, intentionally unimplemented work. Any item that would assert
scientific validity requires benchmark fixtures and uncertainty reporting
before it is added.

- **BF-013 (deferred) — Multi-variable observation models and calibrated
  relationships.** Observation currently depends on one variable; relationships
  are illustrative linear coefficients. Extend observation models to depend on
  multiple variables and calibrate relationship coefficients only against an
  authoritative source with uncertainty, not as validated ecological claims.
- **BF-016 — Richer action spaces.** The action space is the fixed three-step
  decrease/hold/increase contract. Add configurable fine-grained action spaces
  with the same typed controller/validator contract, keeping backward
  compatibility and full validation.
- **BF-017 — Source-freshness and citation reachability.** Citation URLs are
  validated structurally (HTTP(S)); online freshness/reachability checking is
  not part of offline tests. Add an opt-in, clearly-labelled freshness check
  that never blocks or fabricates evidence.
- **BF-018 — GNN / predictive graph analytics.** No GNN or predictive analytics
  until an authoritative edge dataset with per-edge provenance and acceptance
  criteria exists; the experimental `graph` interface already enforces the
  `experimental` label and descriptive-only framing.

## Documentation review (2026-08-02)

Scope from the 2026-08-02 docs-deep review; the full audit is in
`REVIEW_LOG_2026-08-02.md`. Tier definitions: Minor = typo, broken link,
formatting; Medium = stale section rewrite, doc restructure, added missing
guide; Major = large doc system overhaul or cross-cutting refactor.

### Minor

- ✓ Documentation index title capitalization for consistency —
  `DOCUMENTATION_INDEX.md` (118a0d0).
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
  `tools/verify_repository.py` (118a0d0, 222a50b, 880de08).

### Major

- ✓ Documentation-system coherence pass: the index now covers every tracked
  document, README links the new guides, the historical/current boundary is
  preserved, and a scripted link/anchor audit is green over all 19 markdown
  files (118a0d0, 222a50b, 880de08, and the review-log commit).

### Open / deferred

- Trailing whitespace inside historical `One_Earth/` mermaid diagram fences
  (e.g. `Next_Steps.md`) — deferred; not user-visible and cleanup churn is
  disproportionate to benefit.
- Rewriting the speculative `Stream/` and historical `One_Earth/` prose —
  deferred by design; those documents are intentionally labelled historical.
- Full CI matrix (Python 3.11/3.12, bandit, clean wheel install) — not
  re-run locally; `pytest` (102 passed) and `tools/verify_repository.py` are
  green and CI exercises the remainder on push.
