# `tools/`

One script: [verify_repository.py](verify_repository.py). It is the
repository-level contract check and runs in CI as the "Syntax and import scan"
step.

From the repository root:

```bash
uv run python tools/verify_repository.py
```

It fails, with a message naming the file, when any of these do not hold:

- `src` compiles with `compileall`.
- `biofirm` imports and `biofirm.__version__` is non-empty.
- The nine required documents exist and are non-empty: `README.md`,
  `Biofirm_Generative_Model.md`, `CONFIGURATION.md`, `TODO.md`,
  `DOCUMENTATION_INDEX.md`, `One_Earth/INSTALLATION_GUIDE.md`,
  `GRAPH_MODELING.md`, `models/README.md`, and
  `models/biofirm_ecosystem_variable.gnn.md`.
- Every relative markdown link under the repository resolves.
- `One_Earth/oneearth_bioregion_ecoregions.json` has exactly 185 leaf regions
  with unique non-empty IDs and names, and the region and prompt files match
  their schemas.
- No notebook code cell starts a line with `!` or `%`.
- No text file outside the skipped directories matches a credential pattern.

It skips `.git`, `.venv`, `artifacts`, `Outputs`, `Visualizations` and
`__pycache__`.
