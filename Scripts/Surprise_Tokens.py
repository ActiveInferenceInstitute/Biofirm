"""
This script retrieves the most recent environmental history data from CSV files in 
the "Outputs" directory and reads ecosystem configuration from a JSON file. 
It computes surprise values for specified variables based on their constraints and 
stores these values in a new DataFrame. The script then visualizes the surprise values 
and saves the plots as PNG files. Finally, it calculates token accumulation based 
on changes in surprise and generates additional plots for the token history, 
which are also saved as PNG files in the provided output directory.
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

print(f"Computing surprise for {len(config_dict['variables'])} variables over {len(env_history)} timesteps...")

try:
    # Iterate through each variable in config_dict to compute surprise
    for variable, constraints in config_dict['variables'].items():
        lower_bound = constraints['constraints']['lower']
        upper_bound = constraints['constraints']['upper']
        
        # Calculate the median of the constraint range
        median_value = (lower_bound + upper_bound) / 2
        
        # List to store surprise values for the current variable
        surprise_values = []
        
        # Iterate over each timestep to compute surprise for the variable
        for timestep in range(len(env_history)):
            current_value = env_history.iloc[timestep][variable]
            
            # Compute surprise based on the distance from the median
            surprise = np.abs(current_value - median_value)  # Absolute difference from the median
            
            # Optionally, you can apply a log transformation if needed
            # surprise = -np.log(surprise + epsilon)  # Uncomment if you want to use log scale
            
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
    axes[i].set_title(f'Surprise for {variable}')
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




