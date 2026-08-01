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


def test_probability_validation_rejects_bad_shapes_and_preferences() -> None:
    with pytest.raises(MatrixValidationError, match="axis must"):
        validate_probability_matrix([[1.0]], axis=True, name="A")  # type: ignore[arg-type]
    with pytest.raises(MatrixValidationError, match="numeric"):
        validate_probability_matrix([["bad"]], axis=0, name="A")
    with pytest.raises(MatrixValidationError, match="invalid"):
        validate_probability_matrix([[1.0]], axis=2, name="A")
    with pytest.raises(MatrixValidationError, match="one-dimensional"):
        from biofirm.pymdp import ActiveInferenceMatrices

        ActiveInferenceMatrices(np.eye(3), np.eye(3), np.zeros((3, 1)), np.ones(3) / 3)


def test_generalized_observation_bin_matrices_are_valid() -> None:
    matrices = build_active_inference_matrices(5)
    assert matrices.A.shape == (5, 5)
    assert matrices.B.shape == (5, 5, 3)
    assert matrices.C.size == 5
    assert np.allclose(matrices.B.sum(axis=0), 1.0)
    with pytest.raises(MatrixValidationError, match="odd"):
        build_active_inference_matrices(4)
    with pytest.raises(MatrixValidationError, match="odd"):
        build_active_inference_matrices(1)
