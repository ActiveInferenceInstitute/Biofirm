# `One_Earth/`

Source data plus historical documentation for the One Earth biome and
ecoregion hierarchy.

## Source data

- [oneearth_bioregion_ecoregions.json](oneearth_bioregion_ecoregions.json) — the
  One Earth hierarchy. `biofirm validate-data` and
  [tools/verify_repository.py](../tools/verify_repository.py) require exactly
  185 leaf regions, with unique non-empty IDs and names.
- [OneEarth_System_Prompts.json](OneEarth_System_Prompts.json) — a `config` entry
  plus four numeric research prompts.

## Documentation

- [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) — a pointer to the repository
  [README](../README.md). It is one of the nine required documents.
- [BIOREGION_METHODOLOGY.md](BIOREGION_METHODOLOGY.md),
  [CASE_STUDIES.md](CASE_STUDIES.md), [CONTRIBUTING.md](CONTRIBUTING.md),
  [DATA_PROCESSING_PIPELINE.md](DATA_PROCESSING_PIPELINE.md),
  [ERROR_HANDLING.md](ERROR_HANDLING.md), [Next_Steps.md](Next_Steps.md) —
  historical design material, each carrying a status block. They describe a
  broader One Earth system, not the current package.
- [findings.txt](findings.txt) — a short historical pipeline run summary.

`Outputs/`, `Visualizations/`, keys and local environment files are ignored by
[.gitignore](.gitignore). This directory is not a separate installable package.
