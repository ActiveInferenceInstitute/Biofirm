# `.aii/`

InstituteOS sidecar metadata for the Active Inference Institute's platform.
One file, [config.yaml](config.yaml), declares the repository name, slug, full
name, description, category, maturity, steward, ecosystem relations and tags.

It is metadata, not a build input. No command reads it and no test asserts its
contents. Keep the `full_name` and `slug` accurate if the repository moves.

The folder also carries [`readiness.json`](readiness.json): this repository's
tier, baseline commit and waivers for the organization's agent-readiness
standard. That file is read by the standard's checker, not by this project's
build, tests or CI.
