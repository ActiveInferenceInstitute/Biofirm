from __future__ import annotations

import pytest

from biofirm.config import ConfigError, load_config


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
