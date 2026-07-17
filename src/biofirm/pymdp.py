"""Validated generative matrices for the installed PyMDP API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray


class MatrixValidationError(ValueError):
    """Raised when a generative matrix is not a finite probability object."""


FloatArray = NDArray[np.floating[Any]]


def validate_probability_matrix(matrix: Any, *, axis: int, name: str) -> FloatArray:
    """Validate non-negative finite probabilities normalized along ``axis``."""

    if isinstance(axis, bool) or not isinstance(axis, int):
        raise MatrixValidationError(f"{name} axis must be an integer")
    try:
        array = np.asarray(matrix, dtype=float)
    except (TypeError, ValueError) as exc:
        raise MatrixValidationError(f"{name} must be numeric") from exc
    if array.ndim == 0 or not np.all(np.isfinite(array)):
        raise MatrixValidationError(f"{name} must contain finite values")
    if np.any(array < 0):
        raise MatrixValidationError(f"{name} cannot contain negative probabilities")
    if axis < -array.ndim or axis >= array.ndim:
        raise MatrixValidationError(f"{name} axis {axis} is invalid for shape {array.shape}")
    sums = array.sum(axis=axis)
    if not np.allclose(sums, 1.0, atol=1e-6):
        raise MatrixValidationError(f"{name} must sum to one along axis {axis}")
    return array


@dataclass(frozen=True)
class ActiveInferenceMatrices:
    """A valid three-state ecological PyMDP generative model."""

    A: FloatArray
    B: FloatArray
    C: FloatArray
    D: FloatArray

    def __post_init__(self) -> None:
        for field_name in ("A", "B", "C", "D"):
            try:
                array = np.array(getattr(self, field_name), dtype=float, copy=True)
            except (TypeError, ValueError) as exc:
                raise MatrixValidationError(f"{field_name} must be numeric") from exc
            array.setflags(write=False)
            object.__setattr__(self, field_name, array)
        self.validate()

    def validate(self) -> ActiveInferenceMatrices:
        validate_probability_matrix(self.A, axis=0, name="A")
        validate_probability_matrix(self.B, axis=0, name="B")
        validate_probability_matrix(self.D, axis=0, name="D")
        c = np.asarray(self.C, dtype=float)
        if c.ndim != 1 or not np.all(np.isfinite(c)):
            raise MatrixValidationError("C must be a finite one-dimensional preference vector")
        if c.size != 3:
            raise MatrixValidationError("C must contain three preferences")
        return self


def build_active_inference_matrices() -> ActiveInferenceMatrices:
    """Build and validate the bounded decrease/hold/increase model."""

    A = np.eye(3, dtype=np.float32)
    B = np.zeros((3, 3, 3), dtype=np.float32)
    for action in range(3):
        for state in range(3):
            next_state = int(np.clip(state + action - 1, 0, 2))
            B[next_state, state, action] = 1.0
    matrices = ActiveInferenceMatrices(
        A=A,
        B=B,
        C=np.array([-1.0, 2.0, -1.0], dtype=np.float32),
        D=np.full(3, 1 / 3, dtype=np.float32),
    )
    return matrices.validate()
