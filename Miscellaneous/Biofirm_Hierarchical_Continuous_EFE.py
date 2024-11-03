"""
Perplexity prompt-response trace:
https://www.perplexity.ai/search/in-python-i-have-a-dataframe-o-T4eofs5hTJmvaVyfm7O3Xg

"""


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Create example DataFrame with 10 time-series variables
np.random.seed(0)
date_range = pd.date_range(start='2024-01-01', periods=10, freq='D')
variables = pd.DataFrame(np.random.randn(10, 10), 
                        index=date_range, 
                        columns=[f'var{i}' for i in range(10)])

# Define expected ranges for each variable
expected_ranges = {f'var{i}': (np.random.uniform(-2, 0), 
                              np.random.uniform(0, 2)) 
                  for i in range(10)}

class Observation:
    def __init__(self, time, values, constraint_verification):
        self.time = time
        self.values = values
        self.free_energy = compute_free_energy(values)
        self.constraint_verification = constraint_verification

def compute_free_energy(new_observation):
    free_energy = 0
    for i in range(10):
        lower_bound, upper_bound = expected_ranges[f'var{i}']
        if new_observation[i] < lower_bound:
            free_energy += (lower_bound - new_observation[i])**2
        elif new_observation[i] > upper_bound:
            free_energy += (new_observation[i] - upper_bound)**2
    return free_energy

def check_constraints(new_observation):
    constraint_verification = []
    for i in range(10):
        lower_bound, upper_bound = expected_ranges[f'var{i}']
        if lower_bound <= new_observation[i] <= upper_bound:
            constraint_verification.append(1)
        else:
            constraint_verification.append(0)
    return constraint_verification

def process_observations(variables):
    observations = []
    free_energy_data = []
    constraint_verification_list = []
    
    for i in range(len(variables)):
        new_observation = variables.iloc[i].values
        constraint_verification = check_constraints(new_observation)
        observation = Observation(variables.index[i], new_observation, constraint_verification)
        observations.append(observation)
        free_energy_data.append(observation.free_energy)
        constraint_verification_list.append(constraint_verification)
    
    return observations, free_energy_data, constraint_verification_list

def plot_time_series_and_metrics(variables, expected_ranges, free_energy_data, constraint_verification_list):
    fig, axes = plt.subplots(len(variables.columns) + 2, 1, figsize=(12, 20))
    date_range = variables.index

    # Plot individual variable time series
    for i, col in enumerate(variables.columns):
        axes[i].plot(date_range, variables[col], marker='o', label=col)
        lower_bound, upper_bound = expected_ranges[col]
        axes[i].axhline(y=lower_bound, color='r', linestyle='--')
        axes[i].axhline(y=upper_bound, color='g', linestyle='--')
        axes[i].fill_between(date_range, lower_bound, upper_bound, 
                           color='lightgrey', alpha=0.5)
        axes[i].set_title(f'{col} Time Series')
        axes[i].set_xlabel('Date')
        axes[i].set_ylabel('Value')
        axes[i].legend()

    # Plot free energy
    axes[-2].plot(date_range, free_energy_data, color='b', marker='o')
    axes[-2].set_title('Free Energy Over Time')
    axes[-2].set_xlabel('Date')
    axes[-2].set_ylabel('Free Energy')

    # Plot constraint verification
    constraint_verification_array = np.array(constraint_verification_list)
    for var_idx in range(10):
        for t in range(len(date_range)):
            color = 'blue' if constraint_verification_array[t, var_idx] == 1 else 'red'
            axes[-1].scatter(date_range[t], f'var{var_idx}', c=color)
    
    axes[-1].set_title('Constraint Verification Over Time')
    axes[-1].set_xlabel('Date')
    axes[-1].set_ylabel('Variable')
    axes[-1].grid(True)

    plt.tight_layout()
    plt.show()

# Execute the analysis
observations, free_energy_data, constraint_verification_list = process_observations(variables)
plot_time_series_and_metrics(variables, expected_ranges, free_energy_data, constraint_verification_list)