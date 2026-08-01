# Graph and network modeling status

## What exists

`src/biofirm/graph.py` implements the **experimental data model and evaluation
contract** for regional graph/network work. It deliberately does not implement
a GNN or calibrated ecological analytics. Everything it returns is labelled
`experimental` and described as *descriptive topology only*, never as validated
ecological evidence.

- `RegionalNode` and `RegionalEdge` carry explicit provenance (source path) and,
  for edges, an uncertainty in `[0, 1]`, a `kind`, and a `calibrated` flag that
  is `False` until empiric validation exists.
- `nodes_from_json` builds provenance-bound nodes from either a region map
  (e.g. `Bio_Perplexity/Biofirm_Regions.json`) or a hierarchical One Earth
  source (flattened to identified leaves).
- `empty_regional_graph` / `with_candidate_edge` build immutable graphs; every
  edge references existing nodes and is rejected if it is a self-loop or lacks
  provenance.
- `descriptive_summary` returns counts, average out-degree, and unique
  undirected pairs, together with an explicit disclaimer.
- `acceptance_report` checks threshold-based protocol criteria (node/edge
  counts); it is a protocol check, not a scientific validation.
- `biofirm graph` exposes the experimental build + descriptive summary from the
  CLI.

## Not yet implemented (scoped, not validated)

Before any GNN or predictive graph analytics, the following must exist:

- an authoritative graph with edge meanings derived from a source-of-truth
  dataset (not candidate heuristics);
- provenance and uncertainty recorded for *every* edge (the model enforces
  this structurally, but no source dataset yet provides edges);
- baseline comparisons and acceptance metrics with uncertainty reporting; and
- a clearly experimental API that cannot be mistaken for validated ecological
  evidence (the current interface already enforces the `experimental` label).

See `TODO.md` for the scoped future work.
