"""Reproducible ecological transition dynamics and immutable run history."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ._version import __version__
from .config import BiofirmConfig, ConfigError, VariableConfig, observation_index, sha256_json
from .controllers import ControlDecision, Controller, build_controller
from .immutability import freeze, thaw
from .io import atomic_write_json


class SimulationError(RuntimeError):
    """Raised when a simulation cannot produce a valid transition."""


class ResultSchemaError(ValueError):
    """Raised when a serialized simulation result is incomplete or malformed."""


RESULT_SCHEMA_VERSION = 1


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
    schema_version: int = RESULT_SCHEMA_VERSION
    config_sha256: str = ""
    config_snapshot: Mapping[str, Any] = field(default_factory=dict)
    controller: str = "unknown"
    package_version: str = __version__

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
        if self.schema_version != RESULT_SCHEMA_VERSION:
            raise SimulationError(f"unsupported simulation schema version {self.schema_version}")
        if not isinstance(self.controller, str) or not self.controller.strip():
            raise SimulationError("simulation controller must be non-empty")
        if not isinstance(self.package_version, str) or not self.package_version.strip():
            raise SimulationError("simulation package_version must be non-empty")
        snapshot = dict(self.config_snapshot)
        if snapshot:
            try:
                config_hash = sha256_json(snapshot)
            except ValueError as exc:
                raise SimulationError("simulation configuration snapshot is invalid") from exc
            if self.config_sha256 and self.config_sha256 != config_hash:
                raise SimulationError("simulation configuration hash does not match snapshot")
            object.__setattr__(self, "config_sha256", config_hash)
        elif self.config_sha256:
            raise SimulationError("simulation configuration hash requires a snapshot")
        object.__setattr__(self, "config_snapshot", freeze(snapshot))

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
            "schema_version": self.schema_version,
            "config_name": self.config_name,
            "config_sha256": self.config_sha256,
            "config": thaw(self.config_snapshot),
            "controller": self.controller,
            "package_version": self.package_version,
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
    if controller_name is not None:
        selected_name = controller_name
    else:
        # Report the identity of the controller actually used, so a raw
        # controller instance passed directly is never mislabeled with the
        # configured default's name.
        selected_name = getattr(selected_controller, "name", config.controller.name)
    return SimulationResult(
        config.name,
        run_seed,
        tuple(records),
        config_sha256=config.sha256,
        config_snapshot=config.to_dict(),
        controller=selected_name,
    )


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
        controls={name: 0.0 for name in values},
        action_ids={name: 1 for name in values},
        beliefs={name: () for name in values},
        variational_free_energy={name: 0.0 for name in values},
        expected_free_energy={name: () for name in values},
        policy_distributions={name: () for name in values},
    )
    return _record(
        config,
        0,
        values,
        empty,
        {
            f"{name}.{term}": 0.0
            for name in values
            for term in ("trend", "relationship", "control", "noise")
        },
    )


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
        "posterior_entropy": float(
            np.mean([_belief_entropy(decision.beliefs.get(name, ())) for name in config.variables])
        ),
    }
    return TransitionRecord(
        timestep=timestep,
        values=freeze(values),
        observations=freeze(observations),
        controls=freeze(decision.controls),
        action_ids=freeze(decision.action_ids),
        metrics=freeze(metrics),
        beliefs=freeze({name: decision.beliefs.get(name, ()) for name in config.variables}),
        variational_free_energy=freeze(
            {name: decision.variational_free_energy.get(name, 0.0) for name in config.variables}
        ),
        expected_free_energy=freeze(
            {name: decision.expected_free_energy.get(name, ()) for name in config.variables}
        ),
        policy_distributions=freeze(
            {name: decision.policy_distributions.get(name, ()) for name in config.variables}
        ),
        diagnostics=freeze(diagnostics),
    )


def _observation(value: float, variable: VariableConfig) -> int:
    normalised = (value - variable.target) / variable.span
    return observation_index(normalised, variable.observation_bins)


def _action_id(control: float) -> int:
    if control > 1e-12:
        return 2
    if control < -1e-12:
        return 0
    return 1


def _belief_entropy(values: tuple[float, ...]) -> float:
    """Shannon entropy of a belief distribution (0 for an empty/known state)."""
    if not values:
        return 0.0
    total = float(sum(values))
    if total <= 0:
        return 0.0
    return float(
        -sum(prob * math.log(prob) for prob in (value / total for value in values if value > 0))
    )


def write_result(result: SimulationResult, output: str | Path) -> Path:
    """Atomically write a complete JSON result and return its path."""

    try:
        document = result.to_dict()
        validate_result_document(document)
        return atomic_write_json(output, document)
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
    top_level = {
        "schema_version",
        "config_name",
        "config_sha256",
        "config",
        "controller",
        "package_version",
        "seed",
        "summary",
        "records",
    }
    if set(document) != top_level:
        raise ResultSchemaError("simulation result has unexpected top-level fields")
    if document.get("schema_version") != RESULT_SCHEMA_VERSION:
        raise ResultSchemaError(
            f"simulation result requires schema_version {RESULT_SCHEMA_VERSION}"
        )
    config = document.get("config")
    if not isinstance(config, dict):
        raise ResultSchemaError("simulation result requires a configuration snapshot")
    try:
        validated_config = BiofirmConfig.from_dict(config)
    except (ConfigError, TypeError) as exc:
        raise ResultSchemaError(
            "simulation result contains an invalid configuration snapshot"
        ) from exc
    if document.get("config_name") != validated_config.name:
        raise ResultSchemaError("simulation config_name does not match configuration snapshot")
    config_hash = document.get("config_sha256")
    if not isinstance(config_hash, str) or config_hash != validated_config.sha256:
        raise ResultSchemaError("simulation configuration hash does not match snapshot")
    if not isinstance(document.get("controller"), str) or not document["controller"].strip():
        raise ResultSchemaError("simulation result requires controller")
    if (
        not isinstance(document.get("package_version"), str)
        or not document["package_version"].strip()
    ):
        raise ResultSchemaError("simulation result requires package_version")
    summary = document.get("summary")
    expected_summary_keys = {
        "steps",
        "mean_free_energy",
        "final_homeostatic_error",
        "total_control_effort",
    }
    if not isinstance(summary, dict) or set(summary) != expected_summary_keys:
        raise ResultSchemaError("simulation result requires the complete summary")
    if not all(_finite_json_number(value) for value in summary.values()):
        raise ResultSchemaError("simulation summary contains non-finite values")
    variable_names = set(validated_config.variables)
    diagnostic_names = {
        f"{name}.{term}"
        for name in variable_names
        for term in ("trend", "relationship", "control", "noise")
    }
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
    metric_names = {
        "homeostatic_error",
        "homeostatic_score",
        "control_effort",
        "bounded",
        "posterior_entropy",
    }
    timesteps: list[int] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not required.issubset(record):
            raise ResultSchemaError(f"record {index} is missing required fields")
        if set(record) != required:
            raise ResultSchemaError(f"record {index} has unexpected fields")
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
        if set(record["metrics"]) != metric_names:
            raise ResultSchemaError(f"record {index} has inconsistent metrics keys")
        for field_name in (
            "beliefs",
            "variational_free_energy",
            "expected_free_energy",
            "policy_distributions",
            "diagnostics",
        ):
            if not isinstance(record[field_name], dict):
                raise ResultSchemaError(f"record {index} has invalid {field_name}")
        for field_name in ("values", "observations", "controls", "action_ids"):
            if set(record[field_name]) != variable_names:
                raise ResultSchemaError(f"record {index} has inconsistent {field_name} keys")
        if set(record["diagnostics"]) != diagnostic_names:
            raise ResultSchemaError(f"record {index} has inconsistent diagnostics keys")
        for field_name in (
            "beliefs",
            "variational_free_energy",
            "expected_free_energy",
            "policy_distributions",
        ):
            if set(record[field_name]) != variable_names:
                raise ResultSchemaError(f"record {index} has inconsistent {field_name} keys")
        for field_name in ("values", "controls", "metrics"):
            if not all(_finite_json_number(value) for value in record[field_name].values()):
                raise ResultSchemaError(f"record {index} has non-finite {field_name}")
        if not all(_finite_json_number(value) for value in record["diagnostics"].values()):
            raise ResultSchemaError(f"record {index} has non-finite diagnostics")
        for field_name in ("beliefs", "expected_free_energy", "policy_distributions"):
            for name, values in record[field_name].items():
                if not isinstance(values, list) or not all(
                    _finite_json_number(value) for value in values
                ):
                    raise ResultSchemaError(f"record {index} has invalid {field_name}.{name}")
                if (
                    field_name in {"beliefs", "policy_distributions"}
                    and values
                    and (
                        any(float(value) < 0 for value in values)
                        or not math.isclose(float(sum(values)), 1.0, rel_tol=1e-6, abs_tol=1e-6)
                    )
                ):
                    raise ResultSchemaError(f"record {index} has unnormalized {field_name}.{name}")
        if not all(
            _finite_json_number(value) for value in record["variational_free_energy"].values()
        ):
            raise ResultSchemaError(f"record {index} has non-finite variational_free_energy")
        if not all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value < validated_config.variables[name].observation_bins
            for name, value in record["observations"].items()
        ):
            raise ResultSchemaError(f"record {index} has invalid observations")
        if not all(
            isinstance(value, int) and not isinstance(value, bool) and value in {0, 1, 2}
            for value in record["action_ids"].values()
        ):
            raise ResultSchemaError(f"record {index} has invalid action_ids")
        for name, value in record["values"].items():
            variable = validated_config.variables[name]
            if not variable.minimum <= float(value) <= variable.maximum:
                raise ResultSchemaError(f"record {index} has out-of-bounds values.{name}")
            expected_observation = _observation(float(value), variable)
            if record["observations"][name] != expected_observation:
                raise ResultSchemaError(f"record {index} has inconsistent observations.{name}")
            control = float(record["controls"][name])
            if abs(control) > variable.control_strength + 1e-9:
                raise ResultSchemaError(f"record {index} has out-of-bounds controls.{name}")
            expected_action = _action_id(control)
            if record["action_ids"][name] != expected_action:
                raise ResultSchemaError(f"record {index} has inconsistent action_ids.{name}")
        expected_effort = float(np.sum(np.abs(list(record["controls"].values()))))
        expected_error = float(
            np.mean(
                [
                    abs(record["values"][name] - validated_config.variables[name].target)
                    / validated_config.variables[name].span
                    for name in variable_names
                ]
            )
        )
        if (
            not math.isclose(
                float(record["metrics"]["homeostatic_error"]),
                expected_error,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
            or not math.isclose(
                float(record["metrics"]["homeostatic_score"]),
                max(0.0, 1.0 - expected_error),
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
            or not math.isclose(
                float(record["metrics"]["control_effort"]),
                expected_effort,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
            or record["metrics"]["bounded"] != 1.0
        ):
            raise ResultSchemaError(f"record {index} has inconsistent metrics")
        for name in variable_names:
            if index == 0:
                expected_diagnostics = {
                    "trend": 0.0,
                    "relationship": 0.0,
                    "control": 0.0,
                    "noise": 0.0,
                }
            else:
                relationship_effect = 0.0
                relationship = validated_config.relationships.get(name)
                if relationship:
                    previous_values = records[index - 1]["values"]
                    for source, coefficient in relationship.dependencies.items():
                        source_config = validated_config.variables[source]
                        normalised = (
                            float(previous_values[source]) - source_config.target
                        ) / source_config.span
                        relationship_effect += (
                            coefficient * normalised * validated_config.variables[name].span
                        )
                expected_diagnostics = {
                    "trend": validated_config.variables[name].trend,
                    "relationship": relationship_effect,
                    "control": float(record["controls"][name]),
                }
            for term, expected in expected_diagnostics.items():
                diagnostic_actual = float(record["diagnostics"][f"{name}.{term}"])
                if not math.isclose(diagnostic_actual, expected, rel_tol=1e-9, abs_tol=1e-9):
                    raise ResultSchemaError(
                        f"record {index} has inconsistent diagnostics.{name}.{term}"
                    )
    if timesteps != list(range(len(records))):
        raise ResultSchemaError("record timesteps must start at zero and be contiguous")
    expected_summary = _summary_from_document(records)
    for key, expected in expected_summary.items():
        summary_actual: Any = summary.get(key)
        if (
            summary_actual is None
            or not _finite_json_number(summary_actual)
            or not math.isclose(float(summary_actual), expected, rel_tol=1e-9, abs_tol=1e-9)
        ):
            raise ResultSchemaError(f"simulation summary does not match records for {key}")
    return document


def _summary_from_document(records: list[dict[str, Any]]) -> dict[str, float]:
    """Recompute the result summary from JSON records for tamper detection."""

    final = records[-1]
    return {
        "steps": float(max(0, len(records) - 1)),
        "mean_free_energy": float(
            np.mean([sum(record["variational_free_energy"].values()) for record in records])
        ),
        "final_homeostatic_error": float(final["metrics"]["homeostatic_error"]),
        "total_control_effort": float(
            sum(record["metrics"]["control_effort"] for record in records)
        ),
    }


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


def compare_controllers(
    config: BiofirmConfig,
    steps: int,
    seeds: list[int],
    controllers: list[str],
) -> dict[str, Any]:
    """Compare configured controllers across independent seeded simulations."""

    if not controllers or len(set(controllers)) != len(controllers):
        raise SimulationError("controllers must be a non-empty list of unique names")
    rows: list[dict[str, float | int | str]] = []
    for controller_name in controllers:
        rows.extend(parameter_sweep(config, steps, seeds, controller_name))
    aggregates: dict[str, dict[str, float | int | str]] = {}
    for controller_name in controllers:
        selected = [row for row in rows if row["controller"] == controller_name]
        metrics = {
            key
            for row in selected
            for key, value in row.items()
            if key not in {"seed", "controller"} and isinstance(value, (int, float))
        }
        aggregates[controller_name] = {
            "runs": len(selected),
            **{
                f"mean_{metric}": float(np.mean([float(row[metric]) for row in selected]))
                for metric in sorted(metrics)
            },
            **{
                f"std_{metric}": float(np.std([float(row[metric]) for row in selected]))
                for metric in sorted(metrics)
            },
        }
    return {
        "schema_version": 1,
        "config_name": config.name,
        "config_sha256": config.sha256,
        "steps": steps,
        "seeds": list(seeds),
        "controllers": list(controllers),
        "rows": rows,
        "aggregates": aggregates,
    }


def _finite_json_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def run_scenarios(
    configs: list[BiofirmConfig],
    steps: int,
    seeds: list[int],
    controller_name: str | None = None,
) -> dict[str, Any]:
    """Run independent seeded simulations across ecosystem scenario variants.

    Each scenario is a distinct validated configuration; the report exposes
    per-scenario/per-seed summaries plus a per-scenario mean uncertainty
    estimate so scenarios can be compared without making calibrated ecological
    performance claims.
    """
    if not configs:
        raise SimulationError("at least one scenario configuration is required")
    names = [config.name for config in configs]
    if any(not isinstance(name, str) or not name.strip() for name in names) or len(
        set(names)
    ) != len(names):
        raise SimulationError("scenario configurations must have unique non-empty names")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
        raise SimulationError("steps must be a non-negative integer")
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise SimulationError("seeds must be a non-empty list of integers")
    rows: list[dict[str, float | int | str]] = []
    for config in configs:
        for seed in seeds:
            result = simulate(config, steps=steps, seed=seed, controller_name=controller_name)
            final_uncertainty = float(
                np.mean(
                    [
                        _belief_entropy(
                            tuple(float(item) for item in result.records[-1].beliefs[variable])
                        )
                        for variable in config.variables
                    ]
                )
            )
            rows.append(
                {
                    "scenario": config.name,
                    "seed": seed,
                    "controller": controller_name or config.controller.name,
                    **result.summary,
                    "final_uncertainty": final_uncertainty,
                }
            )
    return {
        "schema_version": 1,
        "steps": steps,
        "seeds": list(seeds),
        "scenarios": names,
        "controller": controller_name,
        "rows": rows,
    }
