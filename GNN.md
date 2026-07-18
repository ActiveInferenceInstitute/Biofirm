# Graph and network modeling status

Graph/network modeling is intentionally deferred. The current Biofirm package
models bounded ecological variables and directed relationships, but it does not
yet define an authoritative regional interaction graph, edge provenance model,
or evaluation protocol.

Before implementing GNN or graph analytics, define:

- the graph entities, edge meanings, and source-of-truth datasets;
- provenance and uncertainty for every edge;
- baseline comparisons and acceptance metrics; and
- an experimental API that cannot be mistaken for validated ecological evidence.

See `TODO.md` BF-015 for the scoped future work.
