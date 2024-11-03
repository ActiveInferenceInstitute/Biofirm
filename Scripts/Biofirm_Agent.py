"""Active inference agent for ecosystem control"""

import numpy as np
from typing import Dict, Optional, Union, Tuple, List, Any
import logging
from pymdp import utils
from pymdp.maths import softmax

from Scripts.POMDP_ABCD import POMDPMatrices
from Scripts.utils.logging_utils import setup_logging

class BiofirmAgent:
    """Active inference agent for ecosystem control"""
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """Initialize BiofirmAgent
        
        Args:
            config: Configuration dictionary containing:
                variables: Dict mapping variable names to their settings
            logger: Optional logger instance
        """
        # Basic setup
        self.logger = logger or setup_logging('biofirm_agent')
        self.config = config
        
        # Initialize storage
        self.agents = {}
        self.agent_history = {}
        
        # Create agents for each variable
        for var_name, var_config in config['variables'].items():
            try:
                if self._create_agent(var_name, var_config):
                    self._initialize_history(var_name)
                    self.logger.info(f"Initialized agent for {var_name}")
                else:
                    raise RuntimeError(f"Failed to create agent for {var_name}")
            except Exception as e:
                self.logger.error(f"Error initializing agent for {var_name}: {str(e)}")
                raise

    def _create_agent(self, var_name: str, var_config: Dict) -> bool:
        """Create PyMDP active inference agent for a variable"""
        try:
            # Get POMDP matrices
            matrix_handler = POMDPMatrices(var_config, self.logger)
            matrices = matrix_handler.initialize_all_matrices()
            
            # Create single-step policies
            policies = np.array([[0], [1], [2]])  # DEC, MAIN, INC
            
            # Create PyMDP agent
            agent = Agent(
                A=matrices['A'],
                B=matrices['B'],
                C=matrices['C'],
                D=matrices['D'],
                num_controls=3,
                policies=policies,
                policy_len=1,
                inference_horizon=1,
                inference_algo='MMP',
                action_selection='stochastic',
                sampling_mode="marginal"
            )
            
            # Store agent data
            self.agents[var_name] = {
                'agent': agent,
                'current_obs': None,
                'current_beliefs': matrices['D'][0].copy(),
                'config': var_config
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating agent for {var_name}: {str(e)}")
            return False

    def infer_states(self, observations: Dict[str, int]) -> Dict[str, np.ndarray]:
        """Infer hidden states from observations"""
        beliefs = {}
        
        for var_name in self.config['variables'].keys():
            try:
                # Get agent
                agent_data = self.agents[var_name]
                agent = agent_data['agent']
                
                # Create one-hot observation
                obs = utils.obj_array(1)
                obs[0] = np.zeros(3)  # 3 possible observations
                obs[0][observations[var_name]] = 1.0
                
                # Store observation
                agent_data['current_obs'] = obs
                
                # Infer states
                qs = agent.infer_states(obs)
                beliefs[var_name] = qs[0][0]  # Get first timestep beliefs
                agent_data['current_beliefs'] = beliefs[var_name]
                
                # Log beliefs
                self.logger.debug(
                    f"{var_name} beliefs: "
                    f"LOW={beliefs[var_name][0]:.2f}, "
                    f"HOMEO={beliefs[var_name][1]:.2f}, "
                    f"HIGH={beliefs[var_name][2]:.2f}"
                )
                
            except Exception as e:
                self.logger.error(f"Error inferring states for {var_name}: {str(e)}")
                beliefs[var_name] = np.ones(3) / 3
                
        return beliefs

    def infer_policies(self) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """Infer policies and their expected free energies
        
        For each policy (action sequence), PyMDP:
        1. Uses B matrix to predict state transitions
        2. Uses A matrix to predict observations
        3. Evaluates expected free energy using C preferences
        4. Returns policy distribution and EFE values
        """
        policies = {}
        free_energies = {}
        
        for var_name in self.config['variables'].keys():
            try:
                agent = self.agents[var_name]['agent']
                
                # Get policy distribution and expected free energies
                q_pi, G = agent.infer_policies()
                
                # Store results
                policies[var_name] = q_pi
                free_energies[var_name] = G
                
                # Log policy evaluation
                self.logger.debug(
                    f"{var_name} policy evaluation:\n"
                    f"  DEC:  prob={q_pi[0]:.2f}, EFE={G[0]:.2f}\n"
                    f"  MAIN: prob={q_pi[1]:.2f}, EFE={G[1]:.2f}\n"
                    f"  INC:  prob={q_pi[2]:.2f}, EFE={G[2]:.2f}"
                )
                
            except Exception as e:
                self.logger.error(f"Error inferring policies for {var_name}: {str(e)}")
                policies[var_name] = np.ones(3) / 3
                free_energies[var_name] = np.zeros(3)
                
        return policies, free_energies

    def sample_action(self) -> Dict[str, int]:
        """Sample actions from policy distributions"""
        actions = {}
        
        for var_name in self.config['variables'].keys():
            try:
                agent = self.agents[var_name]['agent']
                action = agent.sample_action()
                actions[var_name] = int(action[0])
                
                self.logger.debug(
                    f"{var_name} action: "
                    f"{['DEC', 'MAIN', 'INC'][actions[var_name]]}"
                )
                
            except Exception as e:
                self.logger.error(f"Error sampling action for {var_name}: {str(e)}")
                actions[var_name] = 1  # Default to MAINTAIN
                
        return actions

    def action_to_controls(self, actions: Dict[str, int]) -> Dict[str, float]:
        """Convert discrete actions to continuous control signals"""
        controls = {}
        
        for var_name, action_idx in actions.items():
            try:
                # Convert action to control signal
                if action_idx == 0:  # DECREASE
                    control = -1.0
                elif action_idx == 1:  # MAINTAIN
                    control = 0.0
                else:  # INCREASE
                    control = 1.0
                
                # Scale by control strength
                control_strength = self.config['variables'][var_name].get('control_strength', 1.0)
                controls[var_name] = control * control_strength
                
                # Update history
                self.agent_history[var_name]['control_signals'].append(controls[var_name])
                
            except Exception as e:
                self.logger.error(f"Error converting action to control for {var_name}: {str(e)}")
                controls[var_name] = 0.0
                
        return controls

    def _initialize_history(self, var_name: str):
        """Initialize history tracking for an agent"""
        self.agent_history[var_name] = {
            'observations': [],
            'beliefs': [],
            'actions': [],
            'control_signals': [],
            'free_energy': [],
            'policy_preferences': []
        }

    def _update_agent_history(self, var_name: str, observation: int, 
                            beliefs: np.ndarray):
        """Update agent history with new data"""
        history = self.agent_history[var_name]
        history['observations'].append(observation)
        history['beliefs'].append(beliefs.copy())
        
        # Update state value if environment available
        if self.environment:
            try:
                state_value = self.environment.get_variable_value(var_name)
                history['state_values'].append(float(state_value))
            except Exception as e:
                self.logger.error(f"Error getting state value: {str(e)}")
                history['state_values'].append(0.0)

    def get_agent_data(self, var_name: str) -> Dict:
        """Get agent data for analysis"""
        return {
            'history': self.agent_history.get(var_name, {}),
            'matrices': self.agents[var_name]['matrices'] if var_name in self.agents else None,
            'config': self.agents[var_name]['config'] if var_name in self.agents else None
        }

    def _validate_config(self, config: Dict) -> Dict:
        """Validate configuration dictionary"""
        required_keys = ['variables']
        if not all(k in config for k in required_keys):
            raise ValueError(f"Missing required keys in config: {required_keys}")
        return config