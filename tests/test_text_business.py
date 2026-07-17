from __future__ import annotations

import json

import pytest

from biofirm.business import BusinessCommittee, BusinessDecisionError, CommitteeConfig
from biofirm.config import load_config
from biofirm.text import BioregionTextProcessor


def test_text_extraction_has_hashes_ranges_and_evidence() -> None:
    config = load_config()
    processor = BioregionTextProcessor(config)
    profile = processor.process(
        "The river and forest support biodiversity between 40 and 80 index."
    )
    assert len(profile.source_sha256) == 64
    assert profile.resources["water"]
    assert profile.variables["biodiversity"]["minimum"] == 40.0
    assert profile.evidence
    assert json.loads(json.dumps(profile.to_dict()))["source_sha256"] == profile.source_sha256


def test_business_policy_is_deterministic_and_auditable() -> None:
    config = load_config()
    committee = BusinessCommittee(config)
    first = committee.evaluate({name: 40.0 for name in config.variables})
    second = committee.evaluate({name: 40.0 for name in config.variables})
    assert first == second
    assert first.action
    assert first.rationale


def test_business_policy_rejects_extra_state_and_invalid_action_schema() -> None:
    config = load_config()
    committee = BusinessCommittee(config)
    with pytest.raises(BusinessDecisionError, match="extra"):
        committee.evaluate({**{name: 40.0 for name in config.variables}, "unexpected": 1.0})
    with pytest.raises(BusinessDecisionError, match="action.name"):
        CommitteeConfig.from_dict(
            {
                "budget": 1,
                "roles": [{"name": "ecology", "weight": 1, "priorities": {}}],
                "actions": [
                    {
                        "name": " ",
                        "controls": {},
                        "cost": 0,
                        "risk": 0,
                        "ecological_effects": {},
                    }
                ],
            },
            config,
        )
