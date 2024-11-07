"""
This script processes environmental data from CSV files and ecosystem configurations 
from a JSON file to compute Bayesian surprise and token accumulation. 

The ActiveInferenceSurpriseTracker class calculates surprise using a truncated 
Gaussian distribution and a Kalman update, measuring the difference between 
prior and posterior distributions via Kullback-Leibler (KL) divergence. 
A preference violation term penalizes observations outside defined bounds. 

For token accumulation, the script tracks changes in surprise, adding tokens 
only when surprise decreases. The change in surprise is calculated as the 
difference between current and previous values, allowing the script to 
visualize both surprise and token accumulation through generated plots, 
revealing the dynamics of environmental variables over time.

Plots for Bayesian surprise and token accumulation are stored in output_dir/visualizations.
"""

# Pull latest environmental history from Outputs directory
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Find all CSV files matching the pattern in the Outputs directory
output_dir = "Outputs"
csv_files = [f for f in os.listdir(output_dir) if f.startswith('data_active_inference_') and f.endswith('.csv')]

# Initialize env_history as None in case no matching files are found
if not csv_files:
    env_history = None
else:
    # Get files with their creation times using full path
    csv_files_with_time = [(f, os.path.getctime(os.path.join(output_dir, f))) for f in csv_files]
    
    # Sort by creation time (most recent first)
    csv_files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # Get the most recent file name
    most_recent_file = csv_files_with_time[0][0]
    
    # Read the CSV using full path into env_history
    env_history = pd.read_csv(os.path.join(output_dir, most_recent_file))

# Pull ecosystem config from JSON file
import json

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

# Read ecosystem config from JSON file
config_dict = read_json_file('utils/ecosystem_config.json')

# Define a small epsilon value to avoid log(0)
epsilon = 1e-10

# Create a new dataframe for surprise history
surprise_history = pd.DataFrame(index=env_history.index)

import numpy as np
import pandas as pd
from scipy import stats

class ActiveInferenceSurpriseTracker:
    def __init__(self, initial_mean, initial_variance, lower_bound, upper_bound, preference_strength=1.0):
        self.prior_mean = initial_mean
        self.prior_variance = initial_variance
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.preference_strength = preference_strength
        
    def preference_distribution(self, x):
        # Create a preference distribution that favors values within bounds
        # Using a truncated Gaussian as the preference distribution
        return stats.truncnorm.pdf(
            x, 
            (self.lower_bound - self.prior_mean) / np.sqrt(self.prior_variance),
            (self.upper_bound - self.prior_mean) / np.sqrt(self.prior_variance),
            loc=self.prior_mean,
            scale=np.sqrt(self.prior_variance)
        )
    
    def update(self, observation, observation_variance):
        # Standard Kalman update for the empirical distribution
        posterior_variance = 1 / (1/self.prior_variance + 1/observation_variance)
        posterior_mean = posterior_variance * (
            self.prior_mean/self.prior_variance + 
            observation/observation_variance
        )
        
        # Combine empirical posterior with preferences
        # The preference_strength parameter controls how strongly we weight preferences
        combined_posterior_mean = (posterior_mean + 
            self.preference_strength * np.clip(posterior_mean, self.lower_bound, self.upper_bound)
        ) / (1 + self.preference_strength)
        
        # Compute surprise as KL divergence between prior and posterior
        # Include both empirical surprise and preference violation
        empirical_surprise = self._kl_divergence_gaussian(
            self.prior_mean, self.prior_variance,
            posterior_mean, posterior_variance
        )
        
        # Additional surprise term for preference violation
        preference_violation = 0.0
        if observation < self.lower_bound:
            preference_violation = self.preference_strength * (self.lower_bound - observation)**2
        elif observation > self.upper_bound:
            preference_violation = self.preference_strength * (observation - self.upper_bound)**2
            
        total_surprise = empirical_surprise + preference_violation
        
        # Update prior for next timestep
        self.prior_mean = combined_posterior_mean
        self.prior_variance = posterior_variance
        
        return total_surprise
    
    def _kl_divergence_gaussian(self, p_mean, p_var, q_mean, q_var):
        return 0.5 * (
            np.log(q_var/p_var) + 
            (p_var + (p_mean - q_mean)**2)/q_var - 1
        )

# Create a new dataframe for surprise history
surprise_history = pd.DataFrame(index=env_history.index)

print(f"Computing surprise for {len(config_dict['variables'])} variables over {len(env_history)} timesteps...")

try:
    # Iterate through each variable in config_dict to compute surprise
    for variable, constraints in config_dict['variables'].items():
        lower_bound = constraints['constraints']['lower']
        upper_bound = constraints['constraints']['upper']
        
        # Initialize the tracker with prior based on constraints
        initial_mean = (lower_bound + upper_bound) / 2
        initial_variance = ((upper_bound - lower_bound) / 4) ** 2  # Using range/4 as 2-sigma
        
        # Create tracker for this variable with preferences
        tracker = ActiveInferenceSurpriseTracker(
            initial_mean, 
            initial_variance,
            lower_bound,
            upper_bound,
            preference_strength=1.0  # Adjust this to control preference strength
        )
        
        # List to store surprise values for the current variable
        surprise_values = []
        
        # Iterate over each timestep to compute surprise for the variable
        for timestep in range(len(env_history)):
            current_value = env_history.iloc[timestep][variable]
            
            # Assume observation variance is proportional to the range
            observation_variance = ((upper_bound - lower_bound) / 6) ** 2
            
            # Compute surprise with preferences and update beliefs
            surprise = tracker.update(current_value, observation_variance)
            surprise_values.append(surprise)

        # Add the surprise values to the surprise_history dataframe
        surprise_history[variable] = surprise_values

except Exception as e:
    print(f"Error computing surprise for {variable}: {str(e)}")


# Plot the surprise values for all variables in subplots using line plots
num_variables = len(surprise_history.columns)
num_rows = (num_variables + 1) // 2  # Calculate number of rows needed for 2 columns

fig, axes = plt.subplots(num_rows, 2, figsize=(12, 5 * num_rows))
axes = axes.flatten()  # Flatten the axes array for easy indexing

for i, variable in enumerate(surprise_history.columns):
    axes[i].plot(surprise_history.index, surprise_history[variable], label=variable, alpha=0.6)  # Changed to line plot
    axes[i].set_title(f'Bayesian surprise for {variable}')
    axes[i].set_xlabel('Timestep')
    axes[i].set_ylabel('Surprise')
    axes[i].grid()
    axes[i].legend()

# Hide any unused subplots
for j in range(i + 1, len(axes)):
    axes[j].axis('off')

plt.tight_layout()
try:    
    plt.savefig(f"{output_dir}/visualizations/surprise_history.png")
    print(f"Surprise history plot saved successfully to {output_dir}/visualizations/surprise_history.png")
except Exception as e:
    print(f"Error saving surprise history plot: {str(e)}")
#plt.show()

# Create a new dataframe for token history
token_history = pd.DataFrame(index=surprise_history.index)

print(f"Computing token accumulation for {len(config_dict['variables'])} variables over {len(env_history)} timesteps...")
try:
    # Initialize the first timestep for token history
    for variable in surprise_history.columns:
        token_history[variable] = 0.0  # Start with zero accumulation

    # Compute the change in surprise and accumulate tokens, where tokens are accumulated only if the surprise decreases
    for timestep in range(1, len(surprise_history)):
        for variable in surprise_history.columns:
            # Calculate the change in surprise
            surprise_change = surprise_history.iloc[timestep][variable] - surprise_history.iloc[timestep - 1][variable]
            
            # Only add to the token history if the surprise decreased
            if surprise_change < 0:
                token_history.loc[timestep, variable] = token_history.loc[timestep - 1, variable] + abs(surprise_change)
            else:
                token_history.loc[timestep, variable] = token_history.loc[timestep - 1, variable]
except Exception as e:
    print(f"Error computing token accumulation for {variable}: {str(e)}")

# Plot the token history values for all variables in subplots using scatter plots
num_variables = len(token_history.columns)
num_rows = (num_variables + 1) // 2  # Calculate number of rows needed for 2 columns

fig, axes = plt.subplots(num_rows, 2, figsize=(12, 5 * num_rows))
axes = axes.flatten()  # Flatten the axes array for easy indexing

for i, variable in enumerate(token_history.columns):
    axes[i].scatter(token_history.index, token_history[variable], label=variable, alpha=0.6, s=5)
    axes[i].set_title(f'Token History for {variable}')
    axes[i].set_xlabel('Timestep')
    axes[i].set_ylabel('Cumulative Change in Surprise')
    axes[i].grid()
    axes[i].legend()

# Hide any unused subplots
for j in range(i + 1, len(axes)):
    axes[j].axis('off')

plt.tight_layout()
try:
    plt.savefig(f"{output_dir}/visualizations/token_history.png")
    print(f"Token history plot saved successfully to {output_dir}/visualizations/token_history.png")
except Exception as e:
    print(f"Error saving token history plot: {str(e)}")
#plt.show()





