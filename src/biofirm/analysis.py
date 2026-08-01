"""Reusable free-energy, surprise, and allocation analysis services."""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

import numpy as np

from .config import BiofirmConfig


@dataclass(frozen=True)
class SurpriseObservation:
    observation: float
    empirical_surprise: float
    preference_surprise: float
    total_surprise: float
    posterior_mean: float


class SurpriseTracker:
    """Track empirical and preference surprise without hidden state resets."""

    def __init__(
        self, prior_mean: float, prior_variance: float, preference: float, strength: float = 1.0
    ):
        values = (prior_mean, prior_variance, preference, strength)
        if any(isinstance(value, bool) for value in values) or not all(
            math.isfinite(float(value)) for value in values
        ):
            raise ValueError("surprise tracker parameters must be finite")
        if prior_variance <= 0:
            raise ValueError("prior_variance must be positive")
        if strength < 0:
            raise ValueError("strength cannot be negative")
        self.prior_mean = float(prior_mean)
        self.prior_variance = float(prior_variance)
        self.preference = float(preference)
        self.strength = float(strength)
        self._count = 0
        self._mean = self.prior_mean

    def update(self, observation: float) -> SurpriseObservation:
        """Absorb one observation and report the surprise it incurred.

        The empirical surprise is computed *before* the running mean absorbs the
        new observation: it measures how surprising the observation is under the
        prior (the current running mean). The reported ``posterior_mean`` is the
        updated mean *after* absorption.
        """
        observation = float(observation)
        if not math.isfinite(observation):
            raise ValueError("observation must be finite")
        prior_mean = self._mean
        empirical = 0.5 * ((observation - prior_mean) ** 2 / self.prior_variance)
        self._count += 1
        self._mean += (observation - self._mean) / self._count
        preference = (
            self.strength * 0.5 * ((observation - self.preference) ** 2 / self.prior_variance)
        )
        return SurpriseObservation(
            observation,
            float(empirical),
            float(preference),
            float(empirical + preference),
            float(self._mean),
        )


def homeostatic_free_energy(values: Mapping[str, float], config: BiofirmConfig) -> float:
    """Compute squared normalized deviation from configured ecological targets."""

    if set(values) != set(config.variables):
        missing = sorted(set(config.variables) - set(values))
        extra = sorted(set(values) - set(config.variables))
        raise ValueError(f"value keys do not match config; missing={missing}, extra={extra}")
    deviations: list[float] = []
    for name, variable in config.variables.items():
        value = values[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ValueError(f"value {name!r} must be finite")
        deviations.append(((float(value) - variable.target) / variable.span) ** 2)
    return float(0.5 * sum(deviations))


def summarize_records(records: Iterable[Mapping[str, object]]) -> dict[str, float]:
    """Summarize serialized simulation records without requiring pandas."""

    rows = list(records)
    if not rows:
        raise ValueError("at least one record is required")
    errors: list[float] = []
    efforts: list[float] = []
    for index, row in enumerate(rows):
        metrics_value = row.get("metrics") if isinstance(row, Mapping) else None
        if not isinstance(metrics_value, Mapping):
            raise ValueError(f"record {index} has no metrics object")
        metrics: Mapping[str, object] = metrics_value
        error = metrics.get("homeostatic_error")
        effort = metrics.get("control_effort")
        if (
            isinstance(error, bool)
            or not isinstance(error, (int, float))
            or not math.isfinite(float(error))
            or isinstance(effort, bool)
            or not isinstance(effort, (int, float))
            or not math.isfinite(float(effort))
        ):
            raise ValueError(f"record {index} has invalid metrics")
        errors.append(float(error))
        efforts.append(float(effort))
    return {
        "records": float(len(rows)),
        "mean_homeostatic_error": float(np.mean(errors)),
        "max_homeostatic_error": float(np.max(errors)),
        "total_control_effort": float(np.sum(efforts)),
    }


@dataclass(frozen=True)
class TokenLedgerEntry:
    """One allocation round's auditable accounting.

    Fields describe the requested, reserved, allocated, and remainder
    quantities precisely:

    - ``requested``: whole tokens made available for allocation this round
      (the remaining budget after previously allocated and reserved tokens).
    - ``reserved``: whole tokens withheld as reserve this round.
    - ``allocated``: whole tokens actually granted across recipients.
    - ``remainder``: the whole-token remainder that the largest-remainder rule
      distributes as one extra token per the largest fractional remainder(s)
      before the round is finalized.
    """

    coalition: tuple[str, ...]
    requested: int
    allocated: int
    reserve: int
    remainder: float


class TokenLedger:
    """Auditable largest-remainder allocation ledger with explicit reserve accounting."""

    def __init__(self, total_tokens: int, reserve_rate: float = 0.0):
        if isinstance(total_tokens, bool) or not isinstance(total_tokens, int) or total_tokens < 0:
            raise ValueError("total_tokens must be a non-negative integer")
        if not math.isfinite(float(reserve_rate)) or not 0 <= reserve_rate < 1:
            raise ValueError("reserve_rate must be in [0, 1)")
        self.total_tokens = int(total_tokens)
        self.reserve_rate = float(reserve_rate)
        self.entries: list[TokenLedgerEntry] = []

    @property
    def reserved_tokens(self) -> int:
        return sum(entry.reserve for entry in self.entries)

    @property
    def allocated_tokens(self) -> int:
        return sum(entry.allocated for entry in self.entries)

    def allocate(
        self, values: Mapping[str, float], coalition: Iterable[str] = ()
    ) -> dict[str, int]:
        if not values:
            raise ValueError("at least one recipient is required")
        if any(
            not isinstance(key, str)
            or not key
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) < 0
            for key, value in values.items()
        ):
            raise ValueError("allocation weights must be finite and non-negative")
        weight_sum = float(sum(values.values()))
        if weight_sum <= 0:
            raise ValueError("allocation weights must have a positive sum")
        remaining = self.total_tokens - self.allocated_tokens - self.reserved_tokens
        reserve = int(math.floor(remaining * self.reserve_rate))
        distributable = remaining - reserve
        quotas = {key: distributable * float(value) / weight_sum for key, value in values.items()}
        allocation = {key: int(math.floor(quota)) for key, quota in quotas.items()}
        remainder_tokens = distributable - sum(allocation.values())
        order = sorted(quotas, key=lambda key: (-(quotas[key] - allocation[key]), key))
        for key in order[:remainder_tokens]:
            allocation[key] += 1
        self.entries.append(
            TokenLedgerEntry(
                tuple(sorted(coalition)),
                distributable,
                sum(allocation.values()),
                reserve,
                float(remainder_tokens),
            )
        )
        return allocation


class ShapleyAllocator:
    """Exact Shapley allocation for explicitly supported coalition sizes."""

    def __init__(self, max_players: int = 10):
        if isinstance(max_players, bool) or not isinstance(max_players, int) or max_players < 1:
            raise ValueError("max_players must be positive")
        self.max_players = max_players

    def values(
        self,
        players: Iterable[str],
        characteristic: Mapping[frozenset[str], float] | Callable[[frozenset[str]], float],
    ) -> dict[str, float]:
        ordered = tuple(dict.fromkeys(players))
        if any(not isinstance(player, str) or not player.strip() for player in ordered):
            raise ValueError("players must be non-empty strings")
        if len(ordered) > self.max_players:
            raise ValueError(
                f"exact Shapley allocation supports at most {self.max_players} players"
            )

        def value(coalition: frozenset[str]) -> float:
            result = (
                characteristic(coalition)
                if callable(characteristic)
                else characteristic.get(coalition)
            )
            if result is None or not math.isfinite(float(result)):
                raise ValueError(f"missing or non-finite coalition value for {sorted(coalition)}")
            return float(result)

        factorial = math.factorial
        player_count = len(ordered)
        allocations: dict[str, float] = {}
        all_players = frozenset(ordered)
        for player in ordered:
            others = all_players - {player}
            contribution = 0.0
            for size in range(player_count):
                for subset_tuple in itertools.combinations(others, size):
                    subset = frozenset(subset_tuple)
                    coefficient = (
                        factorial(size)
                        * factorial(player_count - size - 1)
                        / factorial(player_count)
                    )
                    contribution += coefficient * (value(subset | {player}) - value(subset))
            allocations[player] = contribution
        return allocations
