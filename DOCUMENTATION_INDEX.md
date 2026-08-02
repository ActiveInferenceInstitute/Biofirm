# Documentation Index

## Implemented package contracts

- [README](README.md): installation, commands, safety boundaries, and development checks.
- [Generative model](Biofirm_Generative_Model.md): transition, observation, controller, and artifact contracts.
- [Configuration reference](CONFIGURATION.md): field-by-field schema for `name`, `variables`, `relationships`, `controller`, `output`, and `seed`.
- [Installation guide](One_Earth/INSTALLATION_GUIDE.md): repository-root setup pointer.
- [Contributing](CONTRIBUTING.md): development setup, checks, and conventions.
- [Security](SECURITY.md): live-research safety boundaries and vulnerability reporting.
- [Citation](CITATION.cff): machine-readable citation metadata.
- `src/biofirm/graph.py`: experimental regional interaction graph data model with per-node/per-edge provenance and descriptive-only summaries.

## Authoritative source data

- [Source provenance](Bio_Perplexity/DATA_PROVENANCE.md)
- `Bio_Perplexity/*.json`: regional source maps and research prompts.
- `One_Earth/oneearth_bioregion_ecoregions.json`: 185-leaf One Earth hierarchy.

## Historical or speculative material

- `One_Earth/`: methodology, case studies, pipeline concepts, and historical roadmaps.
- `Stream/`: Active InferAnt discussion and explanatory material.
- [Graph/network status](GNN.md): the experimental graph data model and interface (descriptive only; not validated ecological evidence).

Historical documents may describe systems that are not implemented by the
current package. Active implementation work belongs in [TODO.md](TODO.md).
