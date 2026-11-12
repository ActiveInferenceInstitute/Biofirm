# AGENTS.md — `tests/`

- New behavior lands with a test. The coverage floor is 90% and CI enforces it.
- `conftest.py` puts `<root>/src` first on `sys.path`. Tests run from the source
  tree; do not assume an installed wheel.
- Keep tests offline. Only `test_research.py` exercises the provider path, and
  it must use a fake provider; no test may read a real `PERPLEXITY_API_KEY` or
  make a network call.
- `test_gnn.py` has two modes. With no checkout selected it skips its upstream
  half with an explicit reason; when `GNN_CHECKOUT` points at a missing or
  unusable checkout, or the `gnn` arm's `GNN_EXPORT` is unusable, it must fail,
  never skip. The `gnn conformance (pinned)` CI job provisions that checkout and
  export. Do not weaken either branch. The file does not read the pin: the
  shared `gnn.importers` reader in the `gnn` arm owns the pin and pointer.
- `test_notebook.py` executes
  [../Documentation/Notebooks/ActInf_BioFirm_v_011.ipynb](../Documentation/Notebooks/ActInf_BioFirm_v_011.ipynb)
  and asserts 10 steps and 11 records. A notebook edit that changes the run
  shape must update the assertions.
- Bandit excludes this directory, but credential patterns are still scanned by
  `tools/verify_repository.py`. Never add a realistic key, even as a fixture;
  use obviously synthetic values.
- Do not mark a test `xfail` or skip to get a red suite green. Fix the behavior
  or record a real, documented skip reason.
