# InstituteOS integration — Biofirm

## Identity

| Field | Value |
| --- | --- |
| Repository | `ActiveInferenceInstitute/Biofirm` |
| Affiliation | `institute` |
| Category | `research-software` |
| Status | `active` |
| Maturity | `released` |
| Steward | Active Inference Institute |
| Default branch | `main` |
| Current release | — |
| License | `MIT` |
| Citation | Active Inference Institute — Biofirm. |

## Federation

| Setting | Value |
| --- | --- |
| Dashboard mode | `repos` |
| Analytics | `true` |
| Dashboard | `true` |
| Sync policy | `pull` |
| Registries | — |
| Tags | biofirm, ecological-control, active-inference, python |

## Ecosystem relations

| Repository | Relation | Note |
| --- | --- | --- |
| `ActiveInferenceInstitute/InstituteOS` | `referenced-by` | Federated via the InstituteOS .aii manifest. |
| `ActiveInferenceInstitute/Active_Inference_Ontology` | `references` | Uses Active Inference Ontology terms. |
| `ActiveInferenceInstitute/pymdp` | `depends-on` | Consumes the pymdp active-inference library. |
| `ActiveInferenceInstitute/Generalized_Notation_Notation` | `references` | Uses Generalized Notation Notation (GNN) for model specifications. |

## Key artifacts

| Path | Kind | Description |
| --- | --- | --- |
| `README.md` | `doc` | Repository overview. |
| `AGENTS.md` | `doc` | Agent guidance. |
| `LICENSE` | `doc` | License. |
| `CITATION.cff` | `citation` | Machine-readable citation metadata. |
| `docs` | `doc` | Modular documentation hub (configuration, I/O, GNN). |
| `docs/documentation-index.md` | `doc` | Repository-wide documentation index. |
| `CONFIGURATION.md` | `doc` | Field-by-field configuration reference. |
| `models` | `doc` | GNN model specification and pinned upstream revision. |
| `Documentation` | `doc` | Package walkthrough notebook. |
| `tools` | `code` | Repository verification gate. |
| `pyproject.toml` | `code` | Python package configuration. |
| `src` | `code` | Source tree. |
| `tests` | `test` | Test suite. |
| `One_Earth` | `dataset` | Authoritative One Earth bioregion source data. |
| `Bio_Perplexity` | `dataset` | Authoritative regional source maps and research prompts. |

## Portable tasks

| Task | Command | Working directory | Description |
| --- | --- | --- | --- |
| `inventory` | `git ls-files` | `.` | List tracked files. |
| `test` | `./run.sh test` | `.` | Run the full test suite with the 90% coverage floor. |

## Validation

```bash
python -m aii_platform.aii_sidecar.validate <repo> --completeness
python -m aii_platform.aii_sidecar docs <repo> --overwrite
python -m aii_platform.aii_sidecar.run <repo> --list
```

The sidecar is valid when `validate` prints `OK` and reports no missing artifact,
manifest, link, or declared-doc path. Completeness is a curation target, not a
runtime requirement.

## Data boundary

This sidecar carries metadata only. It does not grant execution permission, does not
replace the repository's own documentation, and must not be used to move private
content into a public repository. Task execution is limited to trusted checkouts.
