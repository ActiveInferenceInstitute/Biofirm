# AGENTS.md — `src/biofirm/data/`

- [ecosystem.json](ecosystem.json) is packaged data, shipped in the wheel. It is
  the default configuration for every offline command.
- It is hand-written JSON, not generated. Change it here and keep
  [../../../CONFIGURATION.md](../../../CONFIGURATION.md) accurate in the same
  commit.
- Validation is strict: unknown fields, non-finite values, invalid ranges and
  relationship cycles are rejected. Run `uv run biofirm validate` and
  `uv run biofirm validate-data` after an edit.
- Variable names are part of the simulation contract. Renaming one changes
  artifact keys; treat it as a schema change.
- Do not put credentials, URLs or secrets in this file. It is published in the
  wheel and in git.
- New files here are included in the wheel by hatchling. Keep the directory to
  configuration data and its guides; no Python modules belong here.
