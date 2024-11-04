"""Utilities for handling belief states in active inference"""

import numpy as np
from typing import Dict, Optional, Union, Tuple, List, Any
import logging

def extract_beliefs_from_pymdp(qs: Any, logger: Optional[logging.Logger] = None, expected_size: Optional[int] = None) -> np.ndarray:
    """Extract and validate belief state from PyMDP output format.
    
    Args:
        qs: Belief state from PyMDP agent (various possible formats)
        logger: Optional logger instance.
        expected_size: Expected number of states in the belief array.
        
    Returns:
        Normalized belief probabilities as flat array
    """
    try:
        # Handle direct numpy array case
        if isinstance(qs, np.ndarray):
            if qs.dtype == object:
                # Handle object array - typical PyMDP format
                beliefs = qs[0].astype(np.float64)
            else:
                # Handle regular numpy array
                beliefs = qs.astype(np.float64)

        # Handle list case
        elif isinstance(qs, list):
            beliefs = np.array(qs[0], dtype=np.float64)

        else:
            raise ValueError(f"Unexpected belief state type: {type(qs)}")

        # Ensure we have a flat array
        if beliefs.ndim > 1:
            beliefs = beliefs.flatten()

        # Validate dimension
        if expected_size is not None:
            if len(beliefs) != expected_size:
                raise ValueError(f"Invalid belief state dimension for #{expected_size}: got {len(beliefs)}")
        else:
            # If not provided, infer expected_size from the array
            expected_size = len(beliefs)

        # Ensure normalization
        belief_sum = np.sum(beliefs)
        if not np.isclose(belief_sum, 1.0, rtol=1e-5):
            if logger:
                logger.warning(f"Beliefs not normalized (sum={belief_sum:.3f}). Normalizing now.")
            beliefs = beliefs / belief_sum

        return beliefs

    except Exception as e:
        if logger:
            logger.error(f"Failed to extract beliefs: {str(e)}")
        raise ValueError(f"Failed to extract beliefs: {str(e)}")

def calculate_belief_entropy(beliefs: np.ndarray) -> float:
    """Calculate entropy of belief distribution
    
    Args:
        beliefs: Belief probability distribution
        
    Returns:
        Entropy value in nats
    """
    return -np.sum(beliefs * np.log(beliefs + 1e-10))

def get_most_likely_state(beliefs: np.ndarray) -> int:
    """Get index of most likely state from beliefs
    
    Args:
        beliefs: Belief probability distribution
        
    Returns:
        Index of maximum probability state
    """
    return np.argmax(beliefs)

def belief_distance(beliefs1: np.ndarray, beliefs2: np.ndarray) -> float:
    """Calculate KL divergence between two belief distributions
    
    Args:
        beliefs1: First belief distribution
        beliefs2: Second belief distribution
        
    Returns:
        KL divergence value
    """
    # Add small constant for numerical stability
    eps = 1e-10
    beliefs1 = beliefs1 + eps
    beliefs2 = beliefs2 + eps
    
    # Normalize
    beliefs1 = beliefs1 / beliefs1.sum()
    beliefs2 = beliefs2 / beliefs2.sum()
    
    return np.sum(beliefs1 * np.log(beliefs1 / beliefs2)) 