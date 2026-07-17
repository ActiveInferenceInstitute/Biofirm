from __future__ import annotations

import numpy as np
import pytest

from biofirm.pymdp import (
    MatrixValidationError,
    build_active_inference_matrices,
    validate_probability_matrix,
)


def test_active_inference_matrices_are_valid_and_normalized() -> None:
    matrices = build_active_inference_matrices()
    assert np.allclose(matrices.A.sum(axis=0), 1.0)
    assert np.allclose(matrices.B.sum(axis=0), 1.0)
    assert np.allclose(matrices.D.sum(axis=0), 1.0)
    matrices.validate()


def test_invalid_probability_matrix_fails_loudly() -> None:
    with pytest.raises(MatrixValidationError, match="sum to one"):
        validate_probability_matrix(np.array([[0.4, 0.4], [0.4, 0.4]]), axis=0, name="A")
    with pytest.raises(MatrixValidationError, match="negative"):
        validate_probability_matrix(np.array([[1.2], [-0.2]]), axis=0, name="A")


def test_probability_matrices_are_read_only() -> None:
    matrices = build_active_inference_matrices()
    with pytest.raises(ValueError):
        matrices.A[0, 0] = 0.0
