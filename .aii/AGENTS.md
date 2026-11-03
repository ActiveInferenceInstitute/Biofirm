# AGENTS.md — `.aii/`

- `config.yaml` is the only file. It is hand-written InstituteOS metadata and is
  not consumed by the build, the tests or CI.
- Update `meta.updated` when you change the file. Keep `repo.full_name` matching
  the actual GitHub location and `repo.slug` matching the package name in
  [../pyproject.toml](../pyproject.toml).
- Do not add credentials or private endpoints here. This file is tracked and
  published.
- If a key's meaning is unclear, leave the existing value alone rather than
  guessing; nothing in the repository validates this schema.
