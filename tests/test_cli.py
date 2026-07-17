from __future__ import annotations

import json

from biofirm.cli import main


def test_offline_cli_commands(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["validate"]) == 0
    run_path = tmp_path / "run.json"
    assert (
        main(
            [
                "simulate",
                "--steps",
                "2",
                "--seed",
                "4",
                "--controller",
                "slide-rule",
                "--output",
                str(run_path),
            ]
        )
        == 0
    )
    assert main(["analyze", "--input", str(run_path)]) == 0
    assert main(["sweep", "--steps", "1", "--seeds", "1", "2", "--controller", "random"]) == 0
    text_path = tmp_path / "region.txt"
    text_path.write_text(
        "A wetland supports biodiversity between 10 and 90 index.", encoding="utf-8"
    )
    assert main(["parse-description", "--input", str(text_path)]) == 0
    output = capsys.readouterr().out
    assert "valid" in output
    assert "source_sha256" in output


def test_business_cli(tmp_path) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps({"biodiversity": 40, "soil_moisture": 40, "water_quality": 40}), encoding="utf-8"
    )
    assert main(["business-evaluate", "--state", str(state)]) == 0


def test_analysis_and_visualization_reject_empty_artifact(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"config_name": "x", "seed": 1, "records": []}), encoding="utf-8")
    assert main(["analyze", "--input", str(empty)]) == 2
    assert "non-empty records" in capsys.readouterr().err
    assert main(["visualize", "--input", str(empty), "--output", str(tmp_path / "plot.png")]) == 2
