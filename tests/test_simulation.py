from __future__ import annotations

import pytest

from biofirm.config import load_config
from biofirm.controllers import ActiveInferenceController, RandomController, SlideRuleController
from biofirm.simulation import ResultSchemaError, simulate, validate_result_document


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
