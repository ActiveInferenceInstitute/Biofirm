# AGENTS.md — `Documentation/Notebooks/`

- The notebook must run offline with no shell or magic commands. A cell line
  starting with `!` or `%` fails `tools/verify_repository.py` and
  `tests/test_notebook.py`.
- `tests/test_notebook.py` executes the cells and asserts
  `result.summary["steps"] == 10` and `len(result.records) == 11`. If you change
  the walkthrough length or shape, update that test in the same commit.
- Keep it a walkthrough of public API. Do not import private helpers, do not
  read environment variables, and do not write files outside the notebook.
- Notebooks are hand-written, not generated. Clear outputs before committing so
  the diff shows only source changes.
- A new notebook needs its own entry in
  [../../docs/documentation-index.md](../../docs/documentation-index.md) and, if the test
  suite should execute it, a test that does so.
