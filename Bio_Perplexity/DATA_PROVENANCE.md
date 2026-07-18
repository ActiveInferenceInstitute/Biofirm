# Source data provenance

The JSON files in this directory are authoritative source inputs for Biofirm's
regional research workflows. They are not generated simulation outputs.

`Biofirm_Regions.json` is the canonical regional map. The former
`NE_Biofirm_Regions.json` file was byte-identical to that map and had no tracked
consumer, so it was removed to prevent two names from representing one source.
`CA_Biofirm_Regions.json` is a separate, smaller regional source.

Run `biofirm validate-data` from the repository root to validate the source
schemas, the 185 One Earth leaf bioregions, prompt structure, and source hashes.
Validation establishes structural integrity only; it does not certify factual
claims, citations, or live research responses.
