# AGENTS.md — `tools/`

- [verify_repository.py](verify_repository.py) is a gate, not a convenience. CI
  runs it and a failure blocks the merge. Keep it runnable with only the
  standard library plus the package's own modules and `nbformat`.
- Do not narrow the required-document list or the link check to make a change
  pass. If a document is renamed, update both the script and the references in
  [../DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md).
- The 185-leaf assertion is a data contract, not a sample check. Change it only
  with the source data and `tests/test_data_validation.py`.
- The credential scan is a negative check. Never add a regex exception; a false
  positive means the fixture is unrealistic, not that the pattern is wrong.
- The script walks `ROOT.rglob`, so it sees new markdown automatically. Any new
  relative link must resolve from the file that contains it.
- Run `uv run python tools/verify_repository.py` from the repository root before
  pushing. There is no separate test for this script.
