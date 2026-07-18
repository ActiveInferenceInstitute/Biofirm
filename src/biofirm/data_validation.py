"""Deterministic validation and provenance summaries for repository source data."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DataValidationError(ValueError):
    """Raised when an authoritative source dataset is malformed."""


@dataclass(frozen=True)
class DataValidationReport:
    """Serializable validation result for the repository's source datasets."""

    one_earth_regions: int
    biofirm_regions: int
    california_regions: int
    biofirm_prompts: int
    one_earth_prompts: int
    source_sha256: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": True,
            "counts": {
                "one_earth_regions": self.one_earth_regions,
                "biofirm_regions": self.biofirm_regions,
                "california_regions": self.california_regions,
                "biofirm_prompts": self.biofirm_prompts,
                "one_earth_prompts": self.one_earth_prompts,
            },
            "source_sha256": dict(self.source_sha256),
        }


def validate_repository_data(
    *,
    one_earth_path: str | Path = "One_Earth/oneearth_bioregion_ecoregions.json",
    biofirm_regions_path: str | Path = "Bio_Perplexity/Biofirm_Regions.json",
    california_regions_path: str | Path = "Bio_Perplexity/CA_Biofirm_Regions.json",
    biofirm_prompts_path: str | Path = "Bio_Perplexity/Biofirm_System_Prompts.json",
    one_earth_prompts_path: str | Path = "One_Earth/OneEarth_System_Prompts.json",
) -> DataValidationReport:
    paths = {
        "one_earth_regions": Path(one_earth_path),
        "biofirm_regions": Path(biofirm_regions_path),
        "california_regions": Path(california_regions_path),
        "biofirm_prompts": Path(biofirm_prompts_path),
        "one_earth_prompts": Path(one_earth_prompts_path),
    }
    raw = {name: _read_json(path) for name, path in paths.items()}
    one_earth = _leaf_regions(raw["one_earth_regions"])
    if len(one_earth) != 185:
        raise DataValidationError(f"expected 185 One Earth leaf bioregions, found {len(one_earth)}")
    ids = [region.get("_id") for region in one_earth]
    names = [region.get("name") for region in one_earth]
    if any(not isinstance(value, str) or not value.strip() for value in ids + names):
        raise DataValidationError("One Earth leaf bioregions require non-empty _id and name")
    if len(set(ids)) != len(ids) or len(set(names)) != len(names):
        raise DataValidationError("One Earth leaf bioregion IDs and names must be unique")
    for region in one_earth:
        for field in ("parentId", "value", "images"):
            if field not in region:
                raise DataValidationError(f"One Earth region {region.get('_id')!r} lacks {field}")

    biofirm_regions = _region_map(raw["biofirm_regions"], "Bio_Perplexity/Biofirm_Regions.json")
    california_regions = _region_map(
        raw["california_regions"], "Bio_Perplexity/CA_Biofirm_Regions.json", california=True
    )
    biofirm_prompts = _prompt_map(raw["biofirm_prompts"], "Bio_Perplexity prompts")
    one_earth_prompts = _prompt_map(raw["one_earth_prompts"], "One Earth prompts")
    return DataValidationReport(
        one_earth_regions=len(one_earth),
        biofirm_regions=len(biofirm_regions),
        california_regions=len(california_regions),
        biofirm_prompts=len(biofirm_prompts),
        one_earth_prompts=len(one_earth_prompts),
        source_sha256={name: _sha256(path) for name, path in paths.items()},
    )


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DataValidationError(f"could not read valid UTF-8 JSON from {path}") from exc


def _leaf_regions(raw: Any) -> list[Mapping[str, Any]]:
    if not isinstance(raw, list):
        raise DataValidationError("One Earth region source must be a list")
    leaves: list[Mapping[str, Any]] = []

    def visit(node: Any) -> None:
        if not isinstance(node, Mapping):
            raise DataValidationError("One Earth hierarchy contains a non-object node")
        children = node.get("children")
        if isinstance(children, list) and children:
            for child in children:
                visit(child)
            return
        leaves.append(node)

    for node in raw:
        visit(node)
    return leaves


def _region_map(raw: Any, label: str, *, california: bool = False) -> dict[str, Mapping[str, Any]]:
    if not isinstance(raw, Mapping) or not raw:
        raise DataValidationError(f"{label} must be a non-empty object")
    result: dict[str, Mapping[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(value, Mapping):
            raise DataValidationError(f"{label} contains an invalid region entry")
        if value.get("id") != key:
            raise DataValidationError(f"{label} key {key!r} does not match its id")
        required_fields = (
            ("state", "county", "region_type") if california else ("state", "county", "country")
        )
        for field in required_fields:
            if not isinstance(value.get(field), str) or not value[field].strip():
                raise DataValidationError(f"{label} region {key!r} lacks {field}")
        result[key] = value
    return result


def _prompt_map(raw: Any, label: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(raw, Mapping) or not raw:
        raise DataValidationError(f"{label} must be a non-empty object")
    result: dict[str, Mapping[str, Any]] = {}
    for key, value in raw.items():
        if key == "config":
            if not isinstance(value, Mapping) or not isinstance(value.get("models"), Mapping):
                raise DataValidationError(f"{label} config requires models")
            continue
        if not isinstance(value, Mapping) or not isinstance(value.get("description"), str):
            raise DataValidationError(f"{label} prompt {key!r} lacks description")
        if not value["description"].strip():
            raise DataValidationError(f"{label} prompt {key!r} has empty description")
        result[str(key)] = value
    if not result:
        raise DataValidationError(f"{label} contains no prompts")
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
