"""Controllers with one typed decision contract."""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from .config import BiofirmConfig, VariableConfig, observation_index
from .immutability import freeze
from .pymdp import build_active_inference_matrices


class ControllerError(RuntimeError):
    """Raised when a controller cannot produce a real decision."""


@dataclass(frozen=True)
class ControlDecision:
    """A controller's complete, auditable output for one timestep."""

    controls: Mapping[str, float]
    action_ids: Mapping[str, int]
    beliefs: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    variational_free_energy: Mapping[str, float] = field(default_factory=dict)
    expected_free_energy: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    policy_distributions: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "controls", freeze(self.controls))
        object.__setattr__(self, "action_ids", freeze(self.action_ids))
        object.__setattr__(self, "beliefs", freeze(self.beliefs))
        object.__setattr__(self, "variational_free_energy", freeze(self.variational_free_energy))
        object.__setattr__(self, "expected_free_energy", freeze(self.expected_free_energy))
        object.__setattr__(self, "policy_distributions", freeze(self.policy_distributions))
        object.__setattr__(self, "metadata", freeze(self.metadata))


class Controller(Protocol):
    """Protocol shared by every simulation controller."""

    def reset(self, seed: int) -> None: ...

    def act(self, values: Mapping[str, float]) -> ControlDecision: ...


def _action_for_control(control: float, tolerance: float = 1e-12) -> int:
    if control > tolerance:
        return 2
    if control < -tolerance:
        return 0
    return 1


class SlideRuleController:
    """Proportional bounded control with configurable damping."""

    name = "slide-rule"

    def __init__(self, config: BiofirmConfig):
        self.config = config
        self._previous: dict[str, float] = {}
        self.reset(config.seed)

    def reset(self, seed: int) -> None:
        del seed
        self._previous = {
            name: variable.initial for name, variable in self.config.variables.items()
        }

    def act(self, values: Mapping[str, float]) -> ControlDecision:
        _validate_values(self.config, values)
        controls: dict[str, float] = {}
        action_ids: dict[str, int] = {}
        metadata: dict[str, object] = {"controller": "slide-rule"}
        for name, variable in self.config.variables.items():
            current = _require_value(values, name)
            error = variable.target - current
            proportional = (error / variable.span) * variable.control_strength
            velocity = current - self._previous.get(name, current)
            control = proportional * self.config.controller.response_rate
            control -= velocity * self.config.controller.damping
            control = float(np.clip(control, -variable.control_strength, variable.control_strength))
            controls[name] = control
            action_ids[name] = _action_for_control(control)
            self._previous[name] = current
        return ControlDecision(controls=controls, action_ids=action_ids, metadata=metadata)


class RandomController:
    """Seeded baseline controller; randomness is explicit and reproducible."""

    name = "random"

    def __init__(self, config: BiofirmConfig, seed: int | None = None):
        self.config = config
        self.reset(config.seed if seed is None else seed)

    def reset(self, seed: int) -> None:
        self._rng = np.random.default_rng(seed)

    def act(self, values: Mapping[str, float]) -> ControlDecision:
        _validate_values(self.config, values)
        controls: dict[str, float] = {}
        action_ids: dict[str, int] = {}
        for name, variable in self.config.variables.items():
            action = int(self._rng.integers(0, 3))
            controls[name] = float((action - 1) * variable.control_strength)
            action_ids[name] = action
        return ControlDecision(
            controls=controls,
            action_ids=action_ids,
            metadata={"controller": "random", "seeded": True},
        )


class ActiveInferenceController:
    """Active inference controller using the installed PyMDP 1.x API.

    Each ecological variable is represented by a three-state discretisation:
    below target, at target, and above target. Actions decrease, hold, or
    increase the state. The controller passes JAX arrays and empirical priors
    explicitly, then records the model's beliefs, free energies, policy
    distribution, and selected action.
    """

    name = "active-inference"

    def __init__(self, config: BiofirmConfig, seed: int | None = None):
        self.config = config
        self._seed = config.seed if seed is None else seed
        self.reset(self._seed)

    def reset(self, seed: int) -> None:
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self._jax_key: Any = None
        self._agents: dict[str, Any] = {}
        try:
            import jax
            import jax.numpy as jnp
            from pymdp.agent import Agent
        except ImportError as exc:  # pragma: no cover - exercised by environment checks
            raise ControllerError(
                "active-inference requires inferactively-pymdp and jax; install biofirm's core dependencies"
            ) from exc
        self._jax = jax
        self._jnp = jnp
        self._jax_key = jax.random.PRNGKey(seed)
        for name, variable in self.config.variables.items():
            matrices = build_active_inference_matrices(variable.observation_bins)
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"A JAX array is being set as static!.*",
                    category=UserWarning,
                )
                self._agents[name] = Agent(
                    A=[jnp.asarray(matrices.A, dtype=jnp.float32)],
                    B=[jnp.asarray(matrices.B, dtype=jnp.float32)],
                    C=[jnp.asarray(matrices.C, dtype=jnp.float32)],
                    D=[jnp.asarray(matrices.D, dtype=jnp.float32)],
                    control_fac_idx=[0],
                    inference_algo="fpi",
                    action_selection="stochastic"
                    if self.config.controller.stochastic
                    else "deterministic",
                )
            del variable

    @staticmethod
    def _discrete_observation(value: float, variable: VariableConfig) -> int:
        normalised = (value - variable.target) / variable.span
        return observation_index(normalised, variable.observation_bins)

    def act(self, values: Mapping[str, float]) -> ControlDecision:
        _validate_values(self.config, values)
        controls: dict[str, float] = {}
        action_ids: dict[str, int] = {}
        beliefs: dict[str, tuple[float, ...]] = {}
        vfes: dict[str, float] = {}
        efes: dict[str, tuple[float, ...]] = {}
        policies: dict[str, tuple[float, ...]] = {}
        for name, variable in self.config.variables.items():
            value = _require_value(values, name)
            observation = self._discrete_observation(value, variable)
            agent = self._agents[name]
            try:
                observation_array = self._jnp.asarray([observation], dtype=self._jnp.int32)
                qs, info = agent.infer_states([observation_array], agent.D, return_info=True)
                q_pi, expected = agent.infer_policies(qs)
                q_pi_np = np.asarray(q_pi).reshape(-1)
                if self.config.controller.stochastic:
                    self._jax_key, action_key = self._jax.random.split(self._jax_key)
                    sampled = agent.sample_action(
                        q_pi, rng_key=self._jax.random.split(action_key, 1)
                    )
                    action = int(np.asarray(sampled).reshape(-1)[0])
                else:
                    action = int(np.argmax(q_pi_np))
                belief = np.asarray(qs[0]).reshape(-1)
                vfe = float(np.asarray(info["vfe"]).reshape(-1)[0])
                controls[name] = float((action - 1) * variable.control_strength)
                action_ids[name] = action
                beliefs[name] = tuple(float(item) for item in belief)
                vfes[name] = vfe
                efes[name] = tuple(float(item) for item in np.asarray(expected).reshape(-1))
                policies[name] = tuple(float(item) for item in q_pi_np)
            except Exception as exc:  # add context without replacing the real decision
                raise ControllerError(f"active-inference failed for variable {name!r}") from exc
        return ControlDecision(
            controls=controls,
            action_ids=action_ids,
            beliefs=beliefs,
            variational_free_energy=vfes,
            expected_free_energy=efes,
            policy_distributions=policies,
            metadata={"controller": "active-inference", "seed": self._seed},
        )


def build_controller(config: BiofirmConfig, name: str | None = None) -> Controller:
    """Build a configured controller without hidden fallbacks."""

    selected = (name or config.controller.name).strip().lower()
    if selected in {"active-inference", "active_inference", "active"}:
        return ActiveInferenceController(config, config.controller.random_seed)
    if selected in {"slide-rule", "slide_rule", "proportional"}:
        return SlideRuleController(config)
    if selected in {"business", "committee"}:
        from .business import BusinessController

        return BusinessController(config)
    if selected == "random":
        return RandomController(config, config.controller.random_seed)
    raise ControllerError(f"unknown controller {selected!r}")


def _require_value(values: Mapping[str, float], name: str) -> float:
    if name not in values:
        raise ControllerError(f"controller input is missing variable {name!r}")
    value = float(values[name])
    if not np.isfinite(value):
        raise ControllerError(f"controller input {name!r} is non-finite")
    return value


def _validate_values(config: BiofirmConfig, values: Mapping[str, float]) -> None:
    if set(values) != set(config.variables):
        missing = sorted(set(config.variables) - set(values))
        extra = sorted(set(values) - set(config.variables))
        raise ControllerError(
            f"controller input keys do not match config; missing={missing}, extra={extra}"
        )
    for name in config.variables:
        _require_value(values, name)
