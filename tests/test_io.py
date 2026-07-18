from __future__ import annotations

import math

import pytest

import biofirm.io as io_module
from biofirm.io import ArtifactError, atomic_write_json, atomic_write_text


def test_atomic_artifact_writers_reject_empty_and_non_json_values(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ArtifactError, match="non-empty"):
        atomic_write_text(tmp_path / "empty.txt", "  ")
    with pytest.raises(ArtifactError, match="valid JSON"):
        atomic_write_json(tmp_path / "bad.json", {"value": math.nan})
    assert atomic_write_text(tmp_path / "ok.txt", "ok").read_text(encoding="utf-8") == "ok"


def test_atomic_text_cleans_up_when_replace_fails(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fail_replace(source, destination):  # type: ignore[no-untyped-def]
        raise OSError("replace failed")

    monkeypatch.setattr(io_module.os, "replace", fail_replace)
    with pytest.raises(ArtifactError, match="atomically write"):
        atomic_write_text(tmp_path / "failed.txt", "content")
