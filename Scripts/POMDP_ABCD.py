"""POMDP matrix handler for active inference ecosystem control"""

import numpy as np
from typing import Dict, Optional, Union, Tuple, List, Any
import logging
from dataclasses import dataclass
from pymdp import utils
from pymdp.maths import softmax

from Scripts.utils.logging_utils import setup_logging

@dataclass
class MatrixConfig:
    """Configuration parameters for POMDP matrices
    
    Each modality has:
    - 3 observations (LOW=0, HOMEO=1, HIGH=2)
    - 3 hidden states (LOW=0, HOMEO=1, HIGH=2)
    - 3 control actions (DECREASE=-1, MAINTAIN=0, INCREASE=1)
    """
    observation_confidence: float = 0.90  # High confidence in observations
    homeostatic_preference: float = 4.0   # Strong preference for homeostatic state
    
    def __post_init__(self):
        """Validate configuration parameters"""
        if not 0.5 < self.observation_confidence < 1.0:
            raise ValueError("observation_confidence must be between 0.5 and 1.0")
        if self.homeostatic_preference <= 1.0:
            raise ValueError("homeostatic_preference must be > 1.0")

class POMDPMatrices:
    """POMDP matrices for active inference control"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """Initialize POMDP matrix handler"""
        self.logger = logger or setup_logging('pomdp')
        
        # Parse and validate config
        self.matrix_config = MatrixConfig(
            observation_confidence=config.get('observation_confidence', 0.90),
            homeostatic_preference=config.get('homeostatic_preference', 4.0)
        )
        
        self.logger.info(
            f"Initialized POMDP matrices with "
            f"confidence={self.matrix_config.observation_confidence:.2f}, "
            f"preference={self.matrix_config.homeostatic_preference:.1f}"
        )

    def initialize_all_matrices(self) -> Dict[str, np.ndarray]:
        """Initialize all POMDP matrices in PyMDP format"""
        try:
            # Initialize raw matrices and explicitly convert to float64 numpy arrays
            A = np.array(self.initialize_likelihood_matrix(), dtype=np.float64)
            B = np.array(self.initialize_transition_matrix(), dtype=np.float64)
            C = np.array(self.initialize_preference_matrix(), dtype=np.float64)
            D = np.array(self.initialize_prior_beliefs(), dtype=np.float64)
            
            # Log matrix shapes and sample values for debugging
            self.logger.debug(
                f"Initialized POMDP matrices:\n"
                f"A: shape={A.shape}, dtype={A.dtype}\n{A}\n"
                f"B: shape={B.shape}, dtype={B.dtype}\n"
                f"C: shape={C.shape}, dtype={C.dtype}, values={C}\n"
                f"D: shape={D.shape}, dtype={D.dtype}, values={D}"
            )
            
            matrices = {
                'A': A,
                'B': B, 
                'C': C,
                'D': D
            }
            
            # Validate matrices before returning
            self._validate_matrices(matrices)
            
            return matrices
            
        except Exception as e:
            self.logger.error(f"Error initializing matrices: {str(e)}")
            raise

    def initialize_likelihood_matrix(self) -> np.ndarray:
        """Initialize observation model P(o|s)
        
        Creates a simple 3x3 likelihood matrix mapping observations to states:
        - Each column is P(o|s) for a given state
        - High confidence in correct observations (diagonal)
        - Small probability of adjacent observations
        
        Returns:
            A[o,s] = P(o|s) likelihood matrix
            Shape: (3,3) for LOW/HOMEO/HIGH observations and states
        """
        # Initialize with zeros
        A = np.zeros((3, 3), dtype=np.float64)
        
        # High confidence in correct observations (diagonal)
        conf = self.matrix_config.observation_confidence  # e.g. 0.90
        np.fill_diagonal(A, conf)
        
        # Small probability of adjacent observations
        noise = (1.0 - conf) / 2.0  # Split remaining probability
        
        # Add noise to adjacent states
        A[0, 1] = noise  # P(o=LOW | s=HOMEO)
        A[1, 0] = noise  # P(o=HOMEO | s=LOW)
        A[1, 2] = noise  # P(o=HOMEO | s=HIGH)
        A[2, 1] = noise  # P(o=HIGH | s=HOMEO)
        
        # Add tiny probability to remaining transitions
        A[0, 2] = noise  # P(o=LOW | s=HIGH)
        A[2, 0] = noise  # P(o=HIGH | s=LOW)
        
        # Final matrix should look like:
        # [0.90  0.05  0.05]  # P(o=LOW | s=...)
        # [0.05  0.90  0.05]  # P(o=HOMEO | s=...)
        # [0.05  0.05  0.90]  # P(o=HIGH | s=...)
        
        # Verify columns sum to 1.0
        if not np.allclose(A.sum(axis=0), 1.0):
            self.logger.error(f"A matrix:\n{A}")
            self.logger.error(f"Column sums: {A.sum(axis=0)}")
            raise ValueError(f"A matrix columns must sum to 1: {A.sum(axis=0)}")
        
        return A.astype(np.float64)  # Ensure float64 type

    def initialize_transition_matrix(self) -> np.ndarray:
        """Initialize transition model P(s'|s,a)
        
        Returns:
            B[s',s,a] = P(s'|s,a) encoding action effects
        """
        B = np.zeros((3, 3, 3), dtype=np.float64)
        
        # DECREASE action [a=0]
        B[:,:,0] = np.array([
            [0.90, 0.80, 0.60],  # P(s'=LOW | s, DEC)
            [0.10, 0.15, 0.30],  # P(s'=HOMEO | s, DEC)
            [0.00, 0.05, 0.10]   # P(s'=HIGH | s, DEC)
        ])
        
        # MAINTAIN action [a=1]
        B[:,:,1] = np.array([
            [0.85, 0.10, 0.00],  # P(s'=LOW | s, MAINTAIN)
            [0.10, 0.80, 0.10],  # P(s'=HOMEO | s, MAINTAIN)
            [0.05, 0.10, 0.90]   # P(s'=HIGH | s, MAINTAIN)
        ])
        
        # INCREASE action [a=2]
        B[:,:,2] = np.array([
            [0.10, 0.05, 0.00],  # P(s'=LOW | s, INC)
            [0.30, 0.15, 0.10],  # P(s'=HOMEO | s, INC)
            [0.60, 0.80, 0.90]   # P(s'=HIGH | s, INC)
        ])
        
        return B

    def initialize_preference_matrix(self) -> np.ndarray:
        """Initialize preferences over observations
        
        Returns:
            C[o] = P(o) with strong preference for HOMEO
        """
        log_prefs = np.array([
            0.1,                                # LOW state
            self.matrix_config.homeostatic_preference,  # HOMEO state (preferred)
            0.1                                 # HIGH state
        ], dtype=np.float64)
        
        # Normalize to probabilities
        prefs = softmax(log_prefs)
        return prefs.reshape(-1)  # Ensure 1D array

    def initialize_prior_beliefs(self) -> np.ndarray:
        """Initialize prior beliefs over states
        
        Returns:
            D[s] = P(s) with slight HOMEO bias
        """
        priors = np.array([0.33, 0.34, 0.33], dtype=np.float64)
        return priors.reshape(-1)  # Ensure 1D array

    def _validate_matrices(self, matrices: Dict[str, np.ndarray]) -> None:
        """Validate POMDP matrices meet PyMDP requirements"""
        try:
            # Get arrays directly - they're already numpy arrays, not object arrays
            A = matrices['A']
            B = matrices['B']
            C = matrices['C']
            D = matrices['D']
            
            # Validate A matrix columns sum to 1 with strict tolerance
            if not np.allclose(A.sum(axis=0), 1.0, rtol=1e-10, atol=1e-10):
                raise ValueError(f"A matrix columns must sum to 1: {A.sum(axis=0)}")
            
            # Validate B matrix for each action with strict tolerance
            for a in range(B.shape[2]):
                if not np.allclose(B[:,:,a].sum(axis=0), 1.0, rtol=1e-10, atol=1e-10):
                    raise ValueError(f"B matrix not normalized for action {a}: {B[:,:,a].sum(axis=0)}")
            
            # Validate C and D are probability distributions with strict tolerance
            for name, M in [('C', C), ('D', D)]:
                if not np.allclose(M.sum(), 1.0, rtol=1e-10, atol=1e-10):
                    raise ValueError(f"{name} matrix must sum to 1: {M.sum()}")
                if not np.all(M >= 0):
                    raise ValueError(f"{name} matrix contains negative values")
                if not np.all(np.isfinite(M)):
                    raise ValueError(f"{name} matrix contains non-finite values")
                
            # Validate shapes
            if A.shape != (3, 3):
                raise ValueError(f"A matrix should be (3,3), got {A.shape}")
            if B.shape != (3, 3, 3):
                raise ValueError(f"B matrix should be (3,3,3), got {B.shape}")
            if C.shape != (3,):
                raise ValueError(f"C matrix should be (3,), got {C.shape}")
            if D.shape != (3,):
                raise ValueError(f"D matrix should be (3,), got {D.shape}")
            
        except Exception as e:
            self.logger.error(f"Matrix validation error: {str(e)}")
            raise