import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path
import seaborn as sns
from scipy import stats
import logging

def plot_data(data: pd.DataFrame, 
             constraints: pd.DataFrame, 
             controllable_variables_list: List[str],
             control_strategy: str = "active_inference",
             output_dir: Path = None):
    """
    Plot environmental variables with enhanced visualization and comparisons
    
    Args:
        data: DataFrame containing simulation history
        constraints: DataFrame with variable constraints
        controllable_variables_list: List of controllable variables
        control_strategy: Strategy used ("random" or "active_inference")
        output_dir: Directory to save plots
    """
    plt.ioff()  # Turn off interactive mode
    
    # Calculate number of rows and columns for subplots
    n_vars = len(data.columns) - 1  # Exclude timestep column
    n_cols = 5  # Set number of columns as 5
    n_rows = int(np.ceil(n_vars / n_cols))  # Calculate number of rows needed

    # Create figure and subplots
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 3*n_rows))
    fig.suptitle(f'Environmental Variables Evolution - {control_strategy.title()} Control', 
                 fontsize=14, y=1.02)
    axes = axes.flatten()

    # Plot each variable
    var_idx = 0
    for col in data.columns:
        if col != 'timestep':
            ax = axes[var_idx]

            # Plot the variable
            line = ax.plot(data['timestep'], data[col], '-', linewidth=2, 
                         label=f'{control_strategy.title()}')[0]

            # Add constraints if they exist for this variable
            if col in constraints['variable'].values:
                constraint = constraints[constraints['variable'] == col].iloc[0]
                ax.axhline(y=constraint['lower_constraint'], color='r', 
                          linestyle='--', alpha=0.8, label='Constraints')
                ax.axhline(y=constraint['upper_constraint'], color='r', 
                          linestyle='--', alpha=0.8)
                
                # Shade the constraint region
                ax.axhspan(constraint['lower_constraint'], 
                          constraint['upper_constraint'], 
                          color='g', alpha=0.1)

            # Add controllable indicator
            title = col.replace('_', ' ').title()
            if col in controllable_variables_list:
                title += "\n(Controllable)"
                ax.set_facecolor('#f0f9ff')  # Light blue background for controllable

            # Customize subplot
            ax.set_title(title)
            ax.set_xlabel('Timestep')
            ax.grid(True, alpha=0.3)
            ax.legend()

            var_idx += 1

    # Remove any empty subplots
    for idx in range(var_idx, len(axes)):
        fig.delaxes(axes[idx])

    # Adjust layout
    plt.tight_layout()
    
    # Save if output directory provided
    if output_dir:
        plt.savefig(output_dir / f'simulation_{control_strategy}.png', 
                   bbox_inches='tight', dpi=300)
    plt.close(fig)  # Close figure

def plot_comparison(random_data: pd.DataFrame, 
                   active_data: pd.DataFrame,
                   constraints: pd.DataFrame,
                   controllable_vars: List[str],
                   output_dir: Path):
    """Plot side-by-side comparison between random and active inference control"""
    plt.ioff()
    
    try:
        # Calculate number of variables and subplot layout
        variables = [col for col in random_data.columns if col != 'timestep']
        n_vars = len(variables)
        n_rows = n_vars
        n_cols = 2  # Side by side comparison
        
        # Create figure
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 4*n_rows))
        fig.suptitle('Random vs Active Inference Control Comparison', fontsize=16, y=1.02)
        
        # Plot each variable
        for idx, var in enumerate(variables):
            # Get constraint values if they exist
            constraint = constraints[constraints['variable'] == var].iloc[0]
            lower = constraint['lower_constraint']
            upper = constraint['upper_constraint']
            
            # Random control subplot
            ax_random = axes[idx, 0]
            ax_random.plot(random_data['timestep'], random_data[var], 
                         'b-', label='Random', alpha=0.7)
            ax_random.axhline(y=lower, color='r', linestyle='--', alpha=0.5)
            ax_random.axhline(y=upper, color='r', linestyle='--', alpha=0.5)
            ax_random.axhspan(lower, upper, color='g', alpha=0.1)
            
            # Active inference subplot
            ax_active = axes[idx, 1]
            ax_active.plot(active_data['timestep'], active_data[var], 
                         'g-', label='Active Inference', alpha=0.7)
            ax_active.axhline(y=lower, color='r', linestyle='--', alpha=0.5)
            ax_active.axhline(y=upper, color='r', linestyle='--', alpha=0.5)
            ax_active.axhspan(lower, upper, color='g', alpha=0.1)
            
            # Calculate time in constraints
            random_in_bounds = ((random_data[var] >= lower) & 
                              (random_data[var] <= upper)).mean() * 100
            active_in_bounds = ((active_data[var] >= lower) & 
                              (active_data[var] <= upper)).mean() * 100
            
            # Customize subplots
            title = var.replace('_', ' ').title()
            if var in controllable_vars:
                title += "\n(Controllable)"
            
            ax_random.set_title(f"{title}\nRandom Control\n{random_in_bounds:.1f}% In Bounds")
            ax_active.set_title(f"{title}\nActive Inference\n{active_in_bounds:.1f}% In Bounds")
            
            for ax in [ax_random, ax_active]:
                ax.grid(True, alpha=0.3)
                ax.legend()
                ax.set_xlabel('Timestep')
            
            # Highlight controllable variables
            if var in controllable_vars:
                ax_random.set_facecolor('#f0f9ff')
                ax_active.set_facecolor('#f0f9ff')
        
        plt.tight_layout()
        
        if output_dir:
            plt.savefig(output_dir / 'strategy_comparison.png', 
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_comparison: {e}")
        plt.close('all')

def plot_satisfaction_rates(random_data: pd.DataFrame, 
                          active_data: pd.DataFrame,
                          constraints: pd.DataFrame,
                          output_dir: Path = None):
    """
    Plot constraint satisfaction rates over time for both strategies
    
    Args:
        random_data: DataFrame from random control simulation
        active_data: DataFrame from active inference simulation
        constraints: DataFrame with variable constraints
        output_dir: Directory to save plots
    """
    plt.ioff()  # Turn off interactive mode
    
    try:
        def calculate_satisfaction(data: pd.DataFrame, 
                                 constraints: pd.DataFrame) -> List[float]:
            """Calculate satisfaction rate at each timestep"""
            satisfaction_rates = []
            for _, row in data.iterrows():
                satisfied = 0
                total = 0
                for var in constraints['variable'].values:
                    constraint = constraints[constraints['variable'] == var].iloc[0]
                    if (row[var] >= constraint['lower_constraint'] and 
                        row[var] <= constraint['upper_constraint']):
                        satisfied += 1
                    total += 1
                satisfaction_rates.append(satisfied / total * 100)
            return satisfaction_rates
        
        # Calculate satisfaction rates
        random_rates = calculate_satisfaction(random_data, constraints)
        active_rates = calculate_satisfaction(active_data, constraints)
        
        # Create figure with two subplots side by side
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Constraint Satisfaction Rate Comparison', fontsize=14)
        
        # Plot random control
        ax1.plot(random_data['timestep'], random_rates, 
                color='blue', alpha=0.7)
        ax1.set_title('Random Control')
        ax1.set_xlabel('Timestep')
        ax1.set_ylabel('Satisfaction Rate (%)')
        ax1.grid(True, alpha=0.3)
        
        # Plot active inference
        ax2.plot(active_data['timestep'], active_rates, 
                color='green', alpha=0.7)
        ax2.set_title('Active Inference')
        ax2.set_xlabel('Timestep')
        ax2.set_ylabel('Satisfaction Rate (%)')
        ax2.grid(True, alpha=0.3)
        
        # Set same y-axis limits for both plots
        y_min = min(min(random_rates), min(active_rates))
        y_max = max(max(random_rates), max(active_rates))
        ax1.set_ylim(y_min, y_max)
        ax2.set_ylim(y_min, y_max)
        
        # Add mean satisfaction rate to titles
        random_mean = np.mean(random_rates)
        active_mean = np.mean(active_rates)
        ax1.set_title(f'Random Control\nMean Satisfaction: {random_mean:.1f}%')
        ax2.set_title(f'Active Inference\nMean Satisfaction: {active_mean:.1f}%')
        
        # Save if output directory provided
        if output_dir:
            plt.savefig(output_dir / 'satisfaction_rates.png', 
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_satisfaction_rates: {e}")
        plt.close('all')

def plot_correlation_heatmaps(random_data: pd.DataFrame, 
                            active_data: pd.DataFrame,
                            output_dir: Path = None):
    """
    Create side-by-side correlation heatmaps for both control strategies
    
    Args:
        random_data: DataFrame from random control simulation
        active_data: DataFrame from active inference simulation
        output_dir: Directory to save plots
    """
    plt.ioff()
    
    try:
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        fig.suptitle('Variable Correlation Comparison', fontsize=16)
        
        # Calculate correlations (excluding timestep)
        random_corr = random_data.drop('timestep', axis=1).corr()
        active_corr = active_data.drop('timestep', axis=1).corr()
        
        # Plot heatmaps
        sns.heatmap(random_corr, ax=ax1, cmap='RdBu_r', center=0, 
                   annot=True, fmt='.2f', square=True, cbar_kws={'label': 'Correlation'})
        sns.heatmap(active_corr, ax=ax2, cmap='RdBu_r', center=0,
                   annot=True, fmt='.2f', square=True, cbar_kws={'label': 'Correlation'})
        
        # Customize plots
        ax1.set_title('Random Control Correlations')
        ax2.set_title('Active Inference Correlations')
        
        # Rotate labels for better readability
        for ax in [ax1, ax2]:
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
            ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
        
        plt.tight_layout()
        
        if output_dir:
            plt.savefig(output_dir / 'correlation_heatmaps.png', 
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_correlation_heatmaps: {e}")
        plt.close('all')

def plot_state_distributions(random_data: pd.DataFrame,
                           active_data: pd.DataFrame,
                           constraints: pd.DataFrame,
                           output_dir: Path = None):
    """Plot distribution of time spent in each state"""
    plt.ioff()
    
    try:
        def calculate_state_distribution(data: pd.DataFrame, 
                                      constraints: pd.DataFrame) -> pd.DataFrame:
            results = []
            for var in constraints['variable'].values:
                constraint = constraints[constraints['variable'] == var].iloc[0]
                values = data[var]
                
                low = (values < constraint['lower_constraint']).mean() * 100
                high = (values > constraint['upper_constraint']).mean() * 100
                home = ((values >= constraint['lower_constraint']) & 
                       (values <= constraint['upper_constraint'])).mean() * 100
                
                results.append({
                    'Variable': var,
                    'LOW': low,
                    'HOMEOSTATIC': home,
                    'HIGH': high
                })
            return pd.DataFrame(results)
        
        # Calculate distributions
        random_dist = calculate_state_distribution(random_data, constraints)
        active_dist = calculate_state_distribution(active_data, constraints)
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
        fig.suptitle('Time Spent in Each State by Variable', fontsize=16)
        
        # Plot settings
        bar_width = 0.25
        colors = ['#ff9999', '#99ff99', '#9999ff']
        states = ['LOW', 'HOMEOSTATIC', 'HIGH']
        
        # Set x positions
        x = np.arange(len(random_dist['Variable']))
        
        # Random control plot
        bars1 = ax1.bar(x, random_dist['LOW'], bar_width, label='LOW', color=colors[0])
        bars2 = ax1.bar(x, random_dist['HOMEOSTATIC'], bar_width, 
                       bottom=random_dist['LOW'], label='HOMEOSTATIC', color=colors[1])
        bars3 = ax1.bar(x, random_dist['HIGH'], bar_width,
                       bottom=random_dist['LOW'] + random_dist['HOMEOSTATIC'],
                       label='HIGH', color=colors[2])
        
        # Active inference plot
        bars4 = ax2.bar(x, active_dist['LOW'], bar_width, label='LOW', color=colors[0])
        bars5 = ax2.bar(x, active_dist['HOMEOSTATIC'], bar_width,
                       bottom=active_dist['LOW'], label='HOMEOSTATIC', color=colors[1])
        bars6 = ax2.bar(x, active_dist['HIGH'], bar_width,
                       bottom=active_dist['LOW'] + active_dist['HOMEOSTATIC'],
                       label='HIGH', color=colors[2])
        
        # Customize plots
        for ax, title in zip([ax1, ax2], ['Random Control', 'Active Inference']):
            ax.set_title(f'{title} - State Distribution')
            ax.set_xlabel('Variables')
            ax.set_ylabel('Percentage of Time (%)')
            ax.set_ylim(0, 100)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Set x-ticks
            ax.set_xticks(x)
            ax.set_xticklabels(random_dist['Variable'], rotation=45, ha='right')
            
            # Add percentage labels on bars
            def add_labels(bars, values):
                for bar, value in zip(bars, values):
                    if value >= 5:  # Only show labels for values >= 5%
                        ax.text(bar.get_x() + bar.get_width()/2, bar.get_y() + bar.get_height()/2,
                               f'{value:.1f}%', ha='center', va='center', rotation=0)
            
            if ax == ax1:
                add_labels([b for b in bars1 if b.get_height() >= 5], random_dist['LOW'])
                add_labels([b for b in bars2 if b.get_height() >= 5], random_dist['HOMEOSTATIC'])
                add_labels([b for b in bars3 if b.get_height() >= 5], random_dist['HIGH'])
            else:
                add_labels([b for b in bars4 if b.get_height() >= 5], active_dist['LOW'])
                add_labels([b for b in bars5 if b.get_height() >= 5], active_dist['HOMEOSTATIC'])
                add_labels([b for b in bars6 if b.get_height() >= 5], active_dist['HIGH'])
        
        plt.tight_layout()
        
        if output_dir:
            plt.savefig(output_dir / 'state_distributions.png',
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_state_distributions: {e}")
        plt.close('all')

def plot_variable_distributions(random_data: pd.DataFrame,
                              active_data: pd.DataFrame,
                              constraints: pd.DataFrame,
                              output_dir: Path = None):
    """
    Plot kernel density estimates of variable distributions for both strategies
    
    Args:
        random_data: DataFrame from random control simulation
        active_data: DataFrame from active inference simulation
        constraints: DataFrame with variable constraints
        output_dir: Directory to save plots
    """
    plt.ioff()
    
    try:
        # Calculate number of variables and subplot layout
        n_vars = len(constraints)
        n_cols = 3
        n_rows = int(np.ceil(n_vars / n_cols))
        
        # Create figure
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 4*n_rows))
        fig.suptitle('Variable Value Distributions Comparison', fontsize=16)
        axes = axes.flatten()
        
        # Plot each variable
        for idx, var in enumerate(constraints['variable']):
            ax = axes[idx]
            
            # Get constraint values
            constraint = constraints[constraints['variable'] == var].iloc[0]
            lower = constraint['lower_constraint']
            upper = constraint['upper_constraint']
            
            # Plot density estimates
            sns.kdeplot(data=random_data[var], ax=ax, color='blue', 
                       alpha=0.5, label='Random')
            sns.kdeplot(data=active_data[var], ax=ax, color='green',
                       alpha=0.5, label='Active Inference')
            
            # Add constraint lines
            ax.axvline(x=lower, color='r', linestyle='--', alpha=0.5)
            ax.axvline(x=upper, color='r', linestyle='--', alpha=0.5)
            
            # Add statistical test
            stat, pval = stats.ks_2samp(random_data[var], active_data[var])
            ax.set_title(f'{var.replace("_", " ").title()}\np={pval:.3f}')
            
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # Remove empty subplots
        for idx in range(len(constraints), len(axes)):
            fig.delaxes(axes[idx])
        
        plt.tight_layout()
        
        if output_dir:
            plt.savefig(output_dir / 'variable_distributions.png',
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_variable_distributions: {e}")
        plt.close('all')

def plot_control_actions(random_data: pd.DataFrame,
                        active_data: pd.DataFrame,
                        controllable_vars: List[str],
                        output_dir: Path):
    """Plot control action distributions and patterns"""
    plt.ioff()
    
    try:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Control Action Analysis', fontsize=16)
        
        # Calculate control actions (differences between timesteps)
        def get_control_actions(data: pd.DataFrame):
            actions = {}
            for var in controllable_vars:
                # Calculate single-step differences and trim to same length
                actions[var] = np.diff(data[var].values)
            return actions
        
        random_actions = get_control_actions(random_data)
        active_actions = get_control_actions(active_data)
        
        # Ensure all action arrays have the same length
        min_length = min(len(random_actions[controllable_vars[0]]),
                        len(active_actions[controllable_vars[0]]))
        
        # Trim all arrays to minimum length
        for var in controllable_vars:
            random_actions[var] = random_actions[var][:min_length]
            active_actions[var] = active_actions[var][:min_length]
        
        # Plot 1: Action Distribution Comparison
        ax = axes[0, 0]
        for var in controllable_vars:
            sns.kdeplot(data=random_actions[var], ax=ax, 
                       label=f'Random-{var}', linestyle='--')
            sns.kdeplot(data=active_actions[var], ax=ax, 
                       label=f'Active-{var}')
        ax.set_title('Control Action Distributions')
        ax.set_xlabel('Action Magnitude')
        ax.set_ylabel('Density')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Plot 2: Action Time Series
        ax = axes[0, 1]
        timesteps = np.arange(min_length)
        for var in controllable_vars:
            ax.plot(timesteps, random_actions[var], alpha=0.3, linestyle='--',
                   label=f'Random-{var}')
            ax.plot(timesteps, active_actions[var], alpha=0.7,
                   label=f'Active-{var}')
        ax.set_title('Control Actions Over Time')
        ax.set_xlabel('Timestep')
        ax.set_ylabel('Action Magnitude')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Plot 3: Action Autocorrelation
        ax = axes[1, 0]
        max_lag = min(50, min_length // 4)
        for var in controllable_vars:
            # Calculate autocorrelation for both strategies
            random_acf = [1.0] + [np.corrcoef(random_actions[var][:-i], 
                                        random_actions[var][i:])[0,1] 
                                for i in range(1, max_lag)]
            active_acf = [1.0] + [np.corrcoef(active_actions[var][:-i], 
                                           active_actions[var][i:])[0,1] 
                               for i in range(1, max_lag)]
            
            ax.plot(range(len(random_acf)), random_acf, linestyle='--', 
                   alpha=0.3, label=f'Random-{var}')
            ax.plot(range(len(active_acf)), active_acf, alpha=0.7,
                   label=f'Active-{var}')
        ax.set_title('Control Action Autocorrelation')
        ax.set_xlabel('Lag')
        ax.set_ylabel('Correlation')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Plot 4: Action Cross-correlation Matrix
        ax = axes[1, 1]
        all_actions = pd.DataFrame({
            f'Random-{var}': random_actions[var] for var in controllable_vars
        })
        all_actions.update({
            f'Active-{var}': active_actions[var] for var in controllable_vars
        })
        
        # Create correlation matrix heatmap
        sns.heatmap(all_actions.corr(), ax=ax, cmap='RdBu_r', center=0,
                   annot=True, fmt='.2f', square=True)
        ax.set_title('Control Action Correlations')
        
        # Adjust layout to prevent overlap
        plt.tight_layout(rect=[0, 0.03, 0.95, 0.95])
        
        if output_dir:
            plt.savefig(output_dir / 'control_actions_analysis.png',
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_control_actions: {e}")
        plt.close('all')

def plot_state_transitions(random_data: pd.DataFrame,
                         active_data: pd.DataFrame,
                         constraints: pd.DataFrame,
                         output_dir: Path):
    """Plot state transition patterns and statistics"""
    plt.ioff()
    
    try:
        def get_states(data: pd.DataFrame, constraints: pd.DataFrame):
            """Convert values to states (LOW=0, HOME=1, HIGH=2)"""
            states = pd.DataFrame()
            for var in constraints['variable']:
                constraint = constraints[constraints['variable'] == var].iloc[0]
                values = data[var]
                states[var] = np.where(values < constraint['lower_constraint'], 0,
                                     np.where(values > constraint['upper_constraint'], 2, 1))
            return states
        
        def get_transition_matrix(states: pd.DataFrame, var: str):
            """Calculate transition matrix with handling for zero-sum rows"""
            transitions = np.zeros((3, 3))
            for i in range(len(states)-1):
                current = states[var].iloc[i]
                next_state = states[var].iloc[i+1]
                transitions[int(current), int(next_state)] += 1
            
            # Handle zero-sum rows
            row_sums = transitions.sum(axis=1)
            for i in range(3):
                if row_sums[i] == 0:
                    transitions[i] = [0, 0, 0]  # Set to zeros instead of dividing
                else:
                    transitions[i] = transitions[i] / row_sums[i]
            
            return transitions
        
        random_states = get_states(random_data, constraints)
        active_states = get_states(active_data, constraints)
        
        # Create visualization
        n_vars = len(constraints)
        fig, axes = plt.subplots(n_vars, 2, figsize=(12, 4*n_vars))
        fig.suptitle('State Transition Analysis', fontsize=16)
        
        for idx, var in enumerate(constraints['variable']):
            # Random control transitions
            ax = axes[idx, 0]
            trans_mat = get_transition_matrix(random_states, var)
            sns.heatmap(trans_mat, ax=ax, cmap='YlOrRd', annot=True, fmt='.2f',
                       xticklabels=['LOW', 'HOME', 'HIGH'],
                       yticklabels=['LOW', 'HOME', 'HIGH'])
            ax.set_title(f'{var} - Random Control')
            
            # Active inference transitions
            ax = axes[idx, 1]
            trans_mat = get_transition_matrix(active_states, var)
            sns.heatmap(trans_mat, ax=ax, cmap='YlOrRd', annot=True, fmt='.2f',
                       xticklabels=['LOW', 'HOME', 'HIGH'],
                       yticklabels=['LOW', 'HOME', 'HIGH'])
            ax.set_title(f'{var} - Active Inference')
        
        plt.tight_layout()
        
        if output_dir:
            plt.savefig(output_dir / 'state_transitions.png',
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_state_transitions: {e}")
        plt.close('all')

def plot_active_inference_analysis(agent_data: Dict[str, List],
                                 output_dir: Path):
    """Plot detailed analysis of active inference agent's decision making
    
    Args:
        agent_data: Dictionary containing:
            - state_beliefs: List of belief distributions over time
            - policy_preferences: List of policy preferences
            - free_energy: List of expected free energy values
            - selected_actions: List of actual actions taken
    """
    plt.ioff()
    
    try:
        fig = plt.figure(figsize=(15, 12))
        gs = plt.GridSpec(3, 2, figure=fig)
        fig.suptitle('Active Inference Agent Analysis', fontsize=16)
        
        # Plot 1: State Belief Evolution
        ax1 = fig.add_subplot(gs[0, :])
        beliefs_data = np.array(agent_data['state_beliefs'])
        im = ax1.imshow(beliefs_data.T, aspect='auto', cmap='viridis')
        ax1.set_title('State Belief Evolution')
        ax1.set_xlabel('Timestep')
        ax1.set_ylabel('State')
        ax1.set_yticks([0, 1, 2])
        ax1.set_yticklabels(['LOW', 'HOME', 'HIGH'])
        plt.colorbar(im, ax=ax1, label='Belief Probability')
        
        # Plot 2: Policy Preferences Over Time
        ax2 = fig.add_subplot(gs[1, 0])
        preferences_data = np.array(agent_data['policy_preferences'])
        im = ax2.imshow(preferences_data.T, aspect='auto', cmap='RdYlBu')
        ax2.set_title('Policy Preferences')
        ax2.set_xlabel('Timestep')
        ax2.set_ylabel('Action')
        ax2.set_yticks([0, 1, 2])
        ax2.set_yticklabels(['DECREASE', 'MAINTAIN', 'INCREASE'])
        plt.colorbar(im, ax=ax2, label='Preference Strength')
        
        # Plot 3: Expected Free Energy
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(agent_data['free_energy'], 'k-', alpha=0.7)
        ax3.set_title('Expected Free Energy')
        ax3.set_xlabel('Timestep')
        ax3.set_ylabel('Free Energy')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Action Selection Analysis
        ax4 = fig.add_subplot(gs[2, :])
        actions = np.array(agent_data['selected_actions'])
        unique_actions, counts = np.unique(actions, return_counts=True)
        
        # Create stacked bar chart showing action transitions
        transitions = np.zeros((3, 3))
        for i in range(len(actions)-1):
            transitions[int(actions[i]), int(actions[i+1])] += 1
            
        # Normalize transitions
        transitions = transitions / transitions.sum(axis=1, keepdims=True)
        
        sns.heatmap(transitions, ax=ax4, cmap='YlOrRd', annot=True, fmt='.2f',
                   xticklabels=['DECREASE', 'MAINTAIN', 'INCREASE'],
                   yticklabels=['DECREASE', 'MAINTAIN', 'INCREASE'])
        ax4.set_title('Action Transition Probabilities')
        
        plt.tight_layout()
        
        if output_dir:
            plt.savefig(output_dir / 'active_inference_analysis.png',
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_active_inference_analysis: {e}")
        plt.close('all')

def plot_system_stability_analysis(random_data: pd.DataFrame,
                                 active_data: pd.DataFrame,
                                 constraints: pd.DataFrame,
                                 output_dir: Path):
    """Analyze and visualize system stability metrics"""
    plt.ioff()
    
    try:
        fig = plt.figure(figsize=(15, 12))
        gs = plt.GridSpec(2, 2, figure=fig)
        fig.suptitle('System Stability Analysis', fontsize=16)
        
        # Plot 1: Phase Space Trajectories
        ax1 = fig.add_subplot(gs[0, 0], projection='3d')
        ax1.plot(random_data['forest_health'], 
                random_data['carbon_sequestration'],
                random_data['riparian_buffer_width'],
                'b-', alpha=0.5, label='Random')
        ax1.plot(active_data['forest_health'],
                active_data['carbon_sequestration'],
                active_data['riparian_buffer_width'],
                'g-', alpha=0.5, label='Active')
        ax1.set_title('Control Variable Phase Space')
        ax1.set_xlabel('Forest Health')
        ax1.set_ylabel('Carbon Seq.')
        ax1.set_zlabel('Buffer Width')
        ax1.legend()
        
        # Plot 2: Stability Metrics
        ax2 = fig.add_subplot(gs[0, 1])
        
        def calculate_stability_metrics(data: pd.DataFrame, 
                                     constraints: pd.DataFrame) -> Dict[str, float]:
            metrics = {}
            for var in constraints['variable']:
                values = data[var]
                constraint = constraints[constraints['variable'] == var].iloc[0]
                target = (constraint['upper_constraint'] + constraint['lower_constraint']) / 2
                
                # Calculate metrics
                metrics[f"{var}_variance"] = values.var()
                metrics[f"{var}_mean_deviation"] = np.abs(values - target).mean()
                metrics[f"{var}_max_deviation"] = np.abs(values - target).max()
                
            return metrics
        
        random_metrics = calculate_stability_metrics(random_data, constraints)
        active_metrics = calculate_stability_metrics(active_data, constraints)
        
        # Create comparison bar plot
        metrics_df = pd.DataFrame({
            'Random': random_metrics,
            'Active': active_metrics
        })
        metrics_df.plot(kind='bar', ax=ax2)
        ax2.set_title('Stability Metrics Comparison')
        ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Control Effort Analysis
        ax3 = fig.add_subplot(gs[1, 0])
        
        def calculate_control_effort(data: pd.DataFrame, 
                                  controllable_vars: List[str]) -> pd.Series:
            efforts = {}
            for var in controllable_vars:
                efforts[var] = np.abs(np.diff(data[var])).sum()
            return pd.Series(efforts)
        
        random_effort = calculate_control_effort(random_data, 
                                               ['forest_health', 'carbon_sequestration', 
                                                'riparian_buffer_width'])
        active_effort = calculate_control_effort(active_data,
                                               ['forest_health', 'carbon_sequestration',
                                                'riparian_buffer_width'])
        
        effort_df = pd.DataFrame({
            'Random': random_effort,
            'Active': active_effort
        })
        effort_df.plot(kind='bar', ax=ax3)
        ax3.set_title('Total Control Effort')
        ax3.set_ylabel('Cumulative Absolute Change')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: System Response Analysis
        ax4 = fig.add_subplot(gs[1, 1])
        
        def calculate_response_metrics(data: pd.DataFrame) -> Dict[str, float]:
            metrics = {}
            for var in data.columns:
                if var != 'timestep':
                    # Calculate various response metrics
                    values = data[var]
                    metrics[f"{var}_settling_time"] = len(values) - np.argmax(
                        (np.abs(values - target) <= tolerance)[::-1]
                    )
                    metrics[f"{var}_overshoot"] = (
                        (values.max() - values.iloc[-1]) / values.iloc[-1] * 100
                    )
            return metrics
        
        random_response = calculate_response_metrics(random_data)
        active_response = calculate_response_metrics(active_data)
        
        response_df = pd.DataFrame({
            'Random': random_response,
            'Active': active_response
        })
        response_df.plot(kind='bar', ax=ax4)
        ax4.set_title('System Response Characteristics')
        ax4.set_xticklabels(ax4.get_xticklabels(), rotation=45, ha='right')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_dir:
            plt.savefig(output_dir / 'system_stability_analysis.png',
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_system_stability_analysis: {e}")
        plt.close('all')

def generate_all_visualizations(random_data: pd.DataFrame,
                              active_data: pd.DataFrame,
                              constraints: pd.DataFrame,
                              controllable_vars: List[str],
                              output_dir: Path,
                              logger: logging.Logger,
                              agent_data: Optional[Dict] = None):
    """Generate and save all visualization types with logging"""
    # Create visualization directory
    vis_dir = output_dir / 'visualizations'
    vis_dir.mkdir(exist_ok=True)
    
    try:
        # Basic visualizations
        visualizations = [
            ("individual strategy plots", lambda: (
                plot_data(random_data, constraints, controllable_vars, 'random', vis_dir),
                plot_data(active_data, constraints, controllable_vars, 'active_inference', vis_dir)
            )),
            ("strategy comparison", lambda: plot_comparison(
                random_data, active_data, constraints, controllable_vars, vis_dir
            )),
            ("satisfaction rates", lambda: plot_satisfaction_rates(
                random_data, active_data, constraints, vis_dir
            )),
            ("correlation heatmaps", lambda: plot_correlation_heatmaps(
                random_data, active_data, vis_dir
            )),
            ("state distributions", lambda: plot_state_distributions(
                random_data, active_data, constraints, vis_dir
            )),
            ("variable distributions", lambda: plot_variable_distributions(
                random_data, active_data, constraints, vis_dir
            )),
            ("control actions", lambda: plot_control_actions(
                random_data, active_data, controllable_vars, vis_dir
            )),
            ("state transitions", lambda: plot_state_transitions(
                random_data, active_data, constraints, vis_dir
            )),
            ("system stability", lambda: plot_system_stability_analysis(
                random_data, active_data, constraints, vis_dir
            ))
        ]

        # Generate each visualization with error handling
        generated_files = []
        for name, plot_func in visualizations:
            try:
                logger.info(f"Generating {name}...")
                plot_func()
                logger.info(f"✓ {name.title()} saved")
            except Exception as e:
                logger.error(f"Error generating {name}: {str(e)}")

        # Generate active inference analysis if data available
        if agent_data is not None:
            try:
                logger.info("Generating active inference analysis...")
                plot_active_inference_analysis(agent_data, vis_dir)
                logger.info("✓ Active inference analysis saved")
            except Exception as e:
                logger.error(f"Error generating active inference analysis: {str(e)}")

        # Log all generated files
        logger.info("\nGenerated visualization files:")
        for file in sorted(vis_dir.glob('*.png')):
            logger.info(f"  - {file.name}")

        # Generate combined report
        try:
            logger.info("\nGenerating combined analysis report...")
            generate_analysis_report(
                random_data=random_data,
                active_data=active_data,
                constraints=constraints,
                controllable_vars=controllable_vars,
                agent_data=agent_data,
                generated_files=generated_files,
                output_dir=vis_dir
            )
            logger.info("✓ Analysis report saved")
        except Exception as e:
            logger.error(f"Error generating analysis report: {str(e)}")

        return True

    except Exception as e:
        logger.error(f"Error in visualization generation: {str(e)}")
        plt.close('all')
        return False

def generate_analysis_report(random_data: pd.DataFrame,
                           active_data: pd.DataFrame,
                           constraints: pd.DataFrame,
                           controllable_vars: List[str],
                           agent_data: Optional[Dict],
                           generated_files: List[str],
                           output_dir: Path):
    """Generate a comprehensive analysis report combining all visualizations"""
    try:
        # Create report figure
        fig = plt.figure(figsize=(20, 30))
        gs = plt.GridSpec(5, 2, figure=fig)
        fig.suptitle('Ecosystem Control Strategy Analysis Report', fontsize=20, y=0.98)

        # 1. Overall Performance Comparison
        ax1 = fig.add_subplot(gs[0, :])
        plot_overall_performance_comparison(random_data, active_data, constraints, ax1)

        # 2. Control Strategy Effectiveness
        ax2 = fig.add_subplot(gs[1, 0])
        plot_control_effectiveness(random_data, active_data, controllable_vars, ax2)

        # 3. System Stability Analysis
        ax3 = fig.add_subplot(gs[1, 1])
        plot_stability_metrics(random_data, active_data, constraints, ax3)

        # 4. State Distribution Analysis
        ax4 = fig.add_subplot(gs[2, :])
        plot_state_distribution_summary(random_data, active_data, constraints, ax4)

        # 5. Control Action Analysis
        ax5 = fig.add_subplot(gs[3, 0])
        plot_control_action_summary(random_data, active_data, controllable_vars, ax5)

        # 6. Active Inference Performance (if data available)
        ax6 = fig.add_subplot(gs[3, 1])
        if agent_data:
            plot_active_inference_summary(agent_data, ax6)
        else:
            ax6.text(0.5, 0.5, 'Active Inference Data Not Available',
                    ha='center', va='center')

        # 7. Key Findings and Recommendations
        ax7 = fig.add_subplot(gs[4, :])
        plot_key_findings(random_data, active_data, constraints, ax7)

        plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.96])
        
        # Save report
        plt.savefig(output_dir / 'analysis_report.png', dpi=300, bbox_inches='tight')
        plt.close(fig)

    except Exception as e:
        raise Exception(f"Error generating analysis report: {str(e)}")

def plot_overall_performance_comparison(random_data: pd.DataFrame,
                                     active_data: pd.DataFrame,
                                     constraints: pd.DataFrame,
                                     ax: plt.Axes):
    """Plot overall performance metrics comparison"""
    # Calculate performance metrics
    metrics = calculate_performance_metrics(random_data, active_data, constraints)
    
    # Create grouped bar plot
    x = np.arange(len(metrics['metrics']))
    width = 0.35
    
    ax.bar(x - width/2, metrics['random'], width, label='Random Control',
           color='lightblue', alpha=0.7)
    ax.bar(x + width/2, metrics['active'], width, label='Active Inference',
           color='lightgreen', alpha=0.7)
    
    ax.set_ylabel('Performance Score')
    ax.set_title('Overall Performance Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics['metrics'], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add value labels
    for i, v in enumerate(metrics['random']):
        ax.text(i - width/2, v, f'{v:.1f}', ha='center', va='bottom')
    for i, v in enumerate(metrics['active']):
        ax.text(i + width/2, v, f'{v:.1f}', ha='center', va='bottom')

def calculate_performance_metrics(random_data: pd.DataFrame,
                               active_data: pd.DataFrame,
                               constraints: pd.DataFrame) -> Dict:
    """Calculate comprehensive performance metrics for both strategies"""
    metrics = {
        'metrics': [
            'Constraint Satisfaction (%)',
            'Stability Score',
            'Control Efficiency',
            'Response Time',
            'Overall Score'
        ],
        'random': [],
        'active': []
    }
    
    # Calculate metrics for both strategies
    for data, key in [(random_data, 'random'), (active_data, 'active')]:
        # 1. Constraint Satisfaction
        satisfaction = calculate_satisfaction_rate(data, constraints)
        
        # 2. Stability Score
        stability = calculate_stability_score(data)
        
        # 3. Control Efficiency
        efficiency = calculate_control_efficiency(data)
        
        # 4. Response Time
        response = calculate_response_time(data)
        
        # 5. Overall Score (weighted average)
        overall = (satisfaction * 0.4 + stability * 0.3 + 
                  efficiency * 0.2 + response * 0.1)
        
        metrics[key] = [satisfaction, stability, efficiency, response, overall]
    
    return metrics

# Add helper functions for metric calculations...