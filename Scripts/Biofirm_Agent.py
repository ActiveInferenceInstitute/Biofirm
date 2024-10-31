import sys
from pathlib import Path
import numpy as np
from typing import List, Dict
from pymdp.agent import Agent
from pymdp.utils import obj_array
import matplotlib.pyplot as plt

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class BiofirmAgent:
    """Wrapper class for PyMDP active inference agent with 3-state system"""
    
    def __init__(self, num_variables: int):
        """Initialize BiofirmAgent with environment dimensions"""
        self.num_variables = num_variables
        
        # Create separate agents for each controllable variable
        self.agents = []
        for i in range(3):  # 3 controllable variables
            A = self._initialize_likelihood_matrix(i)
            B = self._initialize_transition_matrix(i)
            C = self._initialize_preference_matrix(i)
            D = self._initialize_prior_beliefs(i)
            
            agent = Agent(A=A, B=B, C=C, D=D, 
                         inference_algo='MMP',
                         policy_len=1,
                         inference_horizon=2,
                         action_selection='stochastic')
            self.agents.append(agent)

    def _initialize_likelihood_matrix(self, control_idx: int):
        """Initialize A matrix mapping hidden states to observations
        
        The A matrix encodes P(o|s) - probability of observation given hidden state:
        - States (s): LOW(0), HOMEOSTATIC(1), HIGH(2)  
        - Observations (o): LOW(0), HOMEOSTATIC(1), HIGH(2)
        
        Returns:
            3x3 matrix where A[o,s] = P(observation o | state s)
        """
        A = np.zeros((3, 3))
        
        # High confidence (0.9) in correct observations
        # Small chance (0.05) of observing adjacent states
        A[0,0] = 0.9  # P(observe LOW | state LOW) 
        A[1,1] = 0.9  # P(observe HOME | state HOME)
        A[2,2] = 0.9  # P(observe HIGH | state HIGH)
        
        # Add observation uncertainty
        A[0,1] = A[1,0] = 0.05  # LOW-HOME confusion
        A[1,2] = A[2,1] = 0.05  # HOME-HIGH confusion
        A[0,2] = A[2,0] = 0.05  # LOW-HIGH confusion (rare)
        
        return A
    
    def _initialize_transition_matrix(self, control_idx: int):
        """Initialize B matrix encoding state transitions under different actions
        
        The B matrix encodes P(s'|s,a) - probability of next state given current state and action:
        - Current states (s): LOW(0), HOMEOSTATIC(1), HIGH(2)
        - Next states (s'): LOW(0), HOMEOSTATIC(1), HIGH(2)
        - Actions (a): DECREASE(0), MAINTAIN(1), INCREASE(2)
        
        Returns:
            3x3x3 tensor where B[s',s,a] = P(next state s' | current state s, action a)
        """
        # Single B matrix for this control variable
        B = np.zeros((3, 3, 3))  # 3 states, 3 next states, 3 actions
        
        # Action effects for each current state
        for s in range(3):  # Current state (LOW, HOME, HIGH)
            for a in range(3):  # Action (decrease, no change, increase)
                if a == 0:  # Decrease action
                    if s == 0:  # From LOW state
                        B[:,s,a] = [0.9, 0.1, 0.0]  # Likely stay LOW
                    elif s == 1:  # From HOME state
                        B[:,s,a] = [0.7, 0.3, 0.0]  # Likely go LOW
                    else:  # From HIGH state
                        B[:,s,a] = [0.1, 0.8, 0.1]  # Likely go HOME
                        
                elif a == 1:  # No change action
                    if s == 0:  # From LOW state
                        B[:,s,a] = [0.8, 0.2, 0.0]  # Mostly stay LOW
                    elif s == 1:  # From HOME state
                        B[:,s,a] = [0.1, 0.8, 0.1]  # Mostly stay HOME
                    else:  # From HIGH state
                        B[:,s,a] = [0.0, 0.2, 0.8]  # Mostly stay HIGH
                        
                else:  # Increase action
                    if s == 0:  # From LOW state
                        B[:,s,a] = [0.1, 0.8, 0.1]  # Likely go HOME
                    elif s == 1:  # From HOME state
                        B[:,s,a] = [0.0, 0.3, 0.7]  # Likely go HIGH
                    else:  # From HIGH state
                        B[:,s,a] = [0.0, 0.1, 0.9]  # Likely stay HIGH
                
                # Normalize along first axis (next states)
                B[:,s,a] = B[:,s,a] / np.sum(B[:,s,a])
                
                # Verify normalization
                assert np.isclose(np.sum(B[:,s,a]), 1.0), (
                    f"B matrix not normalized for state {s}, action {a}"
                )
        
        return B
    
    def _initialize_preference_matrix(self, control_idx: int):
        """Initialize C matrix (preference/goal encoding) for 3 states"""
        # Strongly prefer HOMEOSTATIC state (state 1)
        return np.array([0.1, 1.0, 0.1])
    
    def _initialize_prior_beliefs(self, control_idx: int):
        """Initialize D matrix (prior beliefs) for 3 states"""
        # Equal prior probability for each state
        return np.array([0.33, 0.34, 0.33])

    def get_action(self, observations: List[int]) -> Dict[str, float]:
        """Get next action based on active inference for each controllable variable
        
        Args:
            observations: List of state indicators where:
                0 = LOW (below target range)
                1 = HOMEOSTATIC (within target range) 
                2 = HIGH (above target range)
        """
        controls = []
        
        # Get action for each controllable variable using its dedicated agent
        for i, agent in enumerate(self.agents):
            # Get observation for this control variable
            obs = observations[i]  # Already encoded as 0,1,2 from Environment._verify_constraints()
            
            # Active Inference steps:
            # 1. State inference using A matrix (observation model)
            qs = agent.infer_states([obs])  # Posterior over hidden states
            
            # 2. Policy inference using B matrix (transition model) and C matrix (preferences)
            q_pi, G = agent.infer_policies()  # Returns policy distribution and expected free energy
            
            # 3. Action selection via free energy minimization
            action = agent.sample_action()  # Samples from policy distribution
            
            # Convert to control signal (-1=decrease, 0=maintain, 1=increase)
            control = (action % 3) - 1
            controls.append(control)
        
        # Scale and return control signals
        return {
            'health': controls[0] * 1.0,
            'carbon': controls[1] * 1.0,
            'buffer': controls[2] * 1.0
        }

    def update_beliefs(self, observations: List[int]):
        """Update agent's beliefs based on observations"""
        # Update beliefs for each agent with its corresponding observation
        for i, agent in enumerate(self.agents):
            obs = observations[i]
            agent.infer_states([obs])

    def visualize_policy_selection(self, obs: int, agent_idx: int):
        """Visualize policy selection process for debugging
        
        Args:
            obs: Current observation (0=LOW, 1=HOME, 2=HIGH)
            agent_idx: Index of agent (0=health, 1=carbon, 2=buffer)
        """
        agent = self.agents[agent_idx]
        
        # Get posterior beliefs and policy distribution
        qs = agent.infer_states([obs])
        q_pi, G = agent.infer_policies()
        
        # Plot state beliefs and expected free energy
        plt.figure(figsize=(10,5))
        
        plt.subplot(121)
        plt.bar(['LOW', 'HOME', 'HIGH'], qs[0])
        plt.title('State Beliefs')
        
        plt.subplot(122)
        plt.bar(['DECREASE', 'MAINTAIN', 'INCREASE'], -G)
        plt.title('Policy Preferences\n(negative free energy)')
        
        plt.tight_layout()
        return plt.gcf()

if __name__ == "__main__":
    # Test the agent
    try:
        # Initialize and test agent
        agent = BiofirmAgent(num_variables=10)
        print("BiofirmAgent initialized successfully")
        
        # Test with sample observations
        observations = [0] * 10  # All variables outside constraints
        action = agent.get_action(observations)
        print(f"\nTest with all variables outside constraints:")
        print(f"Observations: {observations}")
        print(f"Action: {action}")
        
        observations = [1] * 10  # All variables within constraints
        action = agent.get_action(observations)
        print(f"\nTest with all variables within constraints:")
        print(f"Observations: {observations}")
        print(f"Action: {action}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)