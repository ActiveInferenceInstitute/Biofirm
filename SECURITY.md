# Security Policy

Biofirm is a research package for reproducible ecological control and
bioregion research. Its safety model is deliberately conservative: offline by
default, network access only under an explicit opt-in flag, and no
credentials in artifacts.

## Safety boundaries

- **Offline by default.** All commands except live research run without
  network access. Live research requires both an explicit `--live` flag and
  `PERPLEXITY_API_KEY` in the environment; it fails closed when either is
  missing.
- **Official endpoint only.** The default research endpoint is the official
  HTTPS provider endpoint. Custom endpoints require `--allow-custom-endpoint`
  and are intended only for trusted HTTPS-compatible providers; the CLI never
  sends credentials over insecure HTTP.
- **No keys in artifacts or git.** API keys are read from the environment
  only. `.env` is git-ignored and `.env.example` contains a placeholder.
  `tools/verify_repository.py` scans tracked files for credential patterns.
- **Provenance over trust.** Simulation artifacts carry a schema version,
  configuration snapshot, and configuration hash so consumers can validate
  the exact document they analyze. Structural validation establishes artifact
  integrity; it does not certify the factual quality of citations or research
  claims.

## Reporting a vulnerability

Please report suspected vulnerabilities privately via GitHub's private
vulnerability reporting for this repository (Security tab) rather than a
public issue. Include the affected command or module, a minimal reproduction,
and any relevant artifact. Reports are acknowledged and triaged by the
maintainers.

## Scope

The `--allow-custom-endpoint` escape hatch exists for trusted providers; any
proposal to weaken the offline-by-default or HTTPS-only guarantees should be
raised as a security discussion before implementation.

## Revoked historical credentials

The owner confirmed on 2026-10-18 that all affected historical OpenAI keys
were revoked. Four exact commit/path/rule/line fingerprints are recorded in
`.gitleaksignore`; no credential values are stored in that file. This is a
record of accepted revoked history, not a claim that history contains no
credentials or an independent verification of provider revocation. Full-history
scanning remains required. New findings, including new commits at the same
paths, still fail the gate; CI proves this with a synthetic Git-history control.
