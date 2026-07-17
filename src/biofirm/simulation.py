"""Reproducible ecological transition dynamics and immutable run history."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .config import BiofirmConfig, VariableConfig
from .controllers import ControlDecision, Controller, build_controller
from .immutability import freeze, thaw
from .io import atomic_write_json


class SimulationError(RuntimeError):
    """Raised when a simulation cannot produce a valid transition."""


class ResultSchemaError(ValueError):
    """Raised when a serialized simulation result is incomplete or malformed."""


@dataclass(frozen=True)
class TransitionRecord:
    timestep: int
    values: Mapping[str, float]
    observations: Mapping[str, int]
    controls: Mapping[str, float]
    action_ids: Mapping[str, int]
    metrics: Mapping[str, float]
    beliefs: Mapping[str, tuple[float, ...]]
    variational_free_energy: Mapping[str, float]
    expected_free_energy: Mapping[str, tuple[float, ...]]
    policy_distributions: Mapping[str, tuple[float, ...]]
    diagnostics: Mapping[str, float]

    def __post_init__(self) -> None:
        for field_name in (
            "values",
            "observations",
            "controls",
            "action_ids",
            "metrics",
            "beliefs",
            "variational_free_energy",
            "expected_free_energy",
            "policy_distributions",
            "diagnostics",
        ):
            object.__setattr__(self, field_name, freeze(getattr(self, field_name)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestep": self.timestep,
            "values": thaw(self.values),
            "observations": thaw(self.observations),
            "controls": thaw(self.controls),
            "action_ids": thaw(self.action_ids),
            "metrics": thaw(self.metrics),
            "beliefs": thaw(self.beliefs),
            "variational_free_energy": thaw(self.variational_free_energy),
            "expected_free_energy": thaw(self.expected_free_energy),
            "policy_distributions": thaw(self.policy_distributions),
            "diagnostics": thaw(self.diagnostics),
        }


@dataclass(frozen=True)
class SimulationResult:
    config_name: str
    seed: int
    records: tuple[TransitionRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.config_name, str) or not self.config_name.strip():
            raise SimulationError("simulation config_name must be non-empty")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise SimulationError("simulation seed must be an integer")
        records = tuple(self.records)
        if not records:
            raise SimulationError("simulation result must contain transition records")
        if any(not isinstance(record, TransitionRecord) for record in records):
            raise SimulationError("simulation records must be TransitionRecord values")
        object.__setattr__(self, "records", records)

    @property
    def final_values(self) -> Mapping[str, float]:
        return self.records[-1].values

    @property
    def summary(self) -> Mapping[str, float]:
        if not self.records:
            raise SimulationError("simulation result has no transition records")
        final = self.records[-1]
        return {
            "steps": float(max(0, len(self.records) - 1)),
            "mean_free_energy": float(
                np.mean([sum(record.variational_free_energy.values()) for record in self.records])
            ),
            "final_homeostatic_error": float(final.metrics["homeostatic_error"]),
            "total_control_effort": float(
                sum(record.metrics["control_effort"] for record in self.records)
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_name": self.config_name,
            "seed": self.seed,
            "summary": dict(self.summary),
            "records": [record.to_dict() for record in self.records],
        }


def simulate(
    config: BiofirmConfig,
    steps: int = 20,
    seed: int | None = None,
    controller: Controller | None = None,
    controller_name: str | None = None,
) -> SimulationResult:
    """Run a seeded simulation with a complete transition record for each step."""

    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
        raise SimulationError("steps must be a non-negative integer")
    run_seed = config.seed if seed is None else seed
    if isinstance(run_seed, bool) or not isinstance(run_seed, int):
        raise SimulationError("seed must be an integer")
    selected_controller = controller or build_controller(config, controller_name)
    selected_controller.reset(run_seed)
    rng = np.random.default_rng(run_seed)
    values = {name: variable.initial for name, variable in config.variables.items()}
    records: list[TransitionRecord] = [_record_initial(config, values)]
    for timestep in range(1, steps + 1):
        decision = selected_controller.act(values)
        _validate_decision(config, decision)
        next_values, diagnostics = _transition(config, values, decision, rng)
        records.append(_record(config, timestep, next_values, decision, diagnostics))
        values = next_values
    return SimulationResult(config.name, run_seed, tuple(records))


def _transition(
    config: BiofirmConfig,
    values: Mapping[str, float],
    decision: ControlDecision,
    rng: np.random.Generator,
) -> tuple[dict[str, float], dict[str, float]]:
    next_values: dict[str, float] = {}
    diagnostics: dict[str, float] = {}
    for name, variable in config.variables.items():
        current = float(values[name])
        trend_effect = variable.trend
        relationship_effect = 0.0
        relationship = config.relationships.get(name)
        if relationship:
            for source, coefficient in relationship.dependencies.items():
                source_config = config.variables[source]
                normalised = (float(values[source]) - source_config.target) / source_config.span
                relationship_effect += coefficient * normalised * variable.span
        if name not in decision.controls:
            raise SimulationError(f"controller omitted control for {name!r}")
        control = float(decision.controls[name])
        if not math.isfinite(control) or abs(control) > variable.control_strength + 1e-9:
            raise SimulationError(f"controller produced invalid control for {name!r}")
        raw_noise = float(rng.normal(0.0, variable.noise))
        noise = float(np.clip(raw_noise, -3.0 * variable.noise, 3.0 * variable.noise))
        proposed = current + trend_effect + relationship_effect + control + noise
        next_values[name] = float(np.clip(proposed, variable.minimum, variable.maximum))
        diagnostics[f"{name}.trend"] = trend_effect
        diagnostics[f"{name}.relationship"] = relationship_effect
        diagnostics[f"{name}.control"] = control
        diagnostics[f"{name}.noise"] = noise
    return next_values, diagnostics


def _record_initial(config: BiofirmConfig, values: Mapping[str, float]) -> TransitionRecord:
    empty = ControlDecision(
        controls={name: 0.0 for name in values}, action_ids={name: 1 for name in values}
    )
    return _record(config, 0, values, empty, {name: 0.0 for name in values})


def _record(
    config: BiofirmConfig,
    timestep: int,
    values: Mapping[str, float],
    decision: ControlDecision,
    diagnostics: Mapping[str, float],
) -> TransitionRecord:
    observations = {
        name: _observation(value, config.variables[name]) for name, value in values.items()
    }
    errors = [
        abs(value - config.variables[name].target) / config.variables[name].span
        for name, value in values.items()
    ]
    homeostatic_error = float(np.mean(errors))
    metrics = {
        "homeostatic_error": homeostatic_error,
        "homeostatic_score": max(0.0, 1.0 - homeostatic_error),
        "control_effort": float(np.sum(np.abs(list(decision.controls.values())))),
        "bounded": 1.0,
    }
    return TransitionRecord(
        timestep=timestep,
        values=freeze(values),
        observations=freeze(observations),
        controls=freeze(decision.controls),
        action_ids=freeze(decision.action_ids),
        metrics=freeze(metrics),
        beliefs=freeze(decision.beliefs),
        variational_free_energy=freeze(decision.variational_free_energy),
        expected_free_energy=freeze(decision.expected_free_energy),
        policy_distributions=freeze(decision.policy_distributions),
        diagnostics=freeze(diagnostics),
    )


def _observation(value: float, variable: VariableConfig) -> int:
    normalised = (value - variable.target) / variable.span
    if normalised < -0.05:
        return 0
    if normalised > 0.05:
        return 2
    return 1


def write_result(result: SimulationResult, output: str | Path) -> Path:
    """Atomically write a complete JSON result and return its path."""

    try:
        return atomic_write_json(output, result.to_dict())
    except ValueError as exc:
        raise SimulationError(str(exc)) from exc


def validate_result_document(document: Any) -> dict[str, Any]:
    """Validate a decoded result document before analysis or visualization."""

    if not isinstance(document, dict):
        raise ResultSchemaError("simulation result must be a JSON object")
    if not isinstance(document.get("config_name"), str) or not document["config_name"].strip():
        raise ResultSchemaError("simulation result requires config_name")
    if isinstance(document.get("seed"), bool) or not isinstance(document.get("seed"), int):
        raise ResultSchemaError("simulation result requires an integer seed")
    records = document.get("records")
    if not isinstance(records, list) or not records:
        raise ResultSchemaError("simulation result requires non-empty records")
    summary = document.get("summary")
    if not isinstance(summary, dict) or not summary:
        raise ResultSchemaError("simulation result requires a non-empty summary")
    if not all(_finite_json_number(value) for value in summary.values()):
        raise ResultSchemaError("simulation summary contains non-finite values")
    required = {
        "timestep",
        "values",
        "observations",
        "controls",
        "action_ids",
        "metrics",
        "beliefs",
        "variational_free_energy",
        "expected_free_energy",
        "policy_distributions",
        "diagnostics",
    }
    timesteps: list[int] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not required.issubset(record):
            raise ResultSchemaError(f"record {index} is missing required fields")
        if isinstance(record.get("timestep"), bool) or not isinstance(record.get("timestep"), int):
            raise ResultSchemaError(f"record {index} requires an integer timestep")
        timesteps.append(record["timestep"])
        if not isinstance(record["values"], dict) or not record["values"]:
            raise ResultSchemaError(f"record {index} has empty values")
        if not isinstance(record["observations"], dict) or not record["observations"]:
            raise ResultSchemaError(f"record {index} has empty observations")
        if not isinstance(record["controls"], dict) or not record["controls"]:
            raise ResultSchemaError(f"record {index} has empty controls")
        if not isinstance(record["action_ids"], dict) or not record["action_ids"]:
            raise ResultSchemaError(f"record {index} has empty action_ids")
        if not isinstance(record["metrics"], dict) or not record["metrics"]:
            raise ResultSchemaError(f"record {index} has empty metrics")
        for field_name in (
            "beliefs",
            "variational_free_energy",
            "expected_free_energy",
            "policy_distributions",
            "diagnostics",
        ):
            if not isinstance(record[field_name], dict):
                raise ResultSchemaError(f"record {index} has invalid {field_name}")
        for field_name in ("values", "controls", "metrics"):
            if not all(_finite_json_number(value) for value in record[field_name].values()):
                raise ResultSchemaError(f"record {index} has non-finite {field_name}")
        if not all(
            isinstance(value, int) and not isinstance(value, bool) and value in {0, 1, 2}
            for value in record["observations"].values()
        ):
            raise ResultSchemaError(f"record {index} has invalid observations")
        if not all(
            isinstance(value, int) and not isinstance(value, bool) and value in {0, 1, 2}
            for value in record["action_ids"].values()
        ):
            raise ResultSchemaError(f"record {index} has invalid action_ids")
    if timesteps != list(range(len(records))):
        raise ResultSchemaError("record timesteps must start at zero and be contiguous")
    return document


def _validate_decision(config: BiofirmConfig, decision: ControlDecision) -> None:
    names = set(config.variables)
    if set(decision.controls) != names or set(decision.action_ids) != names:
        raise SimulationError("controller decision must contain exactly the configured variables")
    for name, action in decision.action_ids.items():
        if isinstance(action, bool) or not isinstance(action, int) or action not in {0, 1, 2}:
            raise SimulationError(f"controller produced invalid action for {name!r}")


def parameter_sweep(
    config: BiofirmConfig,
    steps: int,
    seeds: list[int],
    controller_name: str | None = None,
) -> list[dict[str, float | int | str]]:
    """Run independent seeded simulations and return summary rows."""

    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
        raise SimulationError("steps must be a non-negative integer")
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise SimulationError("seeds must be a non-empty list of integers")
    rows: list[dict[str, float | int | str]] = []
    for seed in seeds:
        result = simulate(config, steps=steps, seed=seed, controller_name=controller_name)
        rows.append(
            {
                "seed": seed,
                "controller": controller_name or config.controller.name,
                **result.summary,
            }
        )
    return rows


def _finite_json_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )
