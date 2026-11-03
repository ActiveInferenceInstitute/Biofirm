# `src/biofirm/data/`

Packaged package data. The only data file is [ecosystem.json](ecosystem.json),
the default ecosystem configuration used when no `--config` is passed.

It declares `name`, `seed`, `variables`, `relationships`, `controller` and
`output`. Each variable carries initial and target values, physical limits,
trend, noise, control strength and unit. A field-by-field reference is in
[../../../CONFIGURATION.md](../../../CONFIGURATION.md).

Because the file ships inside the wheel, offline commands work from a clean
install without any repository checkout.
