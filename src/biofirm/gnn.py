"""Generalized Notation Notation specification loading and conformance checks.

The generative model of the active-inference controller is specified in
``models/biofirm_ecosystem_variable.gnn.md`` using Generalized Notation
Notation (GNN v1.1). This module parses that repository specification without
depending on the upstream ``gnn`` package, exposes the declared structure, and
compares it with the matrices the package actually builds in
:mod:`biofirm.pymdp`.

The specification file is a repository artifact, so this module resolves it
relative to the checkout root; when the package is installed outside its
checkout, :func:`load_spec` reports the missing file instead of guessing.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import numpy as np
from numpy.typing import NDArray

from .pymdp import ActiveInferenceMatrices, build_active_inference_matrices

FloatArray = NDArray[np.floating[Any]]

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPEC_PATH: Final[Path] = REPO_ROOT / "models" / "biofirm_ecosystem_variable.gnn.md"

EXPECTED_SECTION: Final[str] = "ActInfBiofirmEcosystemVariable"
EXPECTED_MODEL_ID: Final[str] = "biofirm_ecosystem_variable"
EXPECTED_EDGES: Final[frozenset[tuple[str, str, str]]] = frozenset(
    {
        ("D_bin", ">", "s_bin"),
        ("s_bin", ">", "A_level"),
        ("A_level", ">", "o_level"),
        ("s_bin", ">", "B_bin"),
        ("u_control", ">", "B_bin"),
        ("B_bin", ">", "s_bin"),
        ("C_level", "-", "o_level"),
        ("G", ">", "π_control"),
        ("π_control", ">", "u_control"),
    }
)


class GNNSpecError(ValueError):
    """Raised when the GNN specification is missing or malformed."""


@dataclass(frozen=True)
class GNNSpec:
    """The parsed structure of a GNN specification file."""

    section: str
    version: str
    model_name: str
    variables: Mapping[str, tuple[int, ...]]
    connections: tuple[tuple[str, str, str], ...]
    initial_parameterization: Mapping[str, str]
    model_parameters: Mapping[str, str]

    def shape(self, name: str) -> tuple[int, ...]:
        """Return the declared dimensions of a state-space variable."""

        try:
            return self.variables[name]
        except KeyError as exc:
            raise GNNSpecError(f"{name} is not declared in StateSpaceBlock") from exc

    def integer_parameter(self, key: str) -> int:
        """Return a declared integer model parameter."""

        raw = self.text_parameter(key)
        try:
            return int(raw)
        except ValueError as exc:
            raise GNNSpecError(f"model parameter {key} must be an integer, got {raw!r}") from exc

    def text_parameter(self, key: str) -> str:
        """Return a declared model parameter as text."""

        try:
            return self.model_parameters[key]
        except KeyError as exc:
            raise GNNSpecError(f"model parameter {key} is not declared") from exc

    def edges(self) -> frozenset[tuple[str, str, str]]:
        """Return the declared connections as ``(source, operator, target)`` triples."""

        return frozenset(self.connections)


_SECTION_PATTERN: Final = re.compile(r"^##\s+(?P<name>.+?)\s*$")
_IDENTIFIER: Final = r"[^\W\d]\w*"
_DECLARATION_PATTERN: Final = re.compile(rf"^(?P<name>{_IDENTIFIER})\[(?P<dims>[^\]]*)\]")
_CONNECTION_PATTERN: Final = re.compile(
    rf"^(?P<left>{_IDENTIFIER})\s*(?P<operator>>|-)\s*(?P<right>{_IDENTIFIER})$"
)
_ASSIGNMENT_PATTERN: Final = re.compile(rf"^(?P<name>{_IDENTIFIER})\s*=")

_REQUIRED_SECTIONS: Final[tuple[str, ...]] = (
    "GNNSection",
    "GNNVersionAndFlags",
    "ModelName",
    "StateSpaceBlock",
    "Connections",
    "InitialParameterization",
    "ModelParameters",
)


def _split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for raw_line in text.splitlines():
        match = _SECTION_PATTERN.match(raw_line)
        if match is not None:
            if current is not None:
                sections[current] = "\n".join(lines)
            current = match.group("name")
            lines = []
            continue
        if current is not None:
            lines.append(raw_line)
    if current is not None:
        sections[current] = "\n".join(lines)
    return sections


def _parse_variables(block: str) -> dict[str, tuple[int, ...]]:
    variables: dict[str, tuple[int, ...]] = {}
    for raw_line in block.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = _DECLARATION_PATTERN.match(line)
        if match is None:
            raise GNNSpecError(f"unparsable StateSpaceBlock declaration: {raw_line!r}")
        dimensions: list[int] = []
        for token in match.group("dims").split(","):
            token = token.strip()
            if not token or token.startswith("type="):
                continue
            try:
                dimensions.append(int(token))
            except ValueError as exc:
                raise GNNSpecError(f"non-integer dimension in {raw_line!r}") from exc
        name = match.group("name")
        if name in variables:
            raise GNNSpecError(f"duplicate StateSpaceBlock declaration: {name}")
        variables[name] = tuple(dimensions)
    if not variables:
        raise GNNSpecError("StateSpaceBlock declares no variables")
    return variables


def _parse_connections(block: str) -> tuple[tuple[str, str, str], ...]:
    connections: list[tuple[str, str, str]] = []
    for raw_line in block.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = _CONNECTION_PATTERN.match(line)
        if match is None:
            raise GNNSpecError(f"unparsable Connections entry: {raw_line!r}")
        connections.append((match.group("left"), match.group("operator"), match.group("right")))
    if not connections:
        raise GNNSpecError("Connections declares no edges")
    return tuple(connections)


def _parse_initial_parameterization(block: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    lines = block.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].split("#", 1)[0].strip()
        index += 1
        if not line:
            continue
        match = _ASSIGNMENT_PATTERN.match(line)
        if match is None:
            raise GNNSpecError(f"unparsable InitialParameterization entry: {line!r}")
        name = match.group("name")
        value = line[match.end() :].strip()
        depth = value.count("{") - value.count("}")
        while depth > 0 and index < len(lines):
            continuation = lines[index].split("#", 1)[0].strip()
            index += 1
            value = f"{value} {continuation}"
            depth += continuation.count("{") - continuation.count("}")
        if depth != 0:
            raise GNNSpecError(f"unterminated InitialParameterization value for {name}")
        if name in entries:
            raise GNNSpecError(f"duplicate InitialParameterization entry: {name}")
        entries[name] = value
    if not entries:
        raise GNNSpecError("InitialParameterization declares no matrices")
    return entries


def _parse_model_parameters(block: str) -> dict[str, str]:
    parameters: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise GNNSpecError(f"unparsable ModelParameters entry: {raw_line!r}")
        parameters[key.strip()] = value.strip()
    if not parameters:
        raise GNNSpecError("ModelParameters declares no parameters")
    return parameters


def parse_spec(text: str) -> GNNSpec:
    """Parse GNN specification text into a :class:`GNNSpec`."""

    sections = _split_sections(text)
    missing = [section for section in _REQUIRED_SECTIONS if section not in sections]
    if missing:
        raise GNNSpecError(f"missing required sections: {', '.join(missing)}")
    return GNNSpec(
        section=sections["GNNSection"].strip(),
        version=sections["GNNVersionAndFlags"].strip(),
        model_name=sections["ModelName"].strip(),
        variables=_parse_variables(sections["StateSpaceBlock"]),
        connections=_parse_connections(sections["Connections"]),
        initial_parameterization=_parse_initial_parameterization(
            sections["InitialParameterization"]
        ),
        model_parameters=_parse_model_parameters(sections["ModelParameters"]),
    )


def load_spec(path: Path | None = None) -> GNNSpec:
    """Load and parse the repository GNN specification."""

    spec_path = SPEC_PATH if path is None else path
    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GNNSpecError(f"cannot read GNN specification at {spec_path}") from exc
    return parse_spec(text)


def declared_matrix(spec: GNNSpec, name: str) -> FloatArray:
    """Return an ``InitialParameterization`` entry as a numeric array."""

    raw = spec.initial_parameterization.get(name)
    if raw is None:
        raise GNNSpecError(f"{name} is not declared in InitialParameterization")
    literal = raw.replace("{", "[").replace("}", "]")
    try:
        value = ast.literal_eval(literal)
    except (SyntaxError, ValueError) as exc:
        raise GNNSpecError(f"{name} is not a valid numeric literal: {raw!r}") from exc
    try:
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise GNNSpecError(f"{name} is not numeric: {raw!r}") from exc


def _invariant_issues(matrices: ActiveInferenceMatrices, num_bins: int) -> list[str]:
    issues: list[str] = []
    center = (num_bins - 1) // 2
    if not np.array_equal(matrices.A, np.eye(num_bins)):
        issues.append("A must be the identity likelihood over discretized levels")
    if not np.allclose(matrices.D, np.full(num_bins, 1 / num_bins)):
        issues.append("D must be uniform over discretized levels")
    expected_preferences = np.full(num_bins, -1.0)
    expected_preferences[center] = 2.0
    if not np.allclose(matrices.C, expected_preferences):
        issues.append("C must peak at the target level with -1.0 elsewhere")
    expected_transition = np.zeros((num_bins, num_bins, 3))
    for action in range(3):
        for state in range(num_bins):
            next_state = int(np.clip(state + action - 1, 0, num_bins - 1))
            expected_transition[next_state, state, action] = 1.0
    if not np.array_equal(matrices.B, expected_transition):
        issues.append("B must shift by one bin per control and clip at the bounds")
    return issues


def conformance_issues(spec: GNNSpec, num_bins: int = 3) -> tuple[str, ...]:
    """Compare a parsed specification with the matrices the package builds.

    The structural checks apply to every supported ``num_bins``; the declared
    ``InitialParameterization`` values are compared element-wise when
    ``num_bins`` equals the cardinality declared by the specification.
    """

    if isinstance(num_bins, bool) or not isinstance(num_bins, int) or num_bins < 3:
        raise GNNSpecError("num_bins must be an odd integer >= 3")
    if num_bins % 2 == 0:
        raise GNNSpecError("num_bins must be an odd integer >= 3")

    issues: list[str] = []
    if spec.section != EXPECTED_SECTION:
        issues.append(f"unexpected GNNSection: {spec.section!r}")
    if not spec.version.startswith("GNN v"):
        issues.append(f"unexpected GNN version flag: {spec.version!r}")
    if spec.text_parameter("model_id") != EXPECTED_MODEL_ID:
        issues.append(f"unexpected model_id: {spec.text_parameter('model_id')!r}")

    declared_states = spec.shape("s_bin")[0]
    expected_shapes = {
        "s_bin": (declared_states, 1),
        "o_level": (declared_states, 1),
        "A_level": (declared_states, declared_states),
        "B_bin": (declared_states, declared_states, 3),
        "C_level": (declared_states,),
        "D_bin": (declared_states,),
        "u_control": (3, 1),
        "π_control": (3,),
    }
    for name, expected in expected_shapes.items():
        declared = spec.shape(name)
        if declared != expected:
            issues.append(f"{name} declares shape {declared}, expected {expected}")

    if spec.integer_parameter("num_factors") != 1:
        issues.append("the specification must declare exactly one hidden-state factor")
    if spec.integer_parameter("num_modalities") != 1:
        issues.append("the specification must declare exactly one observation modality")
    if spec.integer_parameter("num_actions") != 3:
        issues.append("the specification must declare the three decrease/hold/increase controls")
    if spec.integer_parameter("num_hidden_states") != declared_states:
        issues.append("num_hidden_states must match the declared factor cardinality")
    if spec.integer_parameter("num_obs") != declared_states:
        issues.append("num_obs must match the declared observation cardinality")
    if spec.text_parameter("conditional_independence") != "true":
        issues.append("the single-factor model must declare conditional_independence: true")
    if spec.text_parameter("transition_axis_order") != "next_state,previous_state,action":
        issues.append("the declared transition axis order must be next_state,previous_state,action")

    declared_edges = spec.edges()
    if declared_edges != EXPECTED_EDGES:
        missing = sorted(EXPECTED_EDGES - declared_edges)
        extra = sorted(declared_edges - EXPECTED_EDGES)
        if missing:
            issues.append(f"missing declared connections: {missing}")
        if extra:
            issues.append(f"undeclared connections: {extra}")

    matrices = build_active_inference_matrices(num_bins)
    issues.extend(_invariant_issues(matrices, num_bins))

    if num_bins == declared_states:
        for name, built in (
            ("A_level", matrices.A),
            ("B_bin", matrices.B),
            ("C_level", matrices.C),
            ("D_bin", matrices.D),
        ):
            declared_values = declared_matrix(spec, name)
            if declared_values.shape != built.shape or not np.allclose(declared_values, built):
                issues.append(f"declared {name} does not match the built matrices")

    return tuple(issues)
