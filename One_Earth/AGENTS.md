# AGENTS.md — `One_Earth/`

- [oneearth_bioregion_ecoregions.json](oneearth_bioregion_ecoregions.json) is
  authoritative source input with a hard contract: 185 leaf regions, unique IDs
  and names. `src/biofirm/data_validation.py` enforces the count; change data
  and the check together.
- The markdown files other than `INSTALLATION_GUIDE.md` are historical. They
  carry status blocks and must not be presented as implemented behavior or as
  evidence. Keep the status block when editing them.
- [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) is a required document checked
  by `tools/verify_repository.py`. It must stay non-empty and keep pointing at
  the repository [README](../README.md).
- Outputs belong in the ignored `Outputs/` or `Visualizations/` directories, or
  in a root-level `artifacts/` directory. Never commit generated research,
  plots or logs here.
- Do not put credentials in this tree. `.env`, `*.key` and `credentials.json` are
  ignored; a real key is never committed.
- This is not a Python package. Do not add `__init__.py` or packaging metadata.
