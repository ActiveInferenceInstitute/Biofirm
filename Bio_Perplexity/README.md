# `Bio_Perplexity/`

Authoritative source data for bioregion research. These files are inputs, not
generated simulation output.

| File | Contents |
| --- | --- |
| [Biofirm_Regions.json](Biofirm_Regions.json) | The canonical regional map: 67 regions keyed by region ID, each with `country`, `county`, `id` and `state`. |
| [CA_Biofirm_Regions.json](CA_Biofirm_Regions.json) | A three-region California subset. |
| [Biofirm_System_Prompts.json](Biofirm_System_Prompts.json) | Five research prompts under numeric keys. |
| [DATA_PROVENANCE.md](DATA_PROVENANCE.md) | Provenance notes, including why the former `NE_Biofirm_Regions.json` was removed. |

`biofirm validate-data` validates these files, and
[tools/verify_repository.py](../tools/verify_repository.py) validates them again
on every push. The canonical map has one name: `Biofirm_Regions.json`.
