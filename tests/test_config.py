from __future__ import annotations

import pytest

from biofirm.config import (
    BiofirmConfig,
    ConfigError,
    ControllerConfig,
    OutputConfig,
    RelationshipConfig,
    VariableConfig,
    canonical_json,
    load_config,
)


def test_default_config_is_strict_and_serializable() -> None:
    config = load_config()
    config.validate()
    assert config.to_dict()["variables"]["biodiversity"]["maximum"] == 100.0


def test_unknown_dependency_is_rejected() -> None:
    raw = load_config().to_dict()
    raw["relationships"] = {"biodiversity": {"dependencies": {"unknown": 0.2}}}
    with pytest.raises(ConfigError, match="unknown variable"):
        type(load_config()).from_dict(raw)


def test_relationship_cycle_is_rejected() -> None:
    raw = load_config().to_dict()
    raw["relationships"] = {
        "biodiversity": {"dependencies": {"soil_moisture": 0.2}},
        "soil_moisture": {"dependencies": {"biodiversity": 0.2}},
    }
    with pytest.raises(ConfigError, match="cycles"):
        type(load_config()).from_dict(raw)


def test_invalid_bounds_are_rejected() -> None:
    raw = load_config().to_dict()
    raw["variables"]["biodiversity"]["minimum"] = 101
    with pytest.raises(ConfigError, match="minimum must be below maximum"):
        type(load_config()).from_dict(raw)


def test_required_top_level_fields_and_deep_immutability() -> None:
    raw = load_config().to_dict()
    raw.pop("name")
    with pytest.raises(ConfigError, match="name is required"):
        type(load_config()).from_dict(raw)
    config = load_config()
    with pytest.raises(TypeError):
        config.variables["new"] = config.variables["biodiversity"]  # type: ignore[index]
    with pytest.raises(TypeError):
        config.relationships["new"] = config.relationships.get("biodiversity")  # type: ignore[index]


def test_aliases_are_unique_across_variables_ignoring_case() -> None:
    raw = load_config().to_dict()
    raw["variables"]["biodiversity"]["aliases"] = ["Shared"]
    raw["variables"]["soil_moisture"]["aliases"] = ["shared"]
    with pytest.raises(ConfigError, match="shared"):
        type(load_config()).from_dict(raw)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "", "name"),
        ("unit", "", "unit"),
        ("aliases", ("",), "aliases"),
        ("minimum", 100.0, "minimum"),
        ("initial", 101.0, "initial"),
        ("target", -1.0, "target"),
        ("noise", -1.0, "noise"),
        ("control_strength", -1.0, "control_strength"),
    ],
)
def test_variable_direct_construction_rejects_invalid_values(field, value, message) -> None:  # type: ignore[no-untyped-def]
    values = dict(
        name="x",
        initial=50.0,
        target=50.0,
        minimum=0.0,
        maximum=100.0,
        aliases=(),
    )
    values[field] = value
    with pytest.raises(ConfigError, match=message):
        VariableConfig(**values)


def test_configuration_helpers_and_nested_type_errors(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    with pytest.raises(ConfigError, match="canonical JSON"):
        canonical_json({"bad": float("nan")})
    with pytest.raises(ConfigError, match="object"):
        BiofirmConfig.from_dict([])  # type: ignore[arg-type]
    with pytest.raises(ConfigError, match="controller must"):
        ControllerConfig.from_dict([])  # type: ignore[arg-type]
    with pytest.raises(ConfigError, match="output must"):
        OutputConfig.from_dict([])  # type: ignore[arg-type]
    with pytest.raises(ConfigError, match="relationship targets"):
        RelationshipConfig("", {})
    with pytest.raises(ConfigError, match="dependencies must"):
        RelationshipConfig("x", None)  # type: ignore[arg-type]
    with pytest.raises(ConfigError, match="variables must"):
        BiofirmConfig("x", None)  # type: ignore[arg-type]
    with pytest.raises(ConfigError, match="NUL"):
        OutputConfig("bad\x00path")
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid JSON"):
        load_config(bad)


def test_observation_bins_validation_and_symmetric_indexing() -> None:
    from biofirm.config import observation_index

    assert observation_index(0.0, 3) == 1
    assert observation_index(-0.1, 3) == 0
    assert observation_index(0.1, 3) == 2
    assert observation_index(0.0, 5) == 2
    assert observation_index(-0.1, 5) == 1
    assert observation_index(0.1, 5) == 3

    raw = load_config().to_dict()
    raw["variables"]["biodiversity"]["observation_bins"] = 5
    config = type(load_config()).from_dict(raw)
    assert config.variables["biodiversity"].observation_bins == 5
    raw["variables"]["biodiversity"]["observation_bins"] = 4
    with pytest.raises(ConfigError, match="observation_bins"):
        type(load_config()).from_dict(raw)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"name": "nope"}, "unknown controller"),
        ({"response_rate": 0}, "response_rate"),
        ({"damping": 1}, "damping"),
        ({"stochastic": 1}, "stochastic"),
        ({"random_seed": True}, "random_seed"),
    ],
)
def test_controller_configuration_rejects_invalid_values(kwargs, message) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ConfigError, match=message):
        ControllerConfig.from_dict(kwargs)


def test_config_parsers_reject_unknown_and_malformed_fields() -> None:
    base = load_config().to_dict()
    with pytest.raises(ConfigError, match="unknown fields"):
        VariableConfig.from_dict("x", {"unknown": 1})
    with pytest.raises(ConfigError, match="non-empty strings"):
        VariableConfig.from_dict("", {})
    with pytest.raises(ConfigError, match="aliases"):
        VariableConfig.from_dict(
            "x", {"initial": 1, "target": 1, "minimum": 0, "maximum": 2, "aliases": [1]}
        )  # type: ignore[list-item]
    with pytest.raises(ConfigError, match="unit"):
        VariableConfig.from_dict(
            "x", {"initial": 1, "target": 1, "minimum": 0, "maximum": 2, "unit": " "}
        )
    with pytest.raises(ConfigError, match="unknown fields"):
        RelationshipConfig.from_dict("x", {"extra": {}})
    with pytest.raises(ConfigError, match="object"):
        RelationshipConfig.from_dict("x", {"dependencies": []})  # type: ignore[list-item]
    with pytest.raises(ConfigError, match="unknown fields"):
        ControllerConfig.from_dict({"extra": True})
    with pytest.raises(ConfigError, match="unknown fields"):
        OutputConfig.from_dict({"extra": True})
    base.pop("variables")
    with pytest.raises(ConfigError, match="variables is required"):
        BiofirmConfig.from_dict(base)
    base = load_config().to_dict()
    base["seed"] = True
    with pytest.raises(ConfigError, match="seed"):
        BiofirmConfig.from_dict(base)
