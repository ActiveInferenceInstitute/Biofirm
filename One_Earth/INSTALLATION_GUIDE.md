# Biofirm installation guide

The maintained installation and development instructions are in the repository
[README](../README.md). From the repository root, use a locked environment:

```bash
uv sync --frozen --all-extras
uv run biofirm validate
uv run biofirm validate-data
```

This directory contains One Earth source data and historical design material;
it is not a separate installable Python package.
