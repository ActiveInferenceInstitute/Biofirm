"""
Prompt used:
@Biofirm I am working on a simulation program of POMDP Active Inference agents who work in a firm. 
At each timestep of the simulation, the firm collects data from the environment  related to various metrics for 
taking care of the environment, where the actions of agents attempt to keep the variables in the data within target 
constraints. By keeping variables in their expected target constraint ranges, the agents minimize the 
overall free energy minimization of the firm. My development team wants to include a token generation module 
in the program, where at the end of each timestep, the marginal contribution of each agent to free energy minimization 
is calculated using Shapley values. Tokens are generated based on those Shapley values and distributed to each agent 
based on their respective contribution. Furthermore, the sum total of the token values are stored in a token coop reserve as well. 
Write Python code to create this module and describe how it works step by step.
"""


import numpy as np
from typing import List, Dict

class TokenGenerator:
    def __init__(self):
        self.token_coop_reserve = 0  # Reserve for storing total token values

    def calculate_shapley_values(self, contributions: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate Shapley values for each agent based on their contributions.
        
        :param contributions: A dictionary with agent names as keys and their contributions as values.
        :return: A dictionary with agent names as keys and their Shapley values as values.
        """
        total_contribution = sum(contributions.values())
        shapley_values = {agent: 0 for agent in contributions.keys()}

        # Calculate Shapley values
        for agent in contributions.keys():
            for other_agent in contributions.keys():
                if agent != other_agent:
                    # Calculate marginal contribution
                    marginal_contribution = contributions[agent] / (total_contribution - contributions[other_agent])
                    shapley_values[agent] += marginal_contribution

        # Normalize Shapley values
        total_shapley_value = sum(shapley_values.values())
        for agent in shapley_values.keys():
            shapley_values[agent] = shapley_values[agent] / total_shapley_value if total_shapley_value > 0 else 0

        return shapley_values

    def generate_tokens(self, shapley_values: Dict[str, float], total_tokens: int) -> Dict[str, int]:
        """
        Generate tokens for each agent based on their Shapley values.
        
        :param shapley_values: A dictionary with agent names as keys and their Shapley values as values.
        :param total_tokens: Total number of tokens to distribute.
        :return: A dictionary with agent names as keys and the number of tokens as values.
        """
        tokens_distribution = {agent: int(shapley_value * total_tokens) for agent, shapley_value in shapley_values.items()}
        
        # Adjust for rounding errors
        total_distributed = sum(tokens_distribution.values())
        while total_distributed < total_tokens:
            for agent in tokens_distribution:
                if total_distributed < total_tokens:
                    tokens_distribution[agent] += 1
                    total_distributed += 1
                else:
                    break

        # Update the token coop reserve
        self.token_coop_reserve += total_tokens

        return tokens_distribution

# Example usage
if __name__ == "__main__":
    token_generator = TokenGenerator()
    
    # Example contributions from agents
    contributions = {
        'Agent1': 10.0,
        'Agent2': 20.0,
        'Agent3': 15.0
    }
    
    # Calculate Shapley values
    shapley_values = token_generator.calculate_shapley_values(contributions)
    print("Shapley Values:", shapley_values)
    
    # Generate tokens based on Shapley values
    total_tokens = 100
    tokens = token_generator.generate_tokens(shapley_values, total_tokens)
    print("Tokens Distribution:", tokens)
    print("Token Coop Reserve:", token_generator.token_coop_reserve)