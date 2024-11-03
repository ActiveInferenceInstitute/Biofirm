"""Active inference agent for ecosystem control using multiple independent POMDPs"""

import numpy as np
from typing import Dict, Optional, Union, Tuple, List, Any
import logging
from pymdp.agent import Agent as PyMDPAgent
from pymdp import utils

from Scripts.POMDP_ABCD import POMDPMatrices
from Scripts.utils.logging_utils import setup_logging
from Scripts.utils.matrix_utils import convert_to_obj_array

class BiofirmAgent:
    """Active inference agent bundle for ecosystem control
    
    Creates N independent POMDP agents (one per controllable ecological modality).
    Each POMDP agent:
    - Input: Discrete observation (0=LOW, 1=HOMEO, 2=HIGH) from ecosystem
    - Internal: 
        - A matrix (3x3) for mapping observations to belief states
        - B matrix (3x3x3) for state transitions under actions
        - C vector (3,) preferring HOMEO state
        - D vector (3,) prior beliefs
    - Process:
        1. Get observation -> Update beliefs using A matrix
        2. Infer policies using B matrix and beliefs
        3. Sample action (0=DEC, 1=MAIN, 2=INC)
    - Output: Control signal (-1, 0, +1) * control_strength
    """
    
    def __init__(self, 
                 config: Dict[str, Any],
                 logger: Optional[logging.Logger] = None) -> None:
        """Initialize N independent POMDP agents"""
        self.logger = logger or setup_logging('biofirm_agent')
        self.config = config
        
        # Store controllable variables for analysis
        self.controllable_vars = list(config['variables'].keys())
        
        # Initialize storage for POMDP agents
        self.agents = {}
        
        self.logger.info("\nInitializing Active Inference Agents:")
        self.logger.info(f"Number of modalities: {len(self.controllable_vars)}")
        
        try:
            # Get shared POMDP matrices (same for all agents)
            matrix_handler = POMDPMatrices({
                'observation_confidence': 0.90,
                'homeostatic_preference': 4.0
            }, self.logger)
            
            matrices = matrix_handler.initialize_all_matrices()
            
            # Verify matrices are numpy arrays with correct shapes
            A = matrices['A']  # (3,3)
            B = matrices['B']  # (3,3,3) 
            C = matrices['C']  # (3,)
            D = matrices['D']  # (3,)
            
            # Log matrix verification
            self.logger.debug(
                f"Verified POMDP matrices:\n"
                f"A: shape={A.shape}, dtype={A.dtype}\n"
                f"B: shape={B.shape}, dtype={B.dtype}\n"
                f"C: shape={C.shape}, dtype={C.dtype}\n"
                f"D: shape={D.shape}, dtype={D.dtype}"
            )
            
            # Create POMDP agents for each controllable variable
            for var_name, var_config in self.config['variables'].items():
                try:
                    # Convert matrices to PyMDP's expected object array format
                    A_obs = convert_to_obj_array(A)
                    B_transitions = convert_to_obj_array(B)
                    C_prefs = convert_to_obj_array(C)
                    D_prior = convert_to_obj_array(D)
                    
                    # Log the converted matrices
                    self.logger.debug(
                        f"Converting matrices for {var_name}:\n"
                        f"A_obs: type={type(A_obs)}, element type={type(A_obs[0])}\n"
                        f"B_transitions: type={type(B_transitions)}, element type={type(B_transitions[0])}\n"
                        f"C_prefs: type={type(C_prefs)}, element type={type(C_prefs[0])}\n"
                        f"D_prior: type={type(D_prior)}, element type={type(D_prior[0])}"
                    )
                    
                    # Create agent with properly formatted matrices
                    agent = PyMDPAgent(
                        A=A_obs,  # Object array containing A matrix
                        B=B_transitions,  # Object array containing B matrix
                        C=C_prefs,  # Object array containing C vector
                        D=D_prior,  # Object array containing D vector
                        control_fac_idx=[0],  # Control the first (only) factor
                        inference_algo='MMP',
                        action_selection='stochastic'
                    )
                    
                    # Store agent with its control strength
                    self.agents[var_name] = {
                        'agent': agent,
                        'control_strength': float(var_config['control_strength'])
                    }
                    
                    self.logger.info(
                        f"  • Created POMDP agent for {var_name}:\n"
                        f"    - Control strength: {var_config['control_strength']:.2f}\n"
                        f"    - Matrix shapes: A{A.shape}, B{B.shape}, C{C.shape}, D{D.shape}"
                    )
                    
                except Exception as e:
                    self.logger.error(
                        f"Error creating POMDP agent for {var_name}:\n"
                        f"  Error: {str(e)}\n"
                        f"  A_obs type: {type(A_obs) if 'A_obs' in locals() else 'not created'}\n"
                        f"  A_obs[0] type: {type(A_obs[0]) if 'A_obs' in locals() else 'not created'}\n"
                        f"  A_obs[0] shape: {A_obs[0].shape if 'A_obs' in locals() else 'not created'}"
                    )
                    raise
                
        except Exception as e:
            self.logger.error(f"Error in BiofirmAgent initialization: {str(e)}")
            raise

    def get_action(self, observations: Dict[str, int]) -> Dict[str, float]:
        """Get control signals from each modality's POMDP agent
        
        Args:
            observations: Dict mapping variable names to discrete states (0,1,2)
        
        Returns:
            Dict mapping variable names to control signals (control_strength * [-1,0,1])
        """
        try:
            controls = {}
            
            # Process each modality's agent
            for var_name, agent_data in self.agents.items():
                try:
                    agent = agent_data['agent']
                    
                    # Convert observation to one-hot array
                    obs_idx = observations[var_name]
                    obs_array = np.zeros((1, 3))  # Shape (1,3) for single observation
                    obs_array[0, obs_idx] = 1.0
                    
                    # Update beliefs and get action
                    agent.infer_states([obs_array])  # List[array] for single modality
                    action = agent.sample_action()
                    
                    # Convert discrete action to control signal
                    control = (action[0] - 1.0)  # Convert 0,1,2 to -1,0,1
                    
                    # Scale by control strength
                    control_strength = agent_data['control_strength']
                    controls[var_name] = control * control_strength
                    
                    self.logger.debug(
                        f"{var_name} decision:\n"
                        f"  Observation: {['LOW', 'HOMEO', 'HIGH'][obs_idx]}\n"
                        f"  Action: {['DEC', 'MAIN', 'INC'][action[0]]}\n"
                        f"  Control: {controls[var_name]:+.2f}"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error processing {var_name}: {str(e)}")
                    controls[var_name] = 0.0  # Safe default
            
            return controls
            
        except Exception as e:
            self.logger.error(f"Error in get_action: {str(e)}")
            return {}

    def get_agent_data(self, var_name: str) -> Dict[str, Any]:
        """Get agent data for analysis
        
        Args:
            var_name: Name of variable/modality
            
        Returns:
            Dictionary containing agent data:
                - state_beliefs: List of belief states over time
                - selected_actions: List of actions taken
                - control_signals: List of control signals sent
                - policy_preferences: List of policy preferences
                - expected_free_energy: List of expected free energies
        """
        try:
            if var_name not in self.agents:
                self.logger.warning(f"No agent data for {var_name}")
                return {}
                
            agent_data = self.agents[var_name]
            agent = agent_data['agent']
            
            return {
                'state_beliefs': [agent.qs[0].copy()],  # Current beliefs
                'selected_actions': [1],  # Default to MAINTAIN
                'control_signals': [0.0],  # Default to no control
                'policy_preferences': [np.array([0.33, 0.34, 0.33])],  # Uniform
                'expected_free_energy': [0.0],  # Default EFE
                'control_strength': agent_data['control_strength']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting agent data for {var_name}: {str(e)}")
            return {}