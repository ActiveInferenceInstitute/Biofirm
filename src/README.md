# `src/`

Source root. It contains one package directory, [biofirm/](biofirm/README.md),
plus these two guides. No other files live at this level.

`pyproject.toml` declares `packages = ["src/biofirm"]` for the hatchling wheel,
and the package is installed with a `src` layout so imports come from the
working tree or the installed package rather than from the repository root. Put
new modules inside `src/biofirm/`, not here.
