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
    
    Each ecological modality has:
    - 3 observations (LOW, HOMEO, HIGH)
    - 3 hidden states (LOW, HOMEO, HIGH)
    - 3 control actions (DECREASE, MAINTAIN, INCREASE)
    
    Attributes:
        observation_confidence: Confidence in correct state observations (0-1)
        homeostatic_preference: Strength of preference for homeostatic state
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
    """POMDP matrices for active inference ecosystem control"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """Initialize POMDP matrix handler"""
        self.logger = logger or setup_logging('pomdp')
        
        # Parse and validate config
        self.config = self._validate_config(config)
        self.matrix_config = self._parse_config(config)
        
        self.logger.info(
            f"Initialized POMDP matrices with "
            f"confidence={self.matrix_config.observation_confidence:.2f}, "
            f"preference={self.matrix_config.homeostatic_preference:.1f}"
        )

    def initialize_all_matrices(self) -> Dict[str, np.ndarray]:
        """Initialize all POMDP matrices in PyMDP format
        
        Returns:
            Dictionary containing:
            - A: Observation model [1 x num_obs x num_states]
            - B: Transition model [1 x num_states x num_states x num_actions]
            - C: Preferences [1 x num_obs]
            - D: Prior beliefs [1 x num_states]
        """
        try:
            # Initialize raw matrices
            A = self.initialize_likelihood_matrix()
            B = self.initialize_transition_matrix()
            C = self.initialize_preference_matrix()
            D = self.initialize_prior_beliefs()
            
            # Convert to PyMDP object array format
            A_obj = utils.obj_array(1)
            A_obj[0] = A.copy()
            
            B_obj = utils.obj_array(1)
            B_obj[0] = B.copy()
            
            C_obj = utils.obj_array(1)
            C_obj[0] = C.copy()
            
            D_obj = utils.obj_array(1)
            D_obj[0] = D.copy()
            
            matrices = {
                'A': A_obj,
                'B': B_obj,
                'C': C_obj,
                'D': D_obj
            }
            
            # Validate matrices
            self._validate_matrices(matrices)
            
            self.logger.info(
                f"Initialized POMDP matrices:\n"
                f"  A: P(o|s) with confidence={self.matrix_config.observation_confidence:.2f}\n"
                f"    shape: {A.shape}, sums: {A.sum(axis=0)}\n"
                f"  B: P(s'|s,a) for DEC/MAIN/INC actions\n"
                f"    shape: {B.shape}\n"
                f"  C: Preferences with HOMEO={C[1]:.2f}\n"
                f"    shape: {C.shape}, sum: {C.sum()}\n"
                f"  D: Prior beliefs with HOMEO bias\n"
                f"    shape: {D.shape}, sum: {D.sum()}"
            )
            
            return matrices
            
        except Exception as e:
            self.logger.error(f"Error initializing matrices: {str(e)}")
            raise

    def initialize_likelihood_matrix(self) -> np.ndarray:
        """Initialize observation model P(o|s)
        
        Creates a likelihood mapping from hidden states to observations:
        - Each column represents P(o|s) for a given state
        - High confidence in correct state observation
        - Small probability of observing adjacent states
        
        Returns:
            A[o,s] = P(o|s) with high confidence in correct observations
        """
        conf = self.matrix_config.observation_confidence
        noise = (1.0 - conf)  # Total remaining probability
        
        # For each state, distribute noise to adjacent observations
        A = np.zeros((3, 3), dtype=np.float64)
        
        # LOW state [s=0]
        A[:, 0] = [
            conf,      # P(o=LOW | s=LOW)
            noise,     # P(o=HOMEO | s=LOW)
            0.0        # P(o=HIGH | s=LOW)
        ]
        
        # HOMEO state [s=1]
        A[:, 1] = [
            noise/2,   # P(o=LOW | s=HOMEO)
            conf,      # P(o=HOMEO | s=HOMEO)
            noise/2    # P(o=HIGH | s=HOMEO)
        ]
        
        # HIGH state [s=2]
        A[:, 2] = [
            0.0,       # P(o=LOW | s=HIGH)
            noise,     # P(o=HOMEO | s=HIGH)
            conf       # P(o=HIGH | s=HIGH)
        ]
        
        # Verify column normalization
        if not np.allclose(A.sum(axis=0), 1.0):
            raise ValueError(f"A matrix columns must sum to 1: {A.sum(axis=0)}")
            
        self.logger.debug(
            f"Initialized A matrix with confidence {conf:.2f}:\n{A}\n"
            f"Column sums: {A.sum(axis=0)}"
        )
        
        return A

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
        
        return softmax(log_prefs)

    def initialize_prior_beliefs(self) -> np.ndarray:
        """Initialize prior beliefs over states
        
        Returns:
            D[s] = P(s) with slight HOMEO bias
        """
        return np.array([0.33, 0.34, 0.33], dtype=np.float64)

    def _validate_matrices(self, matrices: Dict[str, np.ndarray]) -> None:
        """Validate POMDP matrices meet PyMDP requirements"""
        try:
            # Validate A matrix columns sum to 1
            A = matrices['A'][0]  # Extract from object array
            if not np.allclose(A.sum(axis=0), 1.0):
                raise ValueError(f"A matrix columns must sum to 1: {A.sum(axis=0)}")
            
            # Validate B matrix for each action
            B = matrices['B'][0]  # Extract from object array
            for a in range(B.shape[2]):
                if not np.allclose(B[:,:,a].sum(axis=0), 1.0):
                    raise ValueError(f"B matrix not normalized for action {a}: {B[:,:,a].sum(axis=0)}")
            
            # Validate C and D are probability distributions
            for name in ['C', 'D']:
                M = matrices[name][0]  # Extract from object array
                if not np.isclose(M.sum(), 1.0):
                    raise ValueError(f"{name} matrix must sum to 1: {M.sum()}")
                if not np.all(M >= 0):
                    raise ValueError(f"{name} matrix contains negative values")
                
            self.logger.debug("All matrices validated successfully")
            
        except Exception as e:
            self.logger.error(f"Matrix validation error: {str(e)}")
            raise

    def _validate_config(self, config: Dict) -> Dict:
        """Validate configuration dictionary"""
        required_keys = ['constraints']
        if not all(k in config for k in required_keys):
            raise ValueError(f"Missing required keys in config: {required_keys}")
        return config

    def _parse_config(self, config: Dict) -> MatrixConfig:
        """Parse configuration into MatrixConfig dataclass"""
        return MatrixConfig(
            observation_confidence=config.get('observation_confidence', 0.90),
            homeostatic_preference=config.get('homeostatic_preference', 4.0)
        )