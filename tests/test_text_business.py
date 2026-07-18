from __future__ import annotations

import json

import pytest

from biofirm.business import BusinessCommittee, BusinessDecisionError, CommitteeConfig
from biofirm.config import load_config
from biofirm.text import (
    BioregionTextProcessor,
    DocumentDependencyError,
    count_tokens,
    dump_profile,
    extract_text,
)


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


def test_text_extraction_pairs_nearest_ranges_and_supports_signed_values() -> None:
    config = load_config()
    processor = BioregionTextProcessor(config)
    profile = processor.process(
        "Biodiversity ranges from -10 to 20 index. Soil moisture ranges from 30 to 40 %."
    )
    assert profile.variables["biodiversity"]["minimum"] == -10.0
    assert profile.variables["soil_moisture"]["maximum"] == 40.0


def test_text_document_helpers_and_dependency_errors(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "region.txt"
    source.write_text("A river supports biodiversity between 10 and 20 index.", encoding="utf-8")
    assert "river" in extract_text(source)
    profile = BioregionTextProcessor(load_config()).process(source.read_text(encoding="utf-8"))
    output = dump_profile(profile, tmp_path / "profile.json")
    assert output.stat().st_size > 0
    assert profile.to_dict()["variables"]
    with pytest.raises(ValueError, match="description"):
        BioregionTextProcessor(load_config()).process(" ")
    monkeypatch.setitem(__import__("sys").modules, "pdfplumber", None)
    with pytest.raises(DocumentDependencyError, match="pdfplumber"):
        extract_text(tmp_path / "region.pdf")
    monkeypatch.setitem(__import__("sys").modules, "tiktoken", None)
    with pytest.raises(DocumentDependencyError, match="token counting"):
        count_tokens("river")


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
