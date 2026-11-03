# AGENTS.md — `Bio_Perplexity/`

- These JSON files are authoritative source input. Do not regenerate them from a
  run and do not treat simulation output as a replacement.
- [Biofirm_Regions.json](Biofirm_Regions.json) is the canonical regional map.
  Do not add a second file that duplicates it under another name. The former
  `NE_Biofirm_Regions.json` was removed for exactly that reason; see
  [DATA_PROVENANCE.md](DATA_PROVENANCE.md).
- After any data edit, run `uv run python tools/verify_repository.py` and
  `uv run biofirm validate-data`. Both check structure, not scientific truth.
- Do not add fetched or scraped data without recording provenance. Do not add
  credentials or API keys; the pipeline reads those from the environment only.
- Keep the counts in [README.md](README.md) accurate if records are added or
  removed.
