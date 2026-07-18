from __future__ import annotations

from pathlib import Path

import nbformat


def test_walkthrough_notebook_executes_offline() -> None:
    notebook_path = (
        Path(__file__).parents[1] / "Documentation" / "Notebooks" / "ActInf_BioFirm_v_011.ipynb"
    )
    notebook = nbformat.read(notebook_path, as_version=4)
    namespace: dict[str, object] = {}
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        assert not any(line.lstrip().startswith(("!", "%")) for line in cell.source.splitlines())
        exec(compile(cell.source, f"{notebook_path}:{index}", "exec"), namespace)

    result = namespace["result"]
    assert result.summary["steps"] == 10  # type: ignore[attr-defined]
    assert len(result.records) == 11  # type: ignore[attr-defined]
