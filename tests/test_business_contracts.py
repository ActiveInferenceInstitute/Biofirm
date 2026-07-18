from __future__ import annotations

import json

import pytest

from biofirm.business import (
    ActionDefinition,
    BusinessDecision,
    BusinessDecisionError,
    CommitteeConfig,
    CommitteeRole,
    load_committee,
)
from biofirm.config import load_config


def _action(config, name: str = "action", cost: float = 1.0) -> dict:  # type: ignore[no-untyped-def]
    return {
        "name": name,
        "controls": {variable: 0.0 for variable in config.variables},
        "cost": cost,
        "risk": 0.1,
        "ecological_effects": {variable: 0.0 for variable in config.variables},
    }


def _committee(config, **overrides) -> dict:  # type: ignore[no-untyped-def]
    value = {
        "budget": 10.0,
        "roles": [{"name": "role", "weight": 1.0, "priorities": {}}],
        "actions": [_action(config)],
    }
    value.update(overrides)
    return value


def test_business_contracts_reject_invalid_direct_values() -> None:
    with pytest.raises(BusinessDecisionError, match="action.name"):
        ActionDefinition("", {}, 1.0, 0.1, {})
    with pytest.raises(BusinessDecisionError, match="risk"):
        ActionDefinition("a", {}, 1.0, 2.0, {})
    with pytest.raises(BusinessDecisionError, match="role.name"):
        CommitteeRole("", 1.0, {})
    with pytest.raises(BusinessDecisionError, match="weights"):
        CommitteeConfig(1.0, (CommitteeRole("r", 0.0, {}),), (ActionDefinition("a", {}, 1, 0, {}),))
    with pytest.raises(BusinessDecisionError, match="decision rationale"):
        BusinessDecision("a", 1.0, 1.0, 0.1, {}, ())
    with pytest.raises(BusinessDecisionError, match="controls"):
        ActionDefinition("a", None, 1.0, 0.1, {})  # type: ignore[arg-type]
    with pytest.raises(BusinessDecisionError, match="priorities"):
        CommitteeRole("r", 1.0, None)  # type: ignore[arg-type]
    with pytest.raises(BusinessDecisionError, match="votes"):
        BusinessDecision("a", 1.0, 1.0, 0.1, None, ("r",))  # type: ignore[arg-type]


def test_committee_schema_rejects_missing_and_duplicate_entries() -> None:
    config = load_config()
    with pytest.raises(BusinessDecisionError, match="missing fields"):
        CommitteeConfig.from_dict({}, config)
    with pytest.raises(BusinessDecisionError, match="roles"):
        CommitteeConfig.from_dict(_committee(config, roles=[]), config)
    with pytest.raises(BusinessDecisionError, match="actions"):
        CommitteeConfig.from_dict(_committee(config, actions=[]), config)
    duplicate_roles = [{"name": "role", "weight": 1.0, "priorities": {}}] * 2
    with pytest.raises(BusinessDecisionError, match="role names"):
        CommitteeConfig.from_dict(_committee(config, roles=duplicate_roles), config)
    duplicate_actions = [_action(config), _action(config)]
    with pytest.raises(BusinessDecisionError, match="action names"):
        CommitteeConfig.from_dict(_committee(config, actions=duplicate_actions), config)


def test_committee_rejects_incomplete_controls_and_budget_exhaustion(tmp_path) -> None:  # type: ignore[no-untyped-def]
    config = load_config()
    incomplete = _action(config)
    incomplete["controls"].pop("biodiversity")
    with pytest.raises(BusinessDecisionError, match="every configured"):
        ActionDefinition.from_dict(incomplete, config)
    too_expensive = _committee(config, budget=0.0, actions=[_action(config, cost=1.0)])
    committee_path = tmp_path / "committee.json"
    committee_path.write_text(json.dumps(too_expensive), encoding="utf-8")
    committee = load_committee(committee_path, config)
    from biofirm.business import BusinessCommittee

    with pytest.raises(BusinessDecisionError, match="no action"):
        BusinessCommittee(config, committee).evaluate({name: 50.0 for name in config.variables})


def test_business_parsers_reject_malformed_actions_and_roles() -> None:
    config = load_config()
    with pytest.raises(BusinessDecisionError, match="non-empty strings"):
        ActionDefinition("action", {"": 1.0}, 1.0, 0.1, {})
    with pytest.raises(BusinessDecisionError, match="missing fields"):
        ActionDefinition.from_dict({}, config)
    with pytest.raises(BusinessDecisionError, match="object"):
        ActionDefinition.from_dict([], config)  # type: ignore[arg-type]
    with pytest.raises(BusinessDecisionError, match="unknown fields"):
        ActionDefinition.from_dict({**_action(config), "extra": 1}, config)
    with pytest.raises(BusinessDecisionError, match="exceeds"):
        oversized = _action(config)
        oversized["controls"]["biodiversity"] = 999.0
        ActionDefinition.from_dict(oversized, config)
    with pytest.raises(BusinessDecisionError, match="object"):
        CommitteeConfig.from_dict([], config)  # type: ignore[arg-type]
    with pytest.raises(BusinessDecisionError, match="each committee role"):
        CommitteeConfig.from_dict(_committee(config, roles=[1]), config)
    with pytest.raises(BusinessDecisionError, match="unknown fields"):
        CommitteeConfig.from_dict(
            _committee(config, roles=[{"name": "r", "weight": 1, "priorities": {}, "extra": 1}]),
            config,
        )
