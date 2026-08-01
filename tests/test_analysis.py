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


def test_token_ledger_conserves_and_accounts_non_uniform_allocation() -> None:
    ledger = TokenLedger(100, reserve_rate=0.1)
    tokens = ledger.allocate({"a": 3.0, "b": 1.0})
    # reserve (10) + allocated (90) exactly account for the 100-token budget.
    assert ledger.reserved_tokens + ledger.allocated_tokens == 100
    assert sum(tokens.values()) == ledger.allocated_tokens == 90
    entry = ledger.entries[0]
    assert entry.reserve == 10
    assert entry.requested == 90
    assert entry.allocated == 90


def test_empirical_surprise_uses_pre_update_prior() -> None:
    tracker = SurpriseTracker(0.0, 1.0, 0.0)
    first = tracker.update(2.0)
    second = tracker.update(2.0)
    assert first.posterior_mean == 2.0
    # The second observation's surprise is computed against the posterior of
    # the first update (i.e. before this observation is absorbed), not after.
    assert second.empirical_surprise == 0.0
    assert second.posterior_mean == 2.0
