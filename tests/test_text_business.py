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


def test_single_range_is_never_attributed_to_two_variables() -> None:
    config = load_config()
    processor = BioregionTextProcessor(config)
    profile = processor.process("biodiversity and soil_moisture between 40 and 80 index.")
    # The bare range is owned by the single nearest variable, not both.
    assert len(profile.variables) == 1
    assert "biodiversity" not in profile.variables or "soil_moisture" not in profile.variables
    assert not profile.ambiguities


def test_ambiguous_range_is_reported_and_not_assigned() -> None:
    config = load_config()
    profile = BioregionTextProcessor(config).process("soil_moisture 40 to 50 biodiversity")
    # Nearly equidistant from two variables -> attributed to neither, reported.
    assert profile.ambiguities
    assert profile.variables == {}


def test_nearby_range_gets_high_confidence_span() -> None:
    config = load_config()
    profile = BioregionTextProcessor(config).process("biodiversity between 40 and 80 index.")
    assert profile.variables["biodiversity"]["confidence"] > 0.5
    range_spans = [span for span in profile.evidence if span.category == "variable-range"]
    assert range_spans


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


def test_committee_ties_break_deterministically_by_name() -> None:
    config = load_config()
    zero = {name: 0.0 for name in config.variables}
    committee = CommitteeConfig.from_dict(
        {
            "budget": 1.0,
            "roles": [
                {
                    "name": "role",
                    "weight": 1.0,
                    "priorities": {name: 1.0 for name in config.variables},
                }
            ],
            "actions": [
                {
                    "name": "alpha",
                    "controls": zero,
                    "cost": 0.0,
                    "risk": 0.0,
                    "ecological_effects": zero,
                },
                {
                    "name": "beta",
                    "controls": zero,
                    "cost": 0.0,
                    "risk": 0.0,
                    "ecological_effects": zero,
                },
            ],
        },
        config,
    )
    # Zero-effect, zero-cost actions all score identically; the equality rule is
    # max((score, name)), so ties resolve deterministically to the
    # lexicographically greatest name.
    first = BusinessCommittee(config, committee).evaluate({name: 50.0 for name in config.variables})
    second = BusinessCommittee(config, committee).evaluate(
        {name: 50.0 for name in config.variables}
    )
    assert first.action == "beta"
    assert second.action == first.action


def test_business_action_id_matches_simulation_contract() -> None:
    import biofirm.business as business
    import biofirm.simulation as simulation

    for control in (0.0, 1e-13, -1e-13, 1.5, -1.5):
        assert business._action_id(control) == simulation._action_id(control)
