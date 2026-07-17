from __future__ import annotations

import pytest

from biofirm.visualization import deterministic_tokens, visualize_documents


def test_tokenization_is_deterministic() -> None:
    assert deterministic_tokens("River, forest; RIVER!") == ["river", "forest", "river"]


def test_visualization_contract_produces_non_empty_artifact(tmp_path) -> None:  # type: ignore[no-untyped-def]
    pytest.importorskip("matplotlib")
    pytest.importorskip("sklearn")
    path = visualize_documents(
        ["river forest", "dry grassland", "coastal wetland"],
        ["water", "land", "coast"],
        tmp_path / "plot.png",
    )
    assert path.stat().st_size > 0
