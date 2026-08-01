"""Biofirm's public package API."""

from ._version import __version__
from .config import (
    BiofirmConfig,
    ConfigError,
    ControllerConfig,
    RelationshipConfig,
    VariableConfig,
    canonical_json,
    load_config,
    sha256_json,
)
from .data_validation import DataValidationError, DataValidationReport, validate_repository_data
from .graph import (
    RegionalEdge,
    RegionalGraph,
    RegionalNode,
    acceptance_report,
    descriptive_summary,
    empty_regional_graph,
    nodes_from_json,
    validate_graph,
    with_candidate_edge,
)
from .pymdp import ActiveInferenceMatrices, MatrixValidationError, build_active_inference_matrices
from .simulation import SimulationResult, compare_controllers, run_scenarios, simulate

__all__ = [
    "BiofirmConfig",
    "ActiveInferenceMatrices",
    "ConfigError",
    "ControllerConfig",
    "RelationshipConfig",
    "SimulationResult",
    "MatrixValidationError",
    "VariableConfig",
    "load_config",
    "build_active_inference_matrices",
    "simulate",
    "compare_controllers",
    "run_scenarios",
    "canonical_json",
    "sha256_json",
    "DataValidationError",
    "DataValidationReport",
    "validate_repository_data",
    "RegionalEdge",
    "RegionalGraph",
    "RegionalNode",
    "acceptance_report",
    "descriptive_summary",
    "empty_regional_graph",
    "nodes_from_json",
    "validate_graph",
    "with_candidate_edge",
    "__version__",
]
