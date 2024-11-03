"""Utilities for POMDP matrix operations and validation"""

import numpy as np
from typing import Dict, Optional, Union, Tuple, List, Any
import logging

def normalize_matrix(matrix: np.ndarray, axis: int = -1) -> np.ndarray:
    """Normalize matrix along specified axis with numerical stability
    
    Args:
        matrix: Input matrix to normalize
        axis: Axis along which to normalize (-1 for entire array)
        
    Returns:
        Normalized matrix
    """
    # Ensure numerical stability
    matrix = np.clip(matrix, 1e-8, None)
    
    if axis == -1:
        # Normalize entire array
        return matrix / matrix.sum()
    else:
        # Normalize along specified axis
        return matrix / matrix.sum(axis=axis, keepdims=True)

def validate_matrix_shape(matrix: np.ndarray, expected_shape: Tuple[int, ...], 
                         name: str, logger: Optional[logging.Logger] = None) -> bool:
    """Validate matrix dimensions
    
    Args:
        matrix: Matrix to validate
        expected_shape: Expected shape tuple
        name: Matrix name for logging
        logger: Optional logger instance
        
    Returns:
        True if valid, False otherwise
    """
    if matrix.shape != expected_shape:
        if logger:
            logger.error(
                f"{name} matrix: Invalid shape {matrix.shape}, "
                f"expected {expected_shape}"
            )
        return False
    return True

def validate_probability_matrix(matrix: np.ndarray, axis: int = 0,
                              rtol: float = 1e-5) -> bool:
    """Validate probability matrix normalization
    
    Args:
        matrix: Probability matrix to validate
        axis: Axis along which probabilities should sum to 1
        rtol: Relative tolerance for sum comparison
        
    Returns:
        True if valid probability matrix, False otherwise
    """
    # Check for non-negative values
    if not np.all(matrix >= 0):
        return False
        
    # Check normalization
    sums = matrix.sum(axis=axis)
    return np.allclose(sums, 1.0, rtol=rtol)

def convert_to_obj_array(arr: np.ndarray) -> np.ndarray:
    """Convert numpy array to object array format required by PyMDP
    
    Args:
        arr: Input numpy array
        
    Returns:
        Object array containing copy of input array
    """
    obj_arr = np.empty(1, dtype=object)
    obj_arr[0] = arr.copy()
    return obj_arr

def extract_from_obj_array(arr: np.ndarray) -> np.ndarray:
    """Extract array from PyMDP object array format
    
    Args:
        arr: Input object array
        
    Returns:
        Extracted numpy array
    """
    if arr.dtype == object:
        return arr[0]
    return arr

def create_confusion_matrix(confidence: float, num_states: int) -> np.ndarray:
    """Create observation confusion matrix with given confidence
    
    Args:
        confidence: Probability of correct observation (0-1)
        num_states: Number of states/observations
        
    Returns:
        Confusion matrix with shape (num_states, num_states)
    """
    # Validate confidence
    confidence = np.clip(confidence, 0.1, 0.9)
    
    # Calculate off-diagonal probabilities
    noise = (1 - confidence) / (num_states - 1)
    
    # Create matrix
    matrix = np.full((num_states, num_states), noise)
    np.fill_diagonal(matrix, confidence)
    
    return matrix 