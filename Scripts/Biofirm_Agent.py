"""Active inference agent for ecosystem control using PyMDP"""

import numpy as np
from typing import Dict, Optional, Union, Tuple, List, Any
import logging
from pymdp.agent import Agent as PyMDPAgent
from pymdp import utils
from pymdp.maths import softmax

from Scripts.POMDP_ABCD import POMDPMatrices
from Scripts.utils.logging_utils import setup_logging

class BiofirmAgent:
    """Active inference agent for ecosystem control using multiple independent POMDPs"""
    
    def __init__(self, 
                 config: Dict[str, Any],
                 logger: Optional[logging.Logger] = None) -> None:
        """Initialize BiofirmAgent with independent POMDP for each controllable variable
        
        Args:
            config: Configuration dictionary containing:
                variables: Dict mapping variable names to their settings
                constraints: Dict of variable constraints
            logger: Optional logger instance
        """
        # Basic setup
        self.logger = logger or setup_logging('biofirm_agent')
        self.config = self._validate_config(config)
        
        # Initialize storage for PyMDP agents
        self.agents = {}
        self.agent_history = {}
        
        # Create POMDP agents for each controllable variable
        for var_name, var_config in self.config['variables'].items():
            if var_config.get('controllable', False):
                try:
                    self._create_pomdp_agent(var_name, var_config)
                    self._initialize_history(var_name)
                    self.logger.info(f"Initialized POMDP agent for {var_name}")
                except Exception as e:
                    self.logger.error(f"Error initializing POMDP agent for {var_name}: {str(e)}")
                    raise

    def _create_pomdp_agent(self, var_name: str, var_config: Dict) -> None:
        """Create PyMDP active inference agent for a variable"""
        try:
            # Create simple POMDP config
            matrix_config = {
                'observation_confidence': 0.90,
                'homeostatic_preference': 4.0
            }
            
            # Get POMDP matrices
            matrix_handler = POMDPMatrices(matrix_config, self.logger)
            matrices = matrix_handler.initialize_all_matrices()
            
            # Create PyMDP agent
            agent = PyMDPAgent(
                A=matrices['A'][0].astype(np.float64),
                B=matrices['B'][0].astype(np.float64),
                C=matrices['C'][0].astype(np.float64),
                D=matrices['D'][0].astype(np.float64),
                num_controls=3,
                control_fac_idx=[0],
                inference_algo='MMP',
                action_selection='stochastic',
                sampling_mode="marginal"
            )
            
            # Store agent and its configuration
            self.agents[var_name] = {
                'agent': agent,
                'current_obs': None,
                'current_beliefs': matrices['D'][0].copy(),
                'config': var_config,
                'matrices': matrices
            }
            
            self.logger.info(f"Created POMDP agent for {var_name}")
            
        except Exception as e:
            self.logger.error(f"Error creating POMDP agent for {var_name}: {str(e)}")
            raise

    def infer_states(self, observations: Dict[str, int]) -> Dict[str, np.ndarray]:
        """Infer hidden states for each POMDP from observations
        
        Args:
            observations: Dictionary mapping variable names to discrete observations (0=LOW, 1=HOMEO, 2=HIGH)
            
        Returns:
            Dictionary mapping variable names to posterior beliefs over states
        """
        beliefs = {}
        
        for var_name, agent_data in self.agents.items():
            try:
                agent = agent_data['agent']
                
                # Create observation array for PyMDP agent
                obs = [observations[var_name]]  # Single modality observation
                
                # Store observation
                agent_data['current_obs'] = obs
                
                # Infer states using PyMDP agent
                qs = agent.infer_states(obs)
                beliefs[var_name] = qs[0]  # Get first factor beliefs
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
                beliefs[var_name] = np.ones(3) / 3  # Uniform beliefs on error
                
        return beliefs

    def infer_policies(self) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """Infer policies for each POMDP
        
        Returns:
            Tuple containing:
            - Dictionary mapping variable names to policy distributions
            - Dictionary mapping variable names to expected free energies
        """
        policies = {}
        free_energies = {}
        
        for var_name, agent_data in self.agents.items():
            try:
                agent = agent_data['agent']
                
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
        """Sample actions from policy distributions for each POMDP
        
        Returns:
            Dictionary mapping variable names to discrete actions (0=DEC, 1=MAIN, 2=INC)
        """
        actions = {}
        
        for var_name, agent_data in self.agents.items():
            try:
                agent = agent_data['agent']
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
        """Convert discrete POMDP actions to continuous control signals
        
        Args:
            actions: Dictionary mapping variable names to discrete actions
            
        Returns:
            Dictionary mapping variable names to continuous control signals
        """
        controls = {}
        
        for var_name, action_idx in actions.items():
            try:
                # Convert action to control signal
                if action_idx == 0:    # DECREASE
                    control = -1.0
                elif action_idx == 1:  # MAINTAIN
                    control = 0.0
                else:                  # INCREASE
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

    def _initialize_history(self, var_name: str) -> None:
        """Initialize history tracking for an agent"""
        self.agent_history[var_name] = {
            'observations': [],
            'beliefs': [],
            'actions': [],
            'control_signals': [],
            'free_energy': [],
            'policy_preferences': []
        }

    def get_agent_data(self, var_name: str) -> Dict:
        """Get agent data for analysis"""
        return {
            'history': self.agent_history.get(var_name, {}),
            'matrices': self.agents[var_name]['matrices'] if var_name in self.agents else None,
            'config': self.agents[var_name]['config'] if var_name in self.agents else None
        }

    def _validate_config(self, config: Dict) -> Dict:
        """Validate configuration dictionary"""
        if 'variables' not in config:
            raise ValueError("Missing 'variables' in config")
            
        # Ensure variables have required fields
        for var_name, var_config in config['variables'].items():
            required_fields = ['controllable', 'control_strength']
            missing = [f for f in required_fields if f not in var_config]
            if missing:
                raise ValueError(f"Variable {var_name} missing required fields: {missing}")
        
        return config

    def get_action(self, observations: Dict[str, int]) -> Dict[str, float]:
        """Get control signals for each variable based on observations
        
        Args:
            observations: Dictionary mapping variable names to discrete observations
                         (0=LOW, 1=HOMEO, 2=HIGH)
        
        Returns:
            Dictionary mapping variable names to control signals (-1.0 to 1.0)
        """
        try:
            controls = {}
            
            # Process each modality
            for var_name, agent_data in self.agents.items():
                try:
                    agent = agent_data['agent']
                    obs = [observations[var_name]]  # Single modality observation
                    
                    # 1. Update beliefs about hidden states
                    qs = agent.infer_states(obs)
                    agent_data['current_beliefs'] = qs[0]
                    
                    # 2. Infer policies using Expected Free Energy
                    q_pi, G = agent.infer_policies()
                    
                    # 3. Sample action from policy posterior
                    action = agent.sample_action()
                    
                    # 4. Convert discrete action to control signal
                    if action[0] == 0:    # DECREASE
                        control = -1.0
                    elif action[0] == 1:  # MAINTAIN
                        control = 0.0
                    else:                 # INCREASE
                        control = 1.0
                    
                    # Scale by control strength
                    control_strength = agent_data['config'].get('control_strength', 1.0)
                    controls[var_name] = control * control_strength
                    
                    # Log decision process
                    self.logger.debug(
                        f"{var_name} decision:\n"
                        f"  Observation: {['LOW', 'HOMEO', 'HIGH'][obs[0]]}\n"
                        f"  Beliefs: LOW={qs[0][0]:.2f}, HOMEO={qs[0][1]:.2f}, HIGH={qs[0][2]:.2f}\n"
                        f"  Policy probs: DEC={q_pi[0]:.2f}, MAIN={q_pi[1]:.2f}, INC={q_pi[2]:.2f}\n"
                        f"  Selected action: {['DEC', 'MAIN', 'INC'][action[0]]}\n"
                        f"  Control signal: {controls[var_name]:+.2f}"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error processing {var_name}: {str(e)}")
                    controls[var_name] = 0.0  # Safe default
            
            return controls
            
        except Exception as e:
            self.logger.error(f"Error in get_action: {str(e)}")
            return {}