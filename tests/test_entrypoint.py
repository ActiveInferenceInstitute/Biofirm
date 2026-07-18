from __future__ import annotations

import runpy

import pytest


def test_module_entrypoint_dispatches_to_cli(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["biofirm", "validate"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("biofirm.__main__", run_name="__main__")
    assert exc_info.value.code == 0
