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
    output = tmp_path / "business.json"
    state.write_text(
        json.dumps({"biodiversity": 40, "soil_moisture": 40, "water_quality": 40}), encoding="utf-8"
    )
    assert main(["business-evaluate", "--state", str(state), "--output", str(output)]) == 0
    document = json.loads(output.read_text(encoding="utf-8"))
    assert output.stat().st_size > 0
    assert document["action"]
    assert document["rationale"]


def test_analysis_and_visualization_reject_empty_artifact(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"config_name": "x", "seed": 1, "records": []}), encoding="utf-8")
    assert main(["analyze", "--input", str(empty)]) == 2
    assert "non-empty records" in capsys.readouterr().err
    assert main(["visualize", "--input", str(empty), "--output", str(tmp_path / "plot.png")]) == 2


def test_data_validation_and_controller_comparison_cli(tmp_path) -> None:  # type: ignore[no-untyped-def]
    data_output = tmp_path / "data.json"
    comparison_output = tmp_path / "comparison.json"
    assert main(["validate-data", "--output", str(data_output)]) == 0
    assert json.loads(data_output.read_text(encoding="utf-8"))["valid"] is True
    assert (
        main(
            [
                "compare",
                "--steps",
                "1",
                "--seeds",
                "1",
                "2",
                "--controllers",
                "slide-rule",
                "random",
                "--output",
                str(comparison_output),
            ]
        )
        == 0
    )
    assert len(json.loads(comparison_output.read_text(encoding="utf-8"))["rows"]) == 4


def test_scenarios_cli(tmp_path) -> None:  # type: ignore[no-untyped-def]
    scenario_a = tmp_path / "a.json"
    scenario_b = tmp_path / "b.json"
    scenario_output = tmp_path / "scenarios.json"
    base_variable = {
        "initial": 50.0,
        "target": 50.0,
        "minimum": 0.0,
        "maximum": 100.0,
        "trend": 0.0,
        "noise": 0.5,
        "control_strength": 2.0,
        "unit": "index",
    }
    controller = {
        "name": "slide-rule",
        "stochastic": False,
        "response_rate": 0.5,
        "damping": 0.2,
    }
    scenario_a.write_text(
        json.dumps(
            {
                "name": "scenario-a",
                "seed": 7,
                "variables": {"biodiversity": dict(base_variable)},
                "controller": dict(controller),
            }
        ),
        encoding="utf-8",
    )
    scenario_b.write_text(
        json.dumps(
            {
                "name": "scenario-b",
                "seed": 8,
                "variables": {"biodiversity": dict(base_variable)},
                "controller": dict(controller),
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "scenarios",
                "--config",
                str(scenario_a),
                "--config",
                str(scenario_b),
                "--steps",
                "1",
                "--seeds",
                "1",
                "2",
                "--controller",
                "slide-rule",
                "--output",
                str(scenario_output),
            ]
        )
        == 0
    )
    report = json.loads(scenario_output.read_text(encoding="utf-8"))
    assert len(report["rows"]) == 4
    assert set(report["scenarios"]) == {"scenario-a", "scenario-b"}


def test_graph_cli(tmp_path) -> None:  # type: ignore[no-untyped-def]
    graph_output = tmp_path / "graph.json"
    assert (
        main(
            [
                "graph",
                "--regions",
                "Bio_Perplexity/Biofirm_Regions.json",
                "--label",
                "experimental",
                "--output",
                str(graph_output),
            ]
        )
        == 0
    )
    report = json.loads(graph_output.read_text(encoding="utf-8"))
    assert report["node_count"] == 67
    assert report["experimental"] is True
    assert "acceptance" in report
