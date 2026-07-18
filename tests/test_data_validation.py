from __future__ import annotations

import json

import pytest

from biofirm.data_validation import DataValidationError, validate_repository_data


def test_repository_data_validation_reports_authoritative_sources() -> None:
    report = validate_repository_data()
    assert report.one_earth_regions == 185
    assert report.biofirm_regions == 67
    assert report.california_regions == 3
    assert len(report.source_sha256) == 5


def test_repository_data_validation_rejects_invalid_region_source(tmp_path) -> None:  # type: ignore[no-untyped-def]
    invalid = tmp_path / "regions.json"
    invalid.write_text(json.dumps({"R1": {"id": "wrong"}}), encoding="utf-8")
    with pytest.raises(DataValidationError, match="could not read|does not match"):
        validate_repository_data(biofirm_regions_path=invalid)


def test_repository_data_validation_rejects_malformed_hierarchy_and_prompts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    invalid_hierarchy = tmp_path / "hierarchy.json"
    invalid_hierarchy.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(DataValidationError, match="must be a list"):
        validate_repository_data(one_earth_path=invalid_hierarchy)

    malformed_prompt = tmp_path / "prompts.json"
    malformed_prompt.write_text(json.dumps({"0": {"description": " "}}), encoding="utf-8")
    with pytest.raises(DataValidationError, match="empty description"):
        validate_repository_data(biofirm_prompts_path=malformed_prompt)

    invalid_json = tmp_path / "broken.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(DataValidationError, match="valid UTF-8 JSON"):
        validate_repository_data(one_earth_prompts_path=invalid_json)
