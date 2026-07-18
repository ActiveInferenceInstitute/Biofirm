from __future__ import annotations

import pytest

from biofirm.analysis import ShapleyAllocator, SurpriseTracker, TokenLedger, homeostatic_free_energy
from biofirm.config import load_config


def test_free_energy_and_surprise_are_numeric() -> None:
    config = load_config()
    assert homeostatic_free_energy({name: 50.0 for name in config.variables}, config) == 0.0
    tracker = SurpriseTracker(0.0, 1.0, 0.0)
    observation = tracker.update(2.0)
    assert observation.empirical_surprise == 2.0
    assert observation.total_surprise >= observation.empirical_surprise


def test_exact_shapley_and_largest_remainder_ledger() -> None:
    players = ("a", "b", "c")
    coalition_values = {
        frozenset(): 0.0,
        frozenset({"a"}): 1.0,
        frozenset({"b"}): 2.0,
        frozenset({"c"}): 3.0,
        frozenset({"a", "b"}): 4.0,
        frozenset({"a", "c"}): 5.0,
        frozenset({"b", "c"}): 6.0,
        frozenset(players): 10.0,
    }
    allocation = ShapleyAllocator().values(players, coalition_values)
    assert sum(allocation.values()) == 10.0
    ledger = TokenLedger(10)
    tokens = ledger.allocate({"a": 1.0, "b": 1.0, "c": 1.0})
    assert sum(tokens.values()) == 10
    assert ledger.allocated_tokens == 10


def test_allocation_contracts_reject_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        TokenLedger(1.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        SurpriseTracker(0.0, 1.0, 0.0).update(float("nan"))
    with pytest.raises(ValueError, match="at most"):
        ShapleyAllocator(max_players=1).values(("a", "b"), {frozenset(): 0.0})


def test_analysis_services_reject_invalid_shapes_and_weights() -> None:
    config = load_config()
    with pytest.raises(ValueError, match="keys"):
        homeostatic_free_energy({"biodiversity": 1.0}, config)
    with pytest.raises(ValueError, match="finite"):
        homeostatic_free_energy({name: float("nan") for name in config.variables}, config)
    with pytest.raises(ValueError, match="record"):
        from biofirm.analysis import summarize_records

        summarize_records([])
    with pytest.raises(ValueError, match="positive sum"):
        TokenLedger(10).allocate({"a": 0.0})
    with pytest.raises(ValueError, match="weights"):
        TokenLedger(10).allocate({"a": -1.0})
    with pytest.raises(ValueError, match="coalition"):
        ShapleyAllocator().values(("a",), {})
