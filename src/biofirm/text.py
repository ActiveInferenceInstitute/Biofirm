"""Deterministic bioregion text extraction and optional document utilities."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import BiofirmConfig
from .io import atomic_write_json


class DocumentDependencyError(RuntimeError):
    """Raised when an optional document dependency is needed but unavailable."""


@dataclass(frozen=True)
class EvidenceSpan:
    category: str
    value: str
    start: int
    end: int
    text: str
    confidence: float


@dataclass(frozen=True)
class BioregionProfile:
    source_sha256: str
    resources: Mapping[str, tuple[EvidenceSpan, ...]]
    variables: Mapping[str, Mapping[str, Any]]
    evidence: tuple[EvidenceSpan, ...]
    ambiguities: tuple[tuple[int, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_sha256": self.source_sha256,
            "resources": {
                key: [span.__dict__ for span in spans] for key, spans in self.resources.items()
            },
            "variables": {key: dict(value) for key, value in self.variables.items()},
            "evidence": [span.__dict__ for span in self.evidence],
            "ambiguities": [{"offset": offset, "text": text} for offset, text in self.ambiguities],
        }


DEFAULT_RESOURCE_LEXICON: Mapping[str, tuple[str, ...]] = {
    "water": ("river", "rivers", "wetland", "wetlands", "lake", "aquifer", "water"),
    "forest": ("forest", "forests", "woodland", "mangrove"),
    "grassland": ("grassland", "prairie", "savanna", "steppe"),
    "coast": ("coast", "coastal", "shore", "estuary", "reef"),
    "agriculture": ("crop", "crops", "farmland", "agriculture", "pasture"),
}

_NUMBER = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
_RANGE_PATTERNS = (
    re.compile(rf"(?P<low>{_NUMBER})\s*(?:-|to|–)\s*(?P<high>{_NUMBER})\s*(?P<unit>[a-zA-Z%°/]+)?"),
    re.compile(
        rf"between\s+(?P<low>{_NUMBER})\s+and\s+(?P<high>{_NUMBER})\s*(?P<unit>[a-zA-Z%°/]+)?"
    ),
)
# Character-position epsilon used to decide when a numeric range is equidistant
# from two different configured variables (i.e., attribution is ambiguous).
_AMBIGUITY_EPS = 5


def _alias_pattern(alias: str) -> str:
    """Match configured snake-case aliases in natural-language spacing too."""

    return re.escape(alias).replace("_", r"[\s_-]+")


class BioregionTextProcessor:
    """Extract configured resources and numeric ranges without an LLM."""

    def __init__(
        self,
        config: BiofirmConfig,
        resource_lexicon: Mapping[str, tuple[str, ...]] | None = None,
    ):
        self.config = config
        self.resource_lexicon = resource_lexicon or DEFAULT_RESOURCE_LEXICON
        self._aliases = {
            alias.casefold(): name
            for name, variable in config.variables.items()
            for alias in (name, *variable.aliases)
        }

    def process(self, description: str) -> BioregionProfile:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        source_hash = hashlib.sha256(description.encode("utf-8")).hexdigest()
        resources: dict[str, list[EvidenceSpan]] = {key: [] for key in self.resource_lexicon}
        evidence: list[EvidenceSpan] = []
        lowered = description.lower()
        for category, terms in self.resource_lexicon.items():
            for term in terms:
                for match in re.finditer(rf"\b{re.escape(term.lower())}\b", lowered):
                    span = EvidenceSpan(
                        category,
                        term,
                        match.start(),
                        match.end(),
                        description[match.start() : match.end()],
                        1.0,
                    )
                    resources[category].append(span)
                    evidence.append(span)
        variables: dict[str, Mapping[str, Any]] = {}
        ambiguities: list[tuple[int, str]] = []
        sentences = list(re.finditer(r"[^.!?]+[.!?]?", description))
        for sentence_match in sentences:
            sentence = sentence_match.group(0)
            sentence_start = sentence_match.start()
            aliases = [
                (alias, variable, alias_match)
                for alias, variable in self._aliases.items()
                for alias_match in re.finditer(rf"\b{_alias_pattern(alias)}\b", sentence.casefold())
            ]
            ranges: list[re.Match[str]] = []
            for pattern in _RANGE_PATTERNS:
                ranges.extend(pattern.finditer(sentence))
            if not aliases or not ranges:
                continue
            # Attribute every range to the single nearest variable alias so one
            # bare numeric range is never silently reused for several variables.
            range_assignments: list[tuple[re.Match[str], str, str, int]] = []
            for matched_range in ranges:
                candidates = sorted(
                    (
                        (abs(matched_range.start() - alias_match.start()), variable, alias)
                        for alias, variable, alias_match in aliases
                    ),
                    key=lambda item: item[0],
                )
                nearest = candidates[0]
                second: tuple[int, str, str] | None = None
                for distance, variable, _alias in candidates[1:]:
                    if variable != nearest[1]:
                        second = (distance, variable, "")
                        break
                if second is not None and abs(second[0] - nearest[0]) <= _AMBIGUITY_EPS:
                    ambiguities.append(
                        (sentence_start + matched_range.start(), matched_range.group(0))
                    )
                    continue
                range_assignments.append((matched_range, nearest[1], nearest[2], nearest[0]))
            # Keep only the closest range per variable, preserving the
            # one-entry-per-variable profile shape for unambiguous matches.
            best_by_variable: dict[str, tuple[re.Match[str], str, str, int]] = {}
            for matched_range, variable, alias, distance in range_assignments:
                current = best_by_variable.get(variable)
                if current is None or distance < current[3]:
                    best_by_variable[variable] = (matched_range, variable, alias, distance)
            for variable, (matched_range, _variable, alias, distance) in best_by_variable.items():
                low = float(matched_range.group("low"))
                high = float(matched_range.group("high"))
                if low > high:
                    low, high = high, low
                unit = matched_range.group("unit") or self.config.variables[variable].unit
                confidence = max(0.0, min(1.0, 1.0 - distance / 60.0))
                variables[variable] = {
                    "minimum": low,
                    "maximum": high,
                    "unit": unit,
                    "source_alias": alias,
                    "confidence": confidence,
                    "ambiguous": False,
                }
                start = sentence_start + matched_range.start()
                span = EvidenceSpan(
                    "variable-range",
                    variable,
                    start,
                    sentence_start + matched_range.end(),
                    sentence.strip(),
                    confidence,
                )
                evidence.append(span)
        return BioregionProfile(
            source_sha256=source_hash,
            resources={key: tuple(value) for key, value in resources.items()},
            variables=variables,
            evidence=tuple(
                sorted(evidence, key=lambda span: (span.start, span.end, span.category))
            ),
            ambiguities=tuple(ambiguities),
        )

    def to_configuration(self, profile: BioregionProfile) -> dict[str, Any]:
        """Return a validated partial override; never invent missing measurements."""

        return {
            "source_sha256": profile.source_sha256,
            "variables": {name: dict(values) for name, values in profile.variables.items()},
            "resources": {
                category: [span.value for span in spans]
                for category, spans in profile.resources.items()
                if spans
            },
        }


def extract_text(path: str | Path) -> str:
    """Read UTF-8 text or PDF text with a clear optional-dependency error."""

    source = Path(path)
    if source.suffix.lower() != ".pdf":
        return source.read_text(encoding="utf-8")
    try:
        import pdfplumber
    except ImportError as exc:
        raise DocumentDependencyError(
            "PDF extraction requires pdfplumber; install biofirm[documents]"
        ) from exc
    with pdfplumber.open(source) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError(f"PDF {source} contains no extractable text")
    return text


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    try:
        import tiktoken
    except ImportError as exc:
        raise DocumentDependencyError(
            "token counting requires tiktoken; install biofirm[documents]"
        ) from exc
    return len(tiktoken.get_encoding(encoding_name).encode(text))


def dump_profile(profile: BioregionProfile, output: str | Path) -> Path:
    return atomic_write_json(output, profile.to_dict())
