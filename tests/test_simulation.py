from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping
from pathlib import Path

import pytest

from biofirm.config import BiofirmConfig, load_config
from biofirm.controllers import (
    ActiveInferenceController,
    ControlDecision,
    RandomController,
    SlideRuleController,
)
from biofirm.simulation import (
    ResultSchemaError,
    SimulationError,
    SimulationResult,
    compare_controllers,
    run_scenarios,
    simulate,
    validate_result_document,
    write_result,
)


def test_seeded_slide_rule_run_is_reproducible_and_bounded() -> None:
    config = load_config()
    first = simulate(config, steps=6, seed=22, controller_name="slide-rule")
    second = simulate(config, steps=6, seed=22, controller_name="slide-rule")
    assert first.to_dict() == second.to_dict()
    for record in first.records:
        for name, value in record.values.items():
            variable = config.variables[name]
            assert variable.minimum <= value <= variable.maximum
            assert name in record.observations
            assert name in record.controls


def test_all_controller_types_make_real_decisions() -> None:
    config = load_config()
    assert isinstance(
        SlideRuleController(config).act({name: 45.0 for name in config.variables}), object
    )
    random_decision = RandomController(config, seed=2).act(
        {name: 50.0 for name in config.variables}
    )
    active_decision = ActiveInferenceController(config, seed=2).act(
        {name: 45.0 for name in config.variables}
    )
    assert set(random_decision.controls) == set(config.variables)
    assert set(active_decision.beliefs) == set(config.variables)
    assert all(len(belief) == 3 for belief in active_decision.beliefs.values())


def test_relationship_and_trend_effects_are_recorded() -> None:
    raw = load_config().to_dict()
    raw["variables"]["soil_moisture"]["trend"] = 1.0
    raw["variables"]["biodiversity"]["noise"] = 0.0
    raw["variables"]["soil_moisture"]["noise"] = 0.0
    config = type(load_config()).from_dict(raw)
    result = simulate(config, steps=1, seed=1, controller_name="slide-rule")
    assert result.records[1].diagnostics["soil_moisture.trend"] == 1.0
    assert "biodiversity.relationship" in result.records[1].diagnostics


def test_business_controller_executes_with_full_control_vector() -> None:
    config = load_config()
    result = simulate(config, steps=2, seed=5, controller_name="business")
    assert len(result.records) == 3
    assert all(set(record.controls) == set(config.variables) for record in result.records)


def test_result_schema_rejects_empty_success_documents() -> None:
    with pytest.raises(ResultSchemaError, match="non-empty records"):
        validate_result_document({"config_name": "x", "seed": 1, "records": []})


def test_result_history_is_deeply_immutable() -> None:
    result = simulate(load_config(), steps=1, seed=3, controller_name="random")
    with pytest.raises(TypeError):
        result.records[0].values["biodiversity"] = 1.0  # type: ignore[index]
    assert isinstance(result.records, tuple)


def test_result_document_contains_identity_and_rejects_tampering() -> None:
    document = simulate(load_config(), steps=1, seed=3, controller_name="slide-rule").to_dict()
    assert document["schema_version"] == 1
    assert len(document["config_sha256"]) == 64
    validate_result_document(document)

    active_document = simulate(
        load_config(), steps=1, seed=3, controller_name="active-inference"
    ).to_dict()
    validate_result_document(active_document)

    changed_summary = {**document, "summary": {**document["summary"], "steps": 999.0}}
    with pytest.raises(ResultSchemaError, match="summary does not match"):
        validate_result_document(changed_summary)

    changed_record = {**document, "records": [dict(record) for record in document["records"]]}
    changed_record["records"][1]["values"] = dict(changed_record["records"][1]["values"])
    changed_record["records"][1]["values"].pop("biodiversity")
    with pytest.raises(ResultSchemaError, match="inconsistent values keys"):
        validate_result_document(changed_record)

    with pytest.raises(ResultSchemaError, match="top-level fields"):
        validate_result_document({**document, "extra": True})
    changed_record["records"][0]["unexpected"] = True
    with pytest.raises(ResultSchemaError, match="unexpected fields"):
        validate_result_document(changed_record)

    changed_metrics = copy.deepcopy(document)
    changed_metrics["records"][0]["metrics"]["homeostatic_error"] = 1.0
    with pytest.raises(ResultSchemaError, match="inconsistent metrics"):
        validate_result_document(changed_metrics)

    changed_distribution = copy.deepcopy(active_document)
    changed_distribution["records"][1]["beliefs"]["biodiversity"] = [2.0, 0.0, 0.0]
    with pytest.raises(ResultSchemaError, match="unnormalized beliefs"):
        validate_result_document(changed_distribution)


def test_controller_comparison_is_seeded_and_aggregated() -> None:
    report = compare_controllers(
        load_config(), steps=1, seeds=[1, 2], controllers=["slide-rule", "random"]
    )
    assert report["schema_version"] == 1
    assert len(report["rows"]) == 4
    assert set(report["aggregates"]) == {"slide-rule", "random"}


def test_simulation_identity_reports_actual_controllers() -> None:
    config = load_config()
    default_result = simulate(config, steps=1, seed=1)
    assert default_result.controller == config.controller.name
    raw_result = simulate(config, steps=2, seed=1, controller=RandomController(config, seed=1))
    assert raw_result.controller == "random"


def test_simulation_and_comparison_reject_invalid_inputs() -> None:
    config = load_config()
    with pytest.raises(SimulationError, match="steps"):
        simulate(config, steps=-1)
    with pytest.raises(SimulationError, match="seed"):
        simulate(config, seed=True)  # type: ignore[arg-type]
    with pytest.raises(SimulationError, match="controllers"):
        compare_controllers(config, 1, [1], [])
    with pytest.raises(SimulationError, match="controllers"):
        compare_controllers(config, 1, [1], ["slide-rule", "slide-rule"])


def test_result_validator_rejects_invalid_schema_fields() -> None:
    document = simulate(load_config(), steps=1, seed=3, controller_name="slide-rule").to_dict()
    cases = [
        ({"schema_version": 2}, "schema_version"),
        ({"config_sha256": "bad"}, "configuration hash"),
        ({"controller": ""}, "controller"),
        ({"package_version": ""}, "package_version"),
    ]
    for changes, message in cases:
        changed = {**document, **changes}
        with pytest.raises(ResultSchemaError, match=message):
            validate_result_document(changed)

    field_cases = [
        ("values", {}, "empty values"),
        ("observations", {}, "empty observations"),
        ("controls", {}, "empty controls"),
        ("action_ids", {}, "empty action_ids"),
        ("metrics", {}, "empty metrics"),
        ("beliefs", [], "invalid beliefs"),
        ("diagnostics", {"wrong": 0.0}, "inconsistent diagnostics"),
        ("observations", {"biodiversity": 99}, "invalid observations"),
        ("action_ids", {"biodiversity": 99}, "invalid action_ids"),
    ]
    for field_name, value, message in field_cases:
        changed = copy.deepcopy(document)
        if field_name in {"observations", "action_ids"} and value:
            value = {
                name: next(iter(value.values())) for name in document["records"][0][field_name]
            }
        changed["records"][0][field_name] = value
        with pytest.raises(ResultSchemaError, match=message):
            validate_result_document(changed)


def test_result_validator_rejects_malformed_records() -> None:
    document = simulate(load_config(), steps=1, seed=3, controller_name="slide-rule").to_dict()
    cases = [
        ({"config": {}}, "invalid configuration"),
        ({"config_name": "wrong"}, "does not match"),
        ({"summary": []}, "summary"),
        ({"records": [{"timestep": 0}]}, "missing required"),
    ]
    for changes, message in cases:
        changed = {**document, **changes}
        with pytest.raises(ResultSchemaError, match=message):
            validate_result_document(changed)


def test_run_scenarios_compares_variants_and_reports_uncertainty() -> None:
    variant = {**load_config().to_dict(), "name": "disturbed", "seed": 9}
    report = run_scenarios(
        [load_config(), type(load_config()).from_dict(variant)],
        2,
        [1, 2],
        controller_name="slide-rule",
    )
    assert report["schema_version"] == 1
    assert len(report["rows"]) == 4
    assert set(report["scenarios"]) == {"biofirm-default-ecosystem", "disturbed"}
    assert "final_uncertainty" in report["rows"][0]
    with pytest.raises(SimulationError, match="scenario"):
        run_scenarios([], 1, [1])
    duplicate = [load_config(), load_config()]
    with pytest.raises(SimulationError, match="unique"):
        run_scenarios(duplicate, 1, [1])


def test_five_bin_observation_contract_and_uncertainty_metric() -> None:
    raw = load_config().to_dict()
    raw["variables"]["biodiversity"]["observation_bins"] = 5
    config = type(load_config()).from_dict(raw)
    result = simulate(config, steps=2, seed=1, controller_name="slide-rule")
    document = result.to_dict()
    validate_result_document(document)
    for record in result.records:
        assert 0 <= record.observations["biodiversity"] < 5
        assert "posterior_entropy" in record.metrics
    assert result.records[0].metrics["posterior_entropy"] == 0.0
    active = simulate(config, steps=2, seed=3, controller_name="active-inference")
    assert len(active.records[1].beliefs["biodiversity"]) == 5
    validate_result_document(active.to_dict())


def test_simulation_result_constructor_and_controller_contracts_fail_closed() -> None:
    config = load_config()
    record = simulate(config, steps=0, controller_name="slide-rule").records[0]
    with pytest.raises(SimulationError, match="schema version"):
        SimulationResult("x", 1, (record,), schema_version=2)
    with pytest.raises(SimulationError, match="transition records"):
        SimulationResult("x", 1, ())
    with pytest.raises(SimulationError, match="configuration snapshot"):
        write_result(SimulationResult("x", 1, (record,)), "invalid-result.json")

    class BadController:
        def reset(self, seed: int) -> None:
            del seed

        def act(self, values):  # type: ignore[no-untyped-def]
            del values
            from biofirm.controllers import ControlDecision

            return ControlDecision(controls={}, action_ids={})

    with pytest.raises(SimulationError, match="exactly"):
        simulate(config, steps=1, controller=BadController())  # type: ignore[arg-type]


def _single_variable_config(**overrides: float) -> BiofirmConfig:
    variable = {
        "initial": 5.0,
        "target": 5.0,
        "minimum": 0.0,
        "maximum": 10.0,
        "trend": 0.5,
        "noise": 0.0,
        "control_strength": 0.5,
    }
    variable.update(overrides)
    return BiofirmConfig.from_dict({"name": "artifact-validation", "variables": {"x": variable}})


@pytest.mark.parametrize("noise", [0.0, 0.2])
def test_result_validator_rejects_noise_outside_three_sigma(noise: float) -> None:
    document = simulate(
        _single_variable_config(noise=noise), steps=1, seed=3, controller_name="slide-rule"
    ).to_dict()
    document["records"][1]["diagnostics"]["x.noise"] = (
        1e-300 if noise == 0.0 else 3.0 * noise + 0.1
    )
    with pytest.raises(ResultSchemaError, match="out-of-bounds diagnostics"):
        validate_result_document(document)


def test_result_validator_rejects_unreconstructable_transition() -> None:
    document = simulate(
        _single_variable_config(), steps=1, seed=3, controller_name="slide-rule"
    ).to_dict()
    record = document["records"][1]
    record["values"]["x"] = 6.0
    record["observations"]["x"] = 2
    record["metrics"]["homeostatic_error"] = 0.1
    record["metrics"]["homeostatic_score"] = 0.9
    document["summary"]["final_homeostatic_error"] = 0.1
    with pytest.raises(ResultSchemaError, match="inconsistent transition"):
        validate_result_document(document)


@pytest.mark.parametrize("component", ["values", "controls"])
def test_result_validator_rejects_inconsistent_initial_record(component: str) -> None:
    document = simulate(
        _single_variable_config(), steps=0, controller_name="slide-rule"
    ).to_dict()
    record = document["records"][0]
    if component == "values":
        record["values"]["x"] = 6.0
        record["observations"]["x"] = 2
        record["metrics"]["homeostatic_error"] = 0.1
        record["metrics"]["homeostatic_score"] = 0.9
        document["summary"]["final_homeostatic_error"] = 0.1
    else:
        record["controls"]["x"] = 0.25
        record["action_ids"]["x"] = 2
        record["metrics"]["control_effort"] = 0.25
        document["summary"]["total_control_effort"] = 0.25
    with pytest.raises(ResultSchemaError, match=f"inconsistent initial {component}"):
        validate_result_document(document)


@pytest.mark.parametrize("entropy", [-1.0, 0.0, math.log(2.0) + 0.25])
def test_result_validator_recomputes_posterior_entropy(entropy: float) -> None:
    document = simulate(
        _single_variable_config(), steps=1, seed=3, controller_name="slide-rule"
    ).to_dict()
    record = document["records"][1]
    record["beliefs"]["x"] = [0.5, 0.5, 0.0]
    record["metrics"]["posterior_entropy"] = entropy
    with pytest.raises(ResultSchemaError, match="inconsistent metrics"):
        validate_result_document(document)


@pytest.mark.parametrize(("initial", "trend", "expected"), [(9.0, 3.0, 10.0), (1.0, -3.0, 0.0)])
def test_clipped_transition_artifacts_round_trip(
    tmp_path: Path, initial: float, trend: float, expected: float
) -> None:
    result = simulate(
        _single_variable_config(initial=initial, target=initial, trend=trend),
        steps=1,
        controller_name="slide-rule",
    )
    path = write_result(result, tmp_path / "clipped.json")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["records"][1]["values"]["x"] == expected
    assert document["records"][1]["diagnostics"]["x.trend"] == trend
    assert document == result.to_dict()


@pytest.mark.parametrize("controller_name", ["slide-rule", "random", "active-inference", "business"])
@pytest.mark.parametrize("control_strength", [0.0, 1e-13, 1e-12])
def test_zero_strength_action_contract_round_trips(
    tmp_path: Path, controller_name: str, control_strength: float
) -> None:
    raw = load_config().to_dict()
    for variable in raw["variables"].values():
        variable["control_strength"] = control_strength
    config = BiofirmConfig.from_dict(raw)
    result = simulate(config, steps=2, seed=2, controller_name=controller_name)
    for record in result.records:
        assert all(abs(control) <= control_strength for control in record.controls.values())
        assert all(action == 1 for action in record.action_ids.values())
    path = write_result(result, tmp_path / "zero-strength.json")
    assert json.loads(path.read_text(encoding="utf-8")) == result.to_dict()


@pytest.mark.parametrize(
    ("control", "action", "message"),
    [
        (0.0, 0, "inconsistent action"),
        (0.0, 2, "inconsistent action"),
        (1e-13, 2, "inconsistent action"),
        (-1e-13, 0, "inconsistent action"),
        (0.25, 0, "inconsistent action"),
        (-0.25, 2, "inconsistent action"),
        (float("nan"), 1, "invalid control"),
        (float("inf"), 2, "invalid control"),
        (0.6, 2, "invalid control"),
    ],
)
def test_simulate_rejects_inconsistent_decision_before_success(
    control: float, action: int, message: str
) -> None:
    class FixedController:
        def reset(self, seed: int) -> None:
            del seed

        def act(self, values: Mapping[str, float]) -> ControlDecision:
            return ControlDecision(
                controls={name: control for name in values},
                action_ids={name: action for name in values},
            )

    with pytest.raises(SimulationError, match=message):
        simulate(_single_variable_config(), steps=1, controller=FixedController())
