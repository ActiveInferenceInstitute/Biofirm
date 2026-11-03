# `Documentation/Notebooks/`

One notebook: [ActInf_BioFirm_v_011.ipynb](ActInf_BioFirm_v_011.ipynb).

It is a seeded, offline walkthrough of the installed package: it loads the
packaged configuration, simulates 10 steps, and leaves a `result` object in the
namespace. Live research is deliberately excluded.

`tests/test_notebook.py` executes every code cell with `exec`, rejects shell and
magic commands, and asserts the run produced 10 steps and 11 records. Bandit
excludes this directory; `tools/verify_repository.py` still scans the notebook
for `!` and `%` lines.
