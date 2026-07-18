# Biofirm current backlog

This is the sole current backlog for the repository. Completed work is recorded
in Git history; this file contains only planned work. Ignored local directories
are outside the project scope.

Priority order: P0 release and correctness gates, P1 architecture and usable
workflows, P2 documentation and repository coherence, then P3 experimental
scientific and product expansion. Every item must land with tests, documentation,
and an explicit acceptance check before it is marked complete.

## P0 — Release and correctness gates

- [ ] **BF-001 — Versioned simulation artifact contract**
  - Add `schema_version`, canonical configuration hash, configuration snapshot, controller identity, package version, seed, and validated summary metadata.
  - Strengthen result validation to enforce exact variable keys, contiguous records, finite values, recomputed summaries, valid observations/actions, and consistent diagnostics.
  - Writers always emit the new schema; legacy unversioned artifacts require explicit compatibility handling.

- [ ] **BF-002 — Research safety and provenance**
  - Fix the duplicated `Bioregion:` payload in `build_prompt`.
  - Canonicalize prompt/source hashing and add prompt-version metadata.
  - Reject arbitrary API-key exfiltration by default: official HTTPS endpoint only; custom endpoints require explicit opt-in, and insecure HTTP is never allowed for normal CLI use.
  - Validate citation URLs, response usage metadata, retry bounds, and provider response schemas.
  - Make JSON/Markdown artifact pairs resumable only when both files and their hashes agree; add a manifest for complete research runs.

- [ ] **BF-003 — Strict configuration and policy invariants**
  - Validate direct dataclass construction as strictly as `from_dict`.
  - Detect case-insensitive alias collisions, duplicate normalized names, invalid output paths, incomplete action vectors, invalid ecological effects, and unsafe committee definitions.
  - Introduce canonical JSON serialization for configuration hashing.
  - Consolidate public error types and document stable public APIs.

- [ ] **BF-004 — Packaging and CI reliability**
  - Make project version metadata single-sourced.
  - Add clean-environment wheel/sdist tests proving packaged JSON resources and CLI operation outside the checkout.
  - Keep lock/export consistency checks and add an explicit coverage floor, targeting 90% after boundary tests land.
  - Preserve Python 3.11/3.12 CI coverage and make the build gate reproducible on a clean runner.

- [ ] **BF-005 — Boundary and regression test expansion**
  - Add tests for malformed result documents, missing/extra keys, summary tampering, NaN/Infinity, partial artifacts, invalid paths, and atomic-write failures.
  - Cover visualization with one document, two documents, one feature, empty tokens, and failed saves.
  - Cover research prompt hashes, endpoint policy, tampered resume artifacts, partial JSON/Markdown pairs, retry caps, and secret non-disclosure.
  - Cover configuration aliases, direct constructors, relationships, committee ties, budget exhaustion, token-ledger conservation, and Shapley edge cases.
  - Treat the current JAX static-array warning as a regression requiring resolution or an explicit compatibility suppression test.

## P1 — Architecture, data, and usable workflows

- [ ] **BF-006 — Controller and model contract**
  - Isolate the PyMDP/JAX adapter behind a tested compatibility boundary.
  - Verify deterministic and stochastic active-inference runs, matrix dimensions, normalized beliefs/policies, action semantics, and seed behavior.
  - Make initial and transition diagnostics use one consistent schema.
  - Add a controller comparison workflow, preferably `biofirm compare`, covering active inference, slide-rule, random, and business controllers with per-seed and aggregate metrics.
  - Do not make scientific performance claims until benchmark fixtures and uncertainty reporting exist.

- [ ] **BF-007 — Source-data validation and provenance**
  - Add deterministic validation for the 185 One Earth leaf bioregions, unique IDs/names/parents, Bio_Perplexity region schemas, prompt-set structure, UTF-8/JSON validity, and stable source hashes.
  - Make `Biofirm_Regions.json` canonical and remove or explicitly mark the byte-identical `NE_Biofirm_Regions.json` after consumer verification.
  - Add provenance, licensing, source-date, and generated-versus-authoritative-data documentation.
  - Never certify research outputs merely because they passed structural validation.

- [ ] **BF-008 — Text, business, and analysis semantics**
  - Improve text extraction for multiple variables/ranges, negative values, units, sentence-local evidence, aliases, and ambiguity.
  - Preserve source spans and confidence without inventing missing measurements.
  - Clarify and test whether empirical surprise is calculated before or after posterior update.
  - Make token-ledger fields accurately describe requested, reserved, allocated, and remainder quantities.
  - Enforce complete business control vectors and deterministic tie-breaking.

- [ ] **BF-009 — CLI and API ergonomics**
  - Add structured `--help` examples and consistent output/error contracts.
  - Add `validate-data` and `compare` commands only after their schemas and tests are defined.
  - Ensure all generated artifacts are atomic, non-empty, schema-valid, and written only when explicitly requested.
  - Add stable public exports and a documented compatibility policy.

## P2 — Documentation and repository coherence

- [ ] **BF-010 — Canonical documentation**
  - Make `README.md` the authoritative installation, command, safety, artifact, and development guide.
  - Expand `Biofirm_Generative_Model.md` with the exact transition, observation, controller, reproducibility, and artifact contracts.
  - Populate or redirect the empty installation guide.
  - Turn `GNN.md` into either a real contract/design document or an explicit deferred placeholder.

- [ ] **BF-011 — Legacy-document reconciliation**
  - Mark old One Earth and Stream documents as historical design notes where they describe systems not implemented here.
  - Extract still-valid future work into this file and remove duplicate or stale active roadmaps from documentation.
  - Add a repository documentation index distinguishing implemented package behavior, source data, historical notes, and speculative research.
  - Add checks for broken local links, empty required documents, stale commands, and contradictory dependency instructions.

- [ ] **BF-012 — Executable examples and notebook validation**
  - Update the notebook to use current APIs and validate it offline in CI.
  - Add deterministic examples for simulation, analysis, visualization, text extraction, business decisions, and safe live-research invocation.
  - Keep live research out of normal tests and notebook execution.

## P3 — Ambitious future capabilities

- [ ] **BF-013 — Richer ecological model**
  - Add configurable observation bins, multi-variable observation models, richer action spaces, calibrated relationships, uncertainty propagation, and scenario configuration.
  - Extend the current model toward DPSIR only after the bounded-state contract and controller benchmarks are stable.
  - Separate illustrative simulations from empirically calibrated ecological claims.

- [ ] **BF-014 — Evidence-aware research pipeline**
  - Add structured claim/evidence records, citation validation, source freshness, provider-cost accounting, cache manifests, and human review states.
  - Support independently rerunnable acquisition, preparation, provider execution, parsing, and rendering stages.
  - Preserve raw provider responses and never substitute synthetic or fallback evidence.

- [ ] **BF-015 — Network/GNN and multi-region integration**
  - Define the data model and scientific purpose before implementing graph analytics.
  - Add regional interaction graphs only when source relationships, evaluation criteria, and provenance are explicit.
  - Keep graph/network work behind a separate experimental interface until validated.
