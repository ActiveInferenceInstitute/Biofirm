"""Configurable, auditable committee decisions for ecological action."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .config import BiofirmConfig
from .controllers import ControlDecision


class BusinessDecisionError(ValueError):
    """Raised when a committee policy is invalid or cannot decide."""


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    controls: Mapping[str, float]
    cost: float
    risk: float
    ecological_effects: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "controls", MappingProxyType(dict(self.controls)))
        object.__setattr__(
            self, "ecological_effects", MappingProxyType(dict(self.ecological_effects))
        )

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any], config: BiofirmConfig) -> ActionDefinition:
        if not isinstance(raw, Mapping):
            raise BusinessDecisionError("each committee action must be an object")
        required = {"name", "controls", "cost", "risk", "ecological_effects"}
        missing = required - set(raw)
        if missing:
            raise BusinessDecisionError(f"action is missing fields: {sorted(missing)}")
        unknown = set(raw) - required
        if unknown:
            raise BusinessDecisionError(f"action has unknown fields: {sorted(unknown)}")
        name = raw["name"]
        if not isinstance(name, str) or not name.strip():
            raise BusinessDecisionError("action.name must be a non-empty string")
        controls = _variable_mapping(raw["controls"], config, "controls")
        effects = _variable_mapping(raw["ecological_effects"], config, "ecological_effects")
        cost = _number(raw["cost"], "cost")
        risk = _number(raw["risk"], "risk")
        if cost < 0 or not 0 <= risk <= 1:
            raise BusinessDecisionError(
                "action cost must be non-negative and risk must be in [0, 1]"
            )
        for variable, control in controls.items():
            if abs(control) > config.variables[variable].control_strength:
                raise BusinessDecisionError(
                    f"controls.{variable} exceeds configured control_strength"
                )
        return cls(name.strip(), controls, cost, risk, effects)


@dataclass(frozen=True)
class CommitteeRole:
    name: str
    weight: float
    priorities: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "priorities", MappingProxyType(dict(self.priorities)))


@dataclass(frozen=True)
class CommitteeConfig:
    budget: float
    roles: tuple[CommitteeRole, ...]
    actions: tuple[ActionDefinition, ...]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any], config: BiofirmConfig) -> CommitteeConfig:
        if not isinstance(raw, Mapping):
            raise BusinessDecisionError("committee configuration must be an object")
        allowed = {"budget", "roles", "actions"}
        unknown = set(raw) - allowed
        if unknown:
            raise BusinessDecisionError(f"committee has unknown fields: {sorted(unknown)}")
        missing = allowed - set(raw)
        if missing:
            raise BusinessDecisionError(f"committee is missing fields: {sorted(missing)}")
        budget = _number(raw.get("budget"), "budget")
        if budget < 0:
            raise BusinessDecisionError("budget cannot be negative")
        roles_raw = raw.get("roles")
        if not isinstance(roles_raw, list) or not roles_raw:
            raise BusinessDecisionError("committee.roles must be a non-empty list")
        roles: list[CommitteeRole] = []
        for item in roles_raw:
            if not isinstance(item, Mapping):
                raise BusinessDecisionError("each committee role must be an object")
            role_unknown = set(item) - {"name", "weight", "priorities"}
            if role_unknown:
                raise BusinessDecisionError(f"role has unknown fields: {sorted(role_unknown)}")
            if not isinstance(item.get("name"), str) or not str(item["name"]).strip():
                raise BusinessDecisionError("role.name must be a non-empty string")
            name = str(item["name"]).strip()
            weight = _number(item.get("weight"), f"role {name}.weight")
            priorities_raw = item.get("priorities", {})
            priorities = _variable_mapping(priorities_raw, config, f"role {name}.priorities")
            if not name or weight < 0:
                raise BusinessDecisionError("role names must be non-empty and weights non-negative")
            roles.append(CommitteeRole(name, weight, priorities))
        if len({role.name for role in roles}) != len(roles):
            raise BusinessDecisionError("role names must be unique")
        if sum(role.weight for role in roles) <= 0:
            raise BusinessDecisionError("committee role weights must have a positive sum")
        actions_raw = raw.get("actions")
        if not isinstance(actions_raw, list) or not actions_raw:
            raise BusinessDecisionError("committee.actions must be a non-empty list")
        actions = tuple(ActionDefinition.from_dict(item, config) for item in actions_raw)
        if len({action.name for action in actions}) != len(actions):
            raise BusinessDecisionError("action names must be unique")
        return cls(budget, tuple(roles), actions)


@dataclass(frozen=True)
class BusinessDecision:
    action: str
    score: float
    cost: float
    risk: float
    votes: Mapping[str, float]
    rationale: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "votes", MappingProxyType(dict(self.votes)))


def default_committee(config: BiofirmConfig, budget: float = 10.0) -> CommitteeConfig:
    actions: list[dict[str, Any]] = []
    for name, variable in config.variables.items():
        actions.extend(
            [
                {
                    "name": f"increase_{name}",
                    "controls": {name: variable.control_strength},
                    "cost": 1.0,
                    "risk": 0.1,
                    "ecological_effects": {name: variable.control_strength},
                },
                {
                    "name": f"decrease_{name}",
                    "controls": {name: -variable.control_strength},
                    "cost": 1.0,
                    "risk": 0.1,
                    "ecological_effects": {name: -variable.control_strength},
                },
            ]
        )
    return CommitteeConfig.from_dict(
        {
            "budget": budget,
            "roles": [
                {
                    "name": "ecology",
                    "weight": 1.0,
                    "priorities": {name: 1.0 for name in config.variables},
                },
                {
                    "name": "operations",
                    "weight": 0.75,
                    "priorities": {name: 0.5 for name in config.variables},
                },
            ],
            "actions": actions,
        },
        config,
    )


class BusinessCommittee:
    """Score actions using role priorities, ecological effects, cost, and risk."""

    def __init__(self, config: BiofirmConfig, committee: CommitteeConfig | None = None):
        self.config = config
        self.committee = committee or default_committee(config)

    def evaluate(self, values: Mapping[str, float]) -> BusinessDecision:
        if set(values) != set(self.config.variables):
            missing = sorted(set(self.config.variables) - set(values))
            extra = sorted(set(values) - set(self.config.variables))
            raise BusinessDecisionError(
                f"state keys do not match config; missing={missing}, extra={extra}"
            )
        for name, value in values.items():
            _number(value, f"state.{name}")
        role_weight_sum = sum(role.weight for role in self.committee.roles)
        scored: list[tuple[float, ActionDefinition, dict[str, float], list[str]]] = []
        for action in self.committee.actions:
            if action.cost > self.committee.budget:
                continue
            votes: dict[str, float] = {}
            rationale: list[str] = []
            score = 0.0
            for role in self.committee.roles:
                vote = 0.0
                for name, variable in self.config.variables.items():
                    error = variable.target - float(values[name])
                    effect = float(action.ecological_effects.get(name, 0.0))
                    priority = float(role.priorities.get(name, 0.0))
                    vote += priority * error * effect / variable.span
                vote -= action.cost * 0.05 + action.risk * 0.5
                votes[role.name] = vote
                score += role.weight * vote
                rationale.append(f"{role.name}: weighted vote {vote:.6f}")
            score /= role_weight_sum
            scored.append((score, action, votes, rationale))
        if not scored:
            raise BusinessDecisionError("no action fits the committee budget")
        score, action, votes, rationale = max(scored, key=lambda item: (item[0], item[1].name))
        rationale.append(f"selected {action.name} with score {score:.6f}")
        return BusinessDecision(
            action.name, float(score), action.cost, action.risk, votes, tuple(rationale)
        )

    def control(self, values: Mapping[str, float]) -> tuple[ControlDecision, BusinessDecision]:
        decision = self.evaluate(values)
        action = next(action for action in self.committee.actions if action.name == decision.action)
        return (
            ControlDecision(
                controls=dict(action.controls),
                action_ids={name: _action_id(value) for name, value in action.controls.items()},
                metadata={
                    "controller": "business",
                    "decision": decision.action,
                    "rationale": decision.rationale,
                },
            ),
            decision,
        )


class BusinessController:
    """Use committee decisions as a simulation controller."""

    def __init__(self, config: BiofirmConfig, committee: CommitteeConfig | None = None):
        self.committee = BusinessCommittee(config, committee)

    def reset(self, seed: int) -> None:
        del seed

    def act(self, values: Mapping[str, float]) -> ControlDecision:
        control, decision = self.committee.control(values)
        controls = {
            name: float(control.controls.get(name, 0.0)) for name in self.committee.config.variables
        }
        return ControlDecision(
            controls=controls,
            action_ids={name: _action_id(value) for name, value in controls.items()},
            beliefs=control.beliefs,
            variational_free_energy=control.variational_free_energy,
            expected_free_energy=control.expected_free_energy,
            policy_distributions=control.policy_distributions,
            metadata={**control.metadata, "business_decision": decision.action},
        )


def load_committee(path: str | Path, config: BiofirmConfig) -> CommitteeConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise BusinessDecisionError("business configuration must be an object")
    return CommitteeConfig.from_dict(raw, config)


def _number(value: Any, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise BusinessDecisionError(f"{name} must be finite")
    return float(value)


def _variable_mapping(value: Any, config: BiofirmConfig, name: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise BusinessDecisionError(f"{name} must be an object")
    unknown = set(value) - set(config.variables)
    if unknown:
        raise BusinessDecisionError(f"{name} has unknown variables: {sorted(unknown)}")
    return {str(key): _number(item, f"{name}.{key}") for key, item in value.items()}


def _action_id(control: float) -> int:
    return 2 if control > 0 else 0 if control < 0 else 1
