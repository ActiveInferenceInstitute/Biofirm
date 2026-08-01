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
        num_states = self.A.shape[0]
        validate_probability_matrix(self.A, axis=0, name="A")
        validate_probability_matrix(self.B, axis=0, name="B")
        validate_probability_matrix(self.D, axis=0, name="D")
        c = np.asarray(self.C, dtype=float)
        if c.ndim != 1 or not np.all(np.isfinite(c)):
            raise MatrixValidationError("C must be a finite one-dimensional preference vector")
        if c.size != num_states:
            raise MatrixValidationError("C must contain one preference per observation state")
        return self


def build_active_inference_matrices(num_bins: int = 3) -> ActiveInferenceMatrices:
    """Build and validate the bounded decrease/hold/increase model.

    ``num_bins`` is the (odd, >= 3) number of symmetric observation states
    around the target; the action space stays the three-step
    decrease/hold/increase contract that shifts the state by one bin.
    """
    if (
        isinstance(num_bins, bool)
        or not isinstance(num_bins, int)
        or num_bins < 3
        or num_bins % 2 == 0
    ):
        raise MatrixValidationError("num_bins must be an odd integer >= 3")
    center = (num_bins - 1) // 2
    A = np.eye(num_bins, dtype=np.float32)
    B = np.zeros((num_bins, num_bins, 3), dtype=np.float32)
    for action in range(3):
        for state in range(num_bins):
            next_state = int(np.clip(state + action - 1, 0, num_bins - 1))
            B[next_state, state, action] = 1.0
    preferences = np.full(num_bins, -1.0, dtype=np.float32)
    preferences[center] = 2.0
    matrices = ActiveInferenceMatrices(
        A=A,
        B=B,
        C=preferences,
        D=np.full(num_bins, 1 / num_bins, dtype=np.float32),
    )
    return matrices.validate()
