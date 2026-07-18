"""Typed configuration and strict validation for Biofirm runs."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any


class ConfigError(ValueError):
    """Raised when a configuration cannot describe a valid ecosystem."""


def canonical_json(value: Any) -> str:
    """Serialize JSON data deterministically without accepting non-finite numbers."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError("value cannot be represented as canonical JSON") from exc


def sha256_json(value: Any) -> str:
    """Return the SHA-256 digest of canonical JSON data."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ConfigError(f"{name} must be finite")
    return result


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{name} must be an object")
    return value


@dataclass(frozen=True)
class VariableConfig:
    """A bounded state variable and its transition parameters."""

    name: str
    initial: float
    target: float
    minimum: float
    maximum: float
    trend: float = 0.0
    noise: float = 0.0
    control_strength: float = 1.0
    unit: str = "index"
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_dict(cls, name: str, raw: Mapping[str, Any]) -> VariableConfig:
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("variable names must be non-empty strings")
        allowed = {
            "initial",
            "target",
            "minimum",
            "maximum",
            "trend",
            "noise",
            "control_strength",
            "unit",
            "aliases",
        }
        unknown = set(raw) - allowed
        if unknown:
            raise ConfigError(f"variable {name!r} has unknown fields: {sorted(unknown)}")
        aliases = raw.get("aliases", ())
        if not isinstance(aliases, (list, tuple)) or not all(isinstance(a, str) for a in aliases):
            raise ConfigError(f"variable {name!r}.aliases must be a list of strings")
        unit = raw.get("unit", "index")
        if not isinstance(unit, str) or not unit.strip():
            raise ConfigError(f"variables.{name}.unit must be a non-empty string")
        if len(set(aliases)) != len(aliases):
            raise ConfigError(f"variables.{name}.aliases must be unique")
        return cls(
            name=name,
            initial=_finite(raw.get("initial"), f"variables.{name}.initial"),
            target=_finite(raw.get("target"), f"variables.{name}.target"),
            minimum=_finite(raw.get("minimum"), f"variables.{name}.minimum"),
            maximum=_finite(raw.get("maximum"), f"variables.{name}.maximum"),
            trend=_finite(raw.get("trend", 0.0), f"variables.{name}.trend"),
            noise=_finite(raw.get("noise", 0.0), f"variables.{name}.noise"),
            control_strength=_finite(
                raw.get("control_strength", 1.0), f"variables.{name}.control_strength"
            ),
            unit=unit,
            aliases=tuple(aliases),
        )

    def validate(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigError("variable names cannot be empty")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ConfigError(f"variables.{self.name}.unit cannot be empty")
        for field_name in (
            "initial",
            "target",
            "minimum",
            "maximum",
            "trend",
            "noise",
            "control_strength",
        ):
            _finite(getattr(self, field_name), f"variables.{self.name}.{field_name}")
        if not isinstance(self.aliases, tuple) or any(
            not isinstance(alias, str) or not alias.strip() for alias in self.aliases
        ):
            raise ConfigError(f"variables.{self.name}.aliases cannot contain empty values")
        normalised_aliases = [alias.strip().casefold() for alias in self.aliases]
        if len(normalised_aliases) != len(set(normalised_aliases)):
            raise ConfigError(f"variables.{self.name}.aliases must be unique ignoring case")
        if self.name.strip().casefold() in normalised_aliases:
            raise ConfigError(f"variables.{self.name}.aliases cannot repeat the variable name")
        if self.minimum >= self.maximum:
            raise ConfigError(f"variables.{self.name}: minimum must be below maximum")
        if not self.minimum <= self.initial <= self.maximum:
            raise ConfigError(f"variables.{self.name}.initial is outside its physical limits")
        if not self.minimum <= self.target <= self.maximum:
            raise ConfigError(f"variables.{self.name}.target is outside its physical limits")
        if self.noise < 0:
            raise ConfigError(f"variables.{self.name}.noise cannot be negative")
        if self.control_strength < 0:
            raise ConfigError(f"variables.{self.name}.control_strength cannot be negative")

    @property
    def span(self) -> float:
        return self.maximum - self.minimum


@dataclass(frozen=True)
class RelationshipConfig:
    """A directed linear relationship from source variables into a target."""

    target: str
    dependencies: Mapping[str, float]

    def __post_init__(self) -> None:
        if not isinstance(self.dependencies, Mapping):
            raise ConfigError("relationship dependencies must be an object")
        object.__setattr__(self, "dependencies", MappingProxyType(dict(self.dependencies)))
        if not isinstance(self.target, str) or not self.target.strip():
            raise ConfigError("relationship targets must be non-empty strings")
        for source, coefficient in self.dependencies.items():
            if not isinstance(source, str) or not source.strip():
                raise ConfigError("relationship dependency keys must be non-empty strings")
            _finite(coefficient, f"relationships.{self.target}.dependencies.{source}")

    @classmethod
    def from_dict(cls, target: str, raw: Mapping[str, Any]) -> RelationshipConfig:
        if not isinstance(target, str) or not target.strip():
            raise ConfigError("relationship targets must be non-empty strings")
        allowed = {"dependencies"}
        unknown = set(raw) - allowed
        if unknown:
            raise ConfigError(f"relationships.{target} has unknown fields: {sorted(unknown)}")
        dependencies_raw = _mapping(raw.get("dependencies"), f"relationships.{target}.dependencies")
        dependencies: dict[str, float] = {}
        for source, value in dependencies_raw.items():
            if not isinstance(source, str) or not source.strip():
                raise ConfigError(f"relationships.{target}.dependencies keys must be strings")
            dependencies[source] = _finite(value, f"relationships.{target}.dependencies.{source}")
        return cls(
            target=target,
            dependencies=dependencies,
        )


@dataclass(frozen=True)
class ControllerConfig:
    name: str = "active-inference"
    stochastic: bool = False
    response_rate: float = 0.5
    damping: float = 0.2
    random_seed: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigError("controller.name must be a non-empty string")
        if self.name.strip().lower() not in {
            "active-inference",
            "active_inference",
            "active",
            "slide-rule",
            "slide_rule",
            "proportional",
            "random",
            "business",
            "committee",
        }:
            raise ConfigError(f"unknown controller {self.name!r}")
        response_rate = _finite(self.response_rate, "controller.response_rate")
        damping = _finite(self.damping, "controller.damping")
        if not 0 < response_rate <= 1:
            raise ConfigError("controller.response_rate must be in (0, 1]")
        if not 0 <= damping < 1:
            raise ConfigError("controller.damping must be in [0, 1)")
        if not isinstance(self.stochastic, bool):
            raise ConfigError("controller.stochastic must be boolean")
        if self.random_seed is not None and (
            isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int)
        ):
            raise ConfigError("controller.random_seed must be an integer or null")

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any] | None) -> ControllerConfig:
        raw = {} if raw is None else raw
        if not isinstance(raw, Mapping):
            raise ConfigError("controller must be an object")
        allowed = {"name", "stochastic", "response_rate", "damping", "random_seed"}
        unknown = set(raw) - allowed
        if unknown:
            raise ConfigError(f"controller has unknown fields: {sorted(unknown)}")
        name = raw.get("name", cls.name)
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("controller.name must be a non-empty string")
        response_rate = _finite(
            raw.get("response_rate", cls.response_rate), "controller.response_rate"
        )
        damping = _finite(raw.get("damping", cls.damping), "controller.damping")
        if not 0 < response_rate <= 1:
            raise ConfigError("controller.response_rate must be in (0, 1]")
        if not 0 <= damping < 1:
            raise ConfigError("controller.damping must be in [0, 1)")
        stochastic = raw.get("stochastic", cls.stochastic)
        if not isinstance(stochastic, bool):
            raise ConfigError("controller.stochastic must be boolean")
        seed = raw.get("random_seed")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise ConfigError("controller.random_seed must be an integer or null")
        return cls(str(name), stochastic, response_rate, damping, seed)


@dataclass(frozen=True)
class OutputConfig:
    directory: str = "artifacts"
    write_by_default: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.directory, str) or not self.directory.strip():
            raise ConfigError("output.directory must be a non-empty string")
        if "\x00" in self.directory:
            raise ConfigError("output.directory cannot contain NUL characters")
        if not isinstance(self.write_by_default, bool):
            raise ConfigError("output.write_by_default must be boolean")

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any] | None) -> OutputConfig:
        raw = {} if raw is None else raw
        if not isinstance(raw, Mapping):
            raise ConfigError("output must be an object")
        allowed = {"directory", "write_by_default"}
        unknown = set(raw) - allowed
        if unknown:
            raise ConfigError(f"output has unknown fields: {sorted(unknown)}")
        directory = raw.get("directory", cls.directory)
        if not isinstance(directory, str) or not directory.strip():
            raise ConfigError("output.directory must be a non-empty string")
        write = raw.get("write_by_default", cls.write_by_default)
        if not isinstance(write, bool):
            raise ConfigError("output.write_by_default must be boolean")
        return cls(directory, write)


@dataclass(frozen=True)
class BiofirmConfig:
    """Complete immutable configuration for one ecosystem model."""

    name: str
    variables: Mapping[str, VariableConfig]
    relationships: Mapping[str, RelationshipConfig] = field(default_factory=dict)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    seed: int = 7

    def __post_init__(self) -> None:
        if not isinstance(self.variables, Mapping):
            raise ConfigError("configuration.variables must be an object")
        if not isinstance(self.relationships, Mapping):
            raise ConfigError("configuration.relationships must be an object")
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))
        object.__setattr__(self, "relationships", MappingProxyType(dict(self.relationships)))
        self.validate()

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> BiofirmConfig:
        if not isinstance(raw, Mapping):
            raise ConfigError("configuration must be an object")
        allowed = {"name", "variables", "relationships", "controller", "output", "seed"}
        unknown = set(raw) - allowed
        if unknown:
            raise ConfigError(f"configuration has unknown fields: {sorted(unknown)}")
        if "name" not in raw:
            raise ConfigError("configuration.name is required")
        if not isinstance(raw["name"], str) or not raw["name"].strip():
            raise ConfigError("configuration.name must be a non-empty string")
        if "variables" not in raw:
            raise ConfigError("configuration.variables is required")
        variables_raw = _mapping(raw.get("variables"), "variables")
        variables: dict[str, VariableConfig] = {}
        for name, value in variables_raw.items():
            if not isinstance(name, str) or not name.strip():
                raise ConfigError("variable keys must be non-empty strings")
            variables[name] = VariableConfig.from_dict(name, _mapping(value, f"variables.{name}"))
        relationships_raw = _mapping(raw.get("relationships", {}), "relationships")
        relationships: dict[str, RelationshipConfig] = {}
        for target, value in relationships_raw.items():
            if not isinstance(target, str) or not target.strip():
                raise ConfigError("relationship keys must be non-empty strings")
            relationships[target] = RelationshipConfig.from_dict(
                target, _mapping(value, f"relationships.{target}")
            )
        seed = raw.get("seed", 7)
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ConfigError("seed must be an integer")
        config = cls(
            name=raw["name"],
            variables=variables,
            relationships=relationships,
            controller=ControllerConfig.from_dict(raw.get("controller")),
            output=OutputConfig.from_dict(raw.get("output")),
            seed=seed,
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigError("configuration.name cannot be empty")
        if not isinstance(self.controller, ControllerConfig):
            raise ConfigError("configuration.controller must be ControllerConfig")
        if not isinstance(self.output, OutputConfig):
            raise ConfigError("configuration.output must be OutputConfig")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ConfigError("seed must be an integer")
        if not self.variables:
            raise ConfigError("at least one variable is required")
        if len(self.variables) != len(set(self.variables)):
            raise ConfigError("variable names must be unique")
        for name, variable in self.variables.items():
            if not isinstance(name, str) or not isinstance(variable, VariableConfig):
                raise ConfigError("variables must map string names to VariableConfig values")
            if name != variable.name:
                raise ConfigError(f"variable key {name!r} does not match its name")
            variable.validate()
        names = {name.casefold() for name in self.variables}
        if len(names) != len(self.variables):
            raise ConfigError("variable names must be unique ignoring case")
        aliases: dict[str, str] = {}
        for name, variable in self.variables.items():
            for alias in (name, *variable.aliases):
                key = alias.strip().casefold()
                owner = aliases.get(key)
                if owner is not None and owner != name:
                    raise ConfigError(
                        f"variable alias {alias!r} is shared by {owner!r} and {name!r}"
                    )
                aliases[key] = name
        for target, relationship in self.relationships.items():
            if not isinstance(target, str) or not isinstance(relationship, RelationshipConfig):
                raise ConfigError(
                    "relationships must map string targets to RelationshipConfig values"
                )
            if target not in self.variables:
                raise ConfigError(f"relationship target {target!r} is unknown")
            if target != relationship.target:
                raise ConfigError(f"relationship key {target!r} does not match its target")
            for source, coefficient in relationship.dependencies.items():
                if source not in self.variables:
                    raise ConfigError(
                        f"relationship {target!r} depends on unknown variable {source!r}"
                    )
                if not math.isfinite(coefficient):
                    raise ConfigError(f"relationship coefficient {target}.{source} must be finite")
        self._validate_relationship_acyclic()

    def _validate_relationship_acyclic(self) -> None:
        graph = {
            target: set(relationship.dependencies)
            for target, relationship in self.relationships.items()
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ConfigError("relationships cannot contain cycles")
            if node in visited:
                return
            visiting.add(node)
            for dependency in graph.get(node, ()):
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for variable in self.variables:
            visit(variable)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "seed": self.seed,
            "variables": {
                name: {
                    "initial": variable.initial,
                    "target": variable.target,
                    "minimum": variable.minimum,
                    "maximum": variable.maximum,
                    "trend": variable.trend,
                    "noise": variable.noise,
                    "control_strength": variable.control_strength,
                    "unit": variable.unit,
                    "aliases": list(variable.aliases),
                }
                for name, variable in self.variables.items()
            },
            "relationships": {
                target: {"dependencies": dict(relationship.dependencies)}
                for target, relationship in self.relationships.items()
            },
            "controller": {
                "name": self.controller.name,
                "stochastic": self.controller.stochastic,
                "response_rate": self.controller.response_rate,
                "damping": self.controller.damping,
                "random_seed": self.controller.random_seed,
            },
            "output": {
                "directory": self.output.directory,
                "write_by_default": self.output.write_by_default,
            },
        }

    @property
    def sha256(self) -> str:
        """Stable identity for this validated configuration."""

        return sha256_json(self.to_dict())


def load_config(path: str | Path | None = None) -> BiofirmConfig:
    """Load and strictly validate JSON configuration, packaged by default."""

    if path is None:
        raw_text = resources.files("biofirm").joinpath("data/ecosystem.json").read_text()
    else:
        raw_text = Path(path).read_text(encoding="utf-8")
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON configuration: {exc}") from exc
    return BiofirmConfig.from_dict(_mapping(raw, "configuration"))
