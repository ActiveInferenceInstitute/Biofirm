"""Biofirm's public package API."""

from .config import (
    BiofirmConfig,
    ConfigError,
    ControllerConfig,
    RelationshipConfig,
    VariableConfig,
    load_config,
)
from .pymdp import ActiveInferenceMatrices, MatrixValidationError, build_active_inference_matrices
from .simulation import SimulationResult, simulate

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
]

__version__ = "0.1.0"
