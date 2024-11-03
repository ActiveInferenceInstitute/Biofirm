import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
from pathlib import Path
import seaborn as sns
from scipy import stats
import logging

def get_unit(variable_name: str) -> str:
    """Get the appropriate unit label for a variable
    
    Args:
        variable_name: Name of the ecological variable
        
    Returns:
        String containing the unit label
    """
    # Define units for each variable type
    units = {
        'forest_health': 'Health Index',
        'carbon_sequestration': 'Tons CO2/ha',
        'wildlife_habitat_quality': 'Habitat Score',
        'riparian_buffer_width': 'Meters',
        'soil_organic_matter': 'Percent',
        'water_quality': 'Quality Index',
        'biodiversity': 'Species Count',
        'erosion_control': 'Erosion Index'
    }
    
    # Return unit if defined, otherwise return generic "Value"
    return units.get(variable_name, 'Value')

def calculate_satisfaction_rate(data: pd.DataFrame, constraints: pd.DataFrame) -> float:
    """Calculate percentage of time variables are within constraints"""
    satisfaction_count = 0
    total_checks = 0
    
    for var in constraints['variable'].values:
        if var in data.columns:
            constraint = constraints[constraints['variable'] == var].iloc[0]
            in_bounds = ((data[var] >= constraint['lower_constraint']) & 
                        (data[var] <= constraint['upper_constraint']))
            satisfaction_count += in_bounds.sum()
            total_checks += len(data)
    
    return (satisfaction_count / total_checks * 100) if total_checks > 0 else 0.0

def plot_data(data: pd.DataFrame, 
             constraints: pd.DataFrame, 
             controllable_variables: List[str],
             control_strategy: str = "active_inference",
             output_dir: Path = None):
    """Plot environmental variables with enhanced visualization and error handling"""
    plt.ioff()
    
    try:
        n_vars = len(data.columns) - 1  # Exclude timestep
        n_cols = min(5, n_vars)  # Adjust columns based on variables
        n_rows = int(np.ceil(n_vars / n_cols))

        # Create figure with two subplots side by side
        fig = plt.figure(figsize=(24, 3*n_rows))
        gs = plt.GridSpec(n_rows, n_cols*2, figure=fig)
        
        # Enhanced title based on control strategy
        if control_strategy == 'active_inference':
            title = 'Active Inference Control'
            color = 'royalblue'
            alpha = 0.9
        else:
            title = 'Random Control'
            color = 'gray'
            alpha = 0.7
            
        fig.suptitle(f'{title}: Variable Evolution Over Time', fontsize=16, y=1.02)

        var_idx = 0
        for col in data.columns:
            if col != 'timestep':
                # Calculate subplot position
                row = var_idx // n_cols
                col_pos = var_idx % n_cols
                
                # Create subplot
                ax = fig.add_subplot(gs[row, col_pos])
                
                # Determine if variable is controlled
                is_controlled = col in controllable_variables
                
                # Plot with enhanced styling
                ax.plot(data['timestep'], data[col], 
                       linewidth=2.5 if is_controlled else 1.5,
                       alpha=alpha,
                       color=color,
                       label='Controlled' if is_controlled else 'Uncontrolled')

                # Add constraints with improved visibility
                if col in constraints['variable'].values:
                    constraint = constraints[constraints['variable'] == col].iloc[0]
                    
                    # Target range
                    ax.axhspan(constraint['lower_constraint'], 
                              constraint['upper_constraint'],
                              color='green', alpha=0.1, label='Target Range')
                    
                    # Constraint lines
                    ax.axhline(y=constraint['lower_constraint'], color='red', 
                              linestyle='--', alpha=0.5)
                    ax.axhline(y=constraint['upper_constraint'], color='red', 
                              linestyle='--', alpha=0.5)

                # Enhanced title and labels
                title = col.replace('_', ' ').title()
                if is_controlled:
                    title += "\n[Controlled]"
                else:
                    title += "\n[Uncontrolled]"
                    
                ax.set_title(title, pad=10)
                ax.set_xlabel('Time Step')
                ax.set_ylabel(f"{get_unit(col)}")
                
                # Improved grid and legend
                ax.grid(True, alpha=0.3, linestyle=':')
                ax.legend(loc='upper right', framealpha=0.9)

                # Calculate and display statistics
                mean_val = data[col].mean()
                std_val = data[col].std()
                in_bounds = 0
                if col in constraints['variable'].values:
                    constraint = constraints[constraints['variable'] == col].iloc[0]
                    in_bounds = ((data[col] >= constraint['lower_constraint']) & 
                               (data[col] <= constraint['upper_constraint'])).mean() * 100
                
                stats_text = f'Mean: {mean_val:.1f}\nStd: {std_val:.1f}\nIn Target: {in_bounds:.1f}%'
                ax.text(0.95, 0.05, stats_text,
                       transform=ax.transAxes,
                       verticalalignment='bottom',
                       horizontalalignment='right',
                       bbox=dict(facecolor='white', alpha=0.8))

                var_idx += 1

        # Adjust layout
        plt.tight_layout()
        
        if output_dir:
            plt.savefig(output_dir / f'simulation_{control_strategy}.png', 
                       bbox_inches='tight', dpi=300)
        plt.close(fig)
        
    except Exception as e:
        print(f"Error in plot_data: {str(e)}")
        plt.close('all')

def plot_comparison(random_data: pd.DataFrame, 
                   active_data: pd.DataFrame,
                   constraints: pd.DataFrame,
                   controllable_vars: List[str],
                   output_dir: Path):
    """Plot side-by-side comparison of control strategies"""
    plt.ioff()
    
    try:
        variables = [col for col in random_data.columns if col != 'timestep']
        n_rows = len(variables)
        n_cols = 2
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 4*n_rows))
        fig.suptitle('Control Strategy Comparison\nActive Inference (Right) vs Natural Evolution (Left)', 
                    fontsize=16, y=1.02)
        
        for idx, var in enumerate(variables):
            is_controlled = var in controllable_vars
            
            # Enhanced styling
            if is_controlled:
                color = 'royalblue'
                alpha = 0.9
                line_width = 2.5
                label = 'Actively Controlled'
            else:
                color = 'gray'
                alpha = 0.7
                line_width = 1.5
                label = 'Uncontrolled'
            
            # Get constraints
            constraint = constraints[constraints['variable'] == var].iloc[0]
            lower = constraint['lower_constraint']
            upper = constraint['upper_constraint']
            
            # Plot both strategies
            for col_idx, (data, strategy) in enumerate([
                (random_data, 'Natural Evolution'),
                (active_data, 'Active Inference')
            ]):
                ax = axes[idx, col_idx]
                
                # Plot data with enhanced styling
                ax.plot(data['timestep'], data[var], color=color,
                       linewidth=line_width, alpha=alpha,
                       label=label if strategy == 'Active Inference' else 'Uncontrolled')
                
                # Add target range
                ax.axhspan(lower, upper, color='green', alpha=0.1, label='Target Range')
                ax.axhline(y=lower, color='red', linestyle='--', alpha=0.5)
                ax.axhline(y=upper, color='red', linestyle='--', alpha=0.5)
                
                # Calculate performance metrics
                in_bounds = ((data[var] >= lower) & (data[var] <= upper)).mean() * 100
                mean_val = data[var].mean()
                std_val = data[var].std()
                
                # Enhanced title with metrics
                control_status = "[Controlled]" if (is_controlled and strategy == 'Active Inference') else "[Uncontrolled]"
                title = (f"{var.replace('_', ' ').title()}\n{control_status}\n"
                        f"In Target: {in_bounds:.1f}%\n"
                        f"Mean: {mean_val:.1f} ± {std_val:.1f}")
                ax.set_title(title)
                
                # Improved aesthetics
                ax.grid(True, alpha=0.3, linestyle=':')
                ax.set_xlabel('Time Step')
                ax.set_ylabel(f"{get_unit(var)}")
                ax.legend(loc='upper right', framealpha=0.9)
                
                # Set background color
                if is_controlled and strategy == 'Active Inference':
                    ax.set_facecolor('#f0f9ff')
                else:
                    ax.set_facecolor('#fafafa')
        
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
    """Create side-by-side correlation heatmaps for both control strategies"""
    plt.ioff()
    
    try:
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        fig.suptitle('Variable Correlation Comparison', fontsize=16)
        
        # Calculate correlations for all variables (excluding timestep)
        def get_correlations(df: pd.DataFrame) -> pd.DataFrame:
            # Remove timestep and calculate correlations
            data = df.drop('timestep', axis=1)
            # Handle zero variance columns
            valid_cols = data.columns[data.std() != 0]
            corr = pd.DataFrame(np.eye(len(data.columns)), 
                              columns=data.columns, 
                              index=data.columns)
            if len(valid_cols) > 0:
                corr.loc[valid_cols, valid_cols] = data[valid_cols].corr()
            return corr
        
        random_corr = get_correlations(random_data)
        active_corr = get_correlations(active_data)
        
        # Plot heatmaps with consistent dimensions
        sns.heatmap(random_corr, ax=ax1, cmap='RdBu_r', center=0, 
                   annot=True, fmt='.2f', square=True)
        sns.heatmap(active_corr, ax=ax2, cmap='RdBu_r', center=0,
                   annot=True, fmt='.2f', square=True)
        
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
                              output_dir: Path):
    """Plot distribution of variables under different control strategies"""
    try:
        # Get variables excluding timestep
        variables = [col for col in random_data.columns if col != 'timestep']
        n_vars = len(variables)
        
        # Create subplots grid
        n_cols = min(5, n_vars)
        n_rows = int(np.ceil(n_vars / n_cols))
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(4*n_cols, 4*n_rows))
        
        # Handle single row/column cases
        if n_rows == 1 and n_cols == 1:
            axes = np.array([[axes]])
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        elif n_cols == 1:
            axes = axes.reshape(-1, 1)
            
        # Plot distributions for each variable
        for idx, var in enumerate(variables):
            row = idx // n_cols
            col = idx % n_cols
            ax = axes[row, col]
            
            # Plot distributions
            sns.kdeplot(data=random_data[var], ax=ax, color='gray', 
                       label='Random', alpha=0.6)
            sns.kdeplot(data=active_data[var], ax=ax, color='royalblue',
                       label='Active', alpha=0.6)
            
            # Add constraints if available
            if var in constraints['variable'].values:
                constraint = constraints[constraints['variable'] == var].iloc[0]
                ax.axvline(constraint['lower_constraint'], color='red', 
                          linestyle='--', alpha=0.5)
                ax.axvline(constraint['upper_constraint'], color='red',
                          linestyle='--', alpha=0.5)
                ax.axvspan(constraint['lower_constraint'], 
                          constraint['upper_constraint'],
                          color='green', alpha=0.1)
            
            ax.set_title(var.replace('_', ' ').title())
            if idx == 0:  # Only show legend for first plot
                ax.legend()
            
            ax.grid(True, alpha=0.3)
        
        # Remove empty subplots
        for idx in range(len(variables), n_rows * n_cols):
            row = idx // n_cols
            col = idx % n_cols
            fig.delaxes(axes[row, col])
        
        plt.suptitle('Variable Distributions: Random vs Active Control', y=1.02)
        plt.tight_layout()
        
        plt.savefig(output_dir / 'variable_distributions.png',
                   bbox_inches='tight', dpi=300)
        plt.close()
        
    except Exception as e:
        print(f"Error generating variable distributions: {str(e)}")
        plt.close('all')

def plot_control_actions(random_data: pd.DataFrame,
                        active_data: pd.DataFrame,
                        controllable_vars: List[str],
                        output_dir: Path,
                        logger: Optional[logging.Logger] = None):
    """Plot control action distributions with improved handling
    
    Args:
        random_data: DataFrame containing random control data
        active_data: DataFrame containing active inference control data
        controllable_vars: List of controllable variable names
        output_dir: Directory to save visualization
        logger: Optional logger instance
    """
    # Use print if logger not provided
    log = logger.info if logger else print
    
    try:
        fig, axes = plt.subplots(5, 2, figsize=(15, 20))
        axes = axes.flatten()
        
        for i, var in enumerate(controllable_vars):
            if i >= len(axes):
                break
                
            ax = axes[i]
            
            # Add small random noise for numerical stability
            def add_jitter(data, var_name):
                if var_name in data.columns:
                    values = data[var_name].values
                    noise = np.random.normal(0, 1e-6, size=len(values))
                    return values + noise
                return np.array([])
            
            random_values = add_jitter(random_data, var)
            active_values = add_jitter(active_data, var)
            
            if len(random_values) > 0 and len(active_values) > 0:
                try:
                    # Plot distributions
                    sns.kdeplot(data=random_values, ax=ax, color='red',
                              label='Random', warn_singular=False)
                    sns.kdeplot(data=active_values, ax=ax, color='green',
                              label='Active Inference', warn_singular=False)
                    
                    # Add statistics
                    ax.axvline(np.mean(random_values), color='red', linestyle='--', alpha=0.5)
                    ax.axvline(np.mean(active_values), color='green', linestyle='--', alpha=0.5)
                    
                    # Add annotations
                    stats_text = (
                        f"Random μ={np.mean(random_values):.2f}, σ={np.std(random_values):.2f}\n"
                        f"Active μ={np.mean(active_values):.2f}, σ={np.std(active_values):.2f}"
                    )
                    ax.text(0.95, 0.95, stats_text, transform=ax.transAxes,
                           verticalalignment='top', horizontalalignment='right',
                           bbox=dict(facecolor='white', alpha=0.8))
                    
                except Exception as e:
                    log(f"Could not plot KDE for {var}, falling back to histogram: {e}")
                    # Fallback to histogram
                    ax.hist(random_values, alpha=0.5, color='red', label='Random',
                           density=True, bins=20)
                    ax.hist(active_values, alpha=0.5, color='green', label='Active',
                           density=True, bins=20)
            
            ax.set_title(f'{var}\nControl Action Distribution')
            ax.set_xlabel('Control Signal')
            ax.set_ylabel('Density')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # Remove empty subplots
        for ax in axes[len(controllable_vars):]:
            fig.delaxes(ax)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'control_actions_analysis.png')
        plt.close()
        
    except Exception as e:
        log(f"Error generating control actions plot: {e}")
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
        
        # Plot 1: Phase Space Trajectories (use controllable variables)
        ax1 = fig.add_subplot(gs[0, 0], projection='3d')
        
        # Get first three controllable variables
        vars_to_plot = [col for col in random_data.columns 
                       if col != 'timestep'][:3]
        
        if len(vars_to_plot) >= 3:
            ax1.plot(random_data[vars_to_plot[0]], 
                    random_data[vars_to_plot[1]],
                    random_data[vars_to_plot[2]],
                    'b-', alpha=0.5, label='Random')
            ax1.plot(active_data[vars_to_plot[0]],
                    active_data[vars_to_plot[1]],
                    active_data[vars_to_plot[2]],
                    'g-', alpha=0.5, label='Active')
            ax1.set_title('Variable Phase Space')
            ax1.set_xlabel(vars_to_plot[0])
            ax1.set_ylabel(vars_to_plot[1])
            ax1.set_zlabel(vars_to_plot[2])
            ax1.legend()
        
        # Plot 2: Stability Metrics
        ax2 = fig.add_subplot(gs[0, 1])
        
        def calculate_stability_metrics(data: pd.DataFrame, 
                                     constraints: pd.DataFrame) -> Dict[str, float]:
            metrics = {}
            for var in data.columns:
                if var != 'timestep':
                    values = data[var].values
                    if len(values) > 0:
                        constraint = constraints[constraints['variable'] == var].iloc[0]
                        target = (constraint['upper_constraint'] + constraint['lower_constraint']) / 2
                        
                        # Calculate metrics
                        metrics[f"{var}_variance"] = np.var(values)
                        metrics[f"{var}_mean_deviation"] = np.mean(np.abs(values - target))
                        metrics[f"{var}_max_deviation"] = np.max(np.abs(values - target))
            
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
        
        def calculate_control_effort(data: pd.DataFrame) -> pd.Series:
            efforts = {}
            for var in data.columns:
                if var != 'timestep':
                    # Calculate rolling mean of absolute changes
                    changes = np.abs(np.diff(data[var].values))
                    efforts[var] = np.mean(changes) if len(changes) > 0 else 0
            return pd.Series(efforts)
        
        random_effort = calculate_control_effort(random_data)
        active_effort = calculate_control_effort(active_data)
        
        effort_df = pd.DataFrame({
            'Random': random_effort,
            'Active': active_effort
        })
        effort_df.plot(kind='bar', ax=ax3)
        ax3.set_title('Average Control Effort')
        ax3.set_ylabel('Mean Absolute Change')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Response Analysis
        ax4 = fig.add_subplot(gs[1, 1])
        
        def calculate_response_metrics(data: pd.DataFrame, 
                                    target: float, 
                                    tolerance: float) -> Dict[str, float]:
            """Calculate response metrics with error handling"""
            metrics = {}
            
            try:
                for var in data.columns:
                    if var != 'timestep':
                        values = data[var].values
                        if len(values) > 0:
                            # Calculate settling time
                            within_tolerance = np.abs(values - target) <= tolerance
                            if np.any(within_tolerance):
                                settling_time = len(values) - np.argmax(within_tolerance[::-1])
                                metrics[f"{var}_settling"] = settling_time
                            
                            # Calculate overshoot
                            if values[-1] != 0:
                                overshoot = ((np.max(values) - values[-1]) / values[-1]) * 100
                                metrics[f"{var}_overshoot"] = overshoot
            except Exception as e:
                print(f"Error in response metrics: {e}")
            
            return metrics
        
        # Calculate response metrics
        response_metrics = {}
        for var in constraints['variable']:
            constraint = constraints[constraints['variable'] == var].iloc[0]
            target = (constraint['upper_constraint'] + constraint['lower_constraint']) / 2
            tolerance = (constraint['upper_constraint'] - constraint['lower_constraint']) * 0.1
            
            random_response = calculate_response_metrics(random_data[[var]], target, tolerance)
            active_response = calculate_response_metrics(active_data[[var]], target, tolerance)
            
            response_metrics.update(random_response)
            response_metrics.update(active_response)
        
        # Plot response metrics
        response_df = pd.DataFrame(response_metrics, index=['Value']).T
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

def plot_decision_comparison(random_data: pd.DataFrame,
                           active_data: pd.DataFrame,
                           controllable_vars: List[str],
                           output_dir: Path):
    """Plot side-by-side comparison of decisions/actions taken by each control strategy"""
    try:
        # Create figure with 2x2 subplots with more space
        fig = plt.figure(figsize=(20, 16))
        gs = plt.GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)
        
        # 1. Overall Decision Distribution (top left) - keep as is
        ax1 = fig.add_subplot(gs[0, 0])
        # ... existing distribution code ...

        # 2. Decision Timing Analysis (top right) - NEW
        ax2 = fig.add_subplot(gs[0, 1])
        def plot_decision_timing(data, label, color):
            changes = []
            for var in controllable_vars:
                var_data = data[var].values
                # Calculate time between value changes
                change_points = np.where(np.abs(np.diff(var_data)) > 0.1)[0]
                if len(change_points) > 1:
                    changes.extend(np.diff(change_points))
            
            if changes:
                sns.histplot(changes, ax=ax2, label=label, color=color, alpha=0.5)
                
        plot_decision_timing(random_data, "Random", "gray")
        plot_decision_timing(active_data, "Active Inference", "royalblue")
        ax2.set_title("Time Between Decisions")
        ax2.set_xlabel("Timesteps")
        ax2.set_ylabel("Frequency")
        ax2.legend()
        
        # 3. Control Effectiveness (bottom left) - NEW
        ax3 = fig.add_subplot(gs[1, 0])
        
        def calculate_control_effectiveness(data, constraints):
            effectiveness = []
            for var in controllable_vars:
                values = data[var].values
                constraint = constraints[constraints['variable'] == var].iloc[0]
                target = (constraint['upper_constraint'] + constraint['lower_constraint']) / 2
                
                # Calculate moving average of distance to target
                window = 50
                distances = np.abs(values - target)
                moving_avg = pd.Series(distances).rolling(window).mean()
                
                # Convert to effectiveness score (inverse of distance)
                max_distance = max(target - constraint['lower_constraint'],
                                 constraint['upper_constraint'] - target)
                effectiveness.append(1 - (moving_avg / max_distance))
                
            return np.mean(effectiveness, axis=0)
            
        random_effect = calculate_control_effectiveness(random_data, constraints)
        active_effect = calculate_control_effectiveness(active_data, constraints)
        
        timesteps = range(len(random_effect))
        ax3.plot(timesteps, random_effect, label="Random", color="gray", alpha=0.7)
        ax3.plot(timesteps, active_effect, label="Active Inference", color="royalblue", alpha=0.7)
        ax3.set_title("Control Effectiveness Over Time")
        ax3.set_xlabel("Timestep")
        ax3.set_ylabel("Effectiveness Score")
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Decision Impact Analysis (bottom right) - keep as is
        ax4 = fig.add_subplot(gs[1, 1])
        # ... existing effectiveness distribution code ...
        
        plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.9)
        plt.savefig(output_dir / 'decision_analysis.png',
                   bbox_inches='tight', dpi=300)
        plt.close()
        
    except Exception as e:
        print(f"Error in plot_decision_analysis: {e}")
        plt.close('all')

def generate_all_visualizations(random_data: pd.DataFrame,
                              active_data: pd.DataFrame,
                              constraints: pd.DataFrame,
                              controllable_vars: List[str],
                              output_dir: Path,
                              logger: logging.Logger) -> bool:
    """Generate all visualization plots"""
    # Create visualizations directory
    vis_dir = output_dir / 'visualizations'
    vis_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info("Generating individual strategy plots...")
        # Create single faceted plot comparing both strategies
        plot_combined_strategies(
            random_data=random_data,
            active_data=active_data,
            constraints=constraints,
            controllable_vars=controllable_vars,
            output_dir=vis_dir
        )
        logger.info("✓ Individual Strategy Plots saved")
        
        logger.info("Generating strategy comparison...")
        plot_comparison(
            random_data=random_data,
            active_data=active_data,
            constraints=constraints,
            controllable_vars=controllable_vars,
            output_dir=vis_dir
        )
        logger.info("✓ Strategy Comparison saved")
        
        logger.info("Generating satisfaction rates...")
        plot_satisfaction_rates(
            random_data=random_data,
            active_data=active_data,
            constraints=constraints,
            output_dir=vis_dir
        )
        logger.info("✓ Satisfaction Rates saved")
        
        logger.info("Generating correlation heatmaps...")
        plot_correlation_heatmaps(
            random_data=random_data,
            active_data=active_data,
            output_dir=vis_dir
        )
        logger.info("✓ Correlation Heatmaps saved")
        
        logger.info("Generating state distributions...")
        plot_state_distributions(
            random_data=random_data,
            active_data=active_data,
            constraints=constraints,
            output_dir=vis_dir
        )
        logger.info("✓ State Distributions saved")
        
        logger.info("Generating variable distributions...")
        plot_variable_distributions(
            random_data=random_data,
            active_data=active_data,
            constraints=constraints,
            output_dir=vis_dir
        )
        logger.info("✓ Variable Distributions saved")
        
        logger.info("Generating control actions...")
        plot_control_actions(
            random_data=random_data,
            active_data=active_data,
            controllable_vars=controllable_vars,
            output_dir=vis_dir,
            logger=logger
        )
        logger.info("✓ Control Actions saved")
        
        logger.info("Generating state transitions...")
        plot_state_transitions(
            random_data=random_data,
            active_data=active_data,
            constraints=constraints,
            output_dir=vis_dir
        )
        logger.info("✓ State Transitions saved")
        
        logger.info("Generating system stability...")
        plot_system_stability_analysis(
            random_data=random_data,
            active_data=active_data,
            constraints=constraints,
            output_dir=vis_dir
        )
        logger.info("✓ System Stability saved")
        
        logger.info("Generating decision comparison...")
        plot_decision_comparison(
            random_data=random_data,
            active_data=active_data,
            controllable_vars=controllable_vars,
            output_dir=vis_dir
        )
        logger.info("✓ Decision Comparison saved")
        
        # Log generated files
        generated_files = list(vis_dir.glob('*.png'))
        if generated_files:
            logger.info("\nGenerated visualization files:")
            for file in sorted(f.name for f in generated_files):
                logger.info(f"  - {file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in visualization generation: {str(e)}")
        logger.debug("Full traceback:", exc_info=True)
        plt.close('all')
        return False

def plot_combined_strategies(random_data: pd.DataFrame,
                           active_data: pd.DataFrame,
                           constraints: pd.DataFrame,
                           controllable_vars: List[str],
                           output_dir: Path):
    """Create single faceted plot comparing both control strategies"""
    plt.ioff()
    
    try:
        # Get variables excluding timestep
        variables = [col for col in random_data.columns if col != 'timestep']
        n_vars = len(variables)
        n_cols = 2  # Two columns: random and active inference
        n_rows = n_vars
        
        # Create figure
        fig = plt.figure(figsize=(20, 4*n_rows))
        gs = plt.GridSpec(n_rows, n_cols)
        
        # Plot each variable
        for var_idx, var_name in enumerate(variables):  # Changed from random_data.columns
            # Plot random control
            ax_random = fig.add_subplot(gs[var_idx, 0])
            plot_variable(ax_random, random_data, var_name, constraints, 
                         controllable_vars, 'Random Control', 'gray')
            
            # Plot active inference
            ax_active = fig.add_subplot(gs[var_idx, 1])
            plot_variable(ax_active, active_data, var_name, constraints,
                         controllable_vars, 'Active Inference', 'royalblue')
            
            # Add variable name to the left
            if var_idx == 0:
                ax_random.set_title('Random Control', fontsize=12, pad=10)
                ax_active.set_title('Active Inference', fontsize=12, pad=10)
        
        plt.suptitle('Control Strategy Comparison', fontsize=14, y=1.02)
        plt.tight_layout()
        
        # Save plot
        plt.savefig(output_dir / 'strategy_comparison.png',
                   bbox_inches='tight', dpi=300)
        plt.close()
        
    except Exception as e:
        print(f"Error in plot_combined_strategies: {str(e)}")
        plt.close('all')

def plot_variable(ax: plt.Axes, 
                 data: pd.DataFrame,
                 var_name: str,
                 constraints: pd.DataFrame,
                 controllable_vars: List[str],
                 title: str,
                 color: str):
    """Plot single variable for a control strategy"""
    
    # Determine if variable is controlled
    is_controlled = var_name in controllable_vars
    
    # Plot variable
    ax.plot(data['timestep'], data[var_name],
            color=color,
            linewidth=2.5 if is_controlled else 1.5,
            alpha=0.9 if is_controlled else 0.7,
            label=var_name)
    
    # Add constraints
    if var_name in constraints['variable'].values:
        constraint = constraints[constraints['variable'] == var_name].iloc[0]
        
        # Target range
        ax.axhspan(constraint['lower_constraint'],
                  constraint['upper_constraint'],
                  color='green', alpha=0.1)
        
        # Constraint lines
        ax.axhline(y=constraint['lower_constraint'], color='red',
                  linestyle='--', alpha=0.5)
        ax.axhline(y=constraint['upper_constraint'], color='red',
                  linestyle='--', alpha=0.5)
    
    # Calculate statistics
    mean_val = data[var_name].mean()
    std_val = data[var_name].std()
    in_bounds = 0
    if var_name in constraints['variable'].values:
        constraint = constraints[constraints['variable'] == var_name].iloc[0]
        in_bounds = ((data[var_name] >= constraint['lower_constraint']) & 
                    (data[var_name] <= constraint['upper_constraint'])).mean() * 100
    
    # Add statistics text
    stats_text = f'{var_name}\nMean: {mean_val:.1f}\nStd: {std_val:.1f}\nIn Target: {in_bounds:.1f}%'
    ax.text(0.02, 0.98, stats_text,
            transform=ax.transAxes,
            verticalalignment='top',
            bbox=dict(facecolor='white', alpha=0.8))
    
    # Customize plot
    ax.grid(True, alpha=0.3)
    ax.set_ylabel(get_unit(var_name))
    if is_controlled:
        ax.set_facecolor('#f0f9ff')  # Light blue background for controlled variables

def plot_belief_dynamics(beliefs: np.ndarray, 
                        variable_name: str,
                        output_dir: Path,
                        logger: Optional[logging.Logger] = None) -> None:
    """Plot belief dynamics over time with improved error handling"""
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Ensure beliefs is 2D array [timesteps, belief_states]
        if len(beliefs.shape) == 1:
            beliefs = beliefs.reshape(-1, 1)
            
        # Create heatmap of belief evolution
        im = ax.imshow(beliefs.T, aspect='auto', cmap='viridis')
        plt.colorbar(im, ax=ax, label='Belief Probability')
        
        ax.set_title(f'Belief Dynamics for {variable_name}')
        ax.set_xlabel('Time Step')
        ax.set_ylabel('Belief State')
        
        # Save plot
        output_path = output_dir / f'belief_dynamics_{variable_name}.png'
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        plt.close()
        
        if logger:
            logger.info(f"Belief dynamics plot saved to {output_path}")
            
    except Exception as e:
        if logger:
            logger.error(f"Error generating belief dynamics plot: {str(e)}")
        plt.close()

def plot_decision_analysis(decisions: np.ndarray,
                          variable_name: str, 
                          output_dir: Path,
                          logger: Optional[logging.Logger] = None) -> None:
    """Plot decision analysis with improved visualization and metrics
    
    Args:
        decisions: Array of decisions/actions taken
        variable_name: Name of the variable being controlled
        output_dir: Directory to save visualization
        logger: Optional logger instance
    """
    try:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Decision Analysis for {variable_name}', fontsize=14)
        
        # 1. Decision Distribution (Top Left)
        ax = axes[0, 0]
        unique_decisions, counts = np.unique(decisions, return_counts=True)
        percentages = counts / len(decisions) * 100
        
        bars = ax.bar(['Decrease', 'Maintain', 'Increase'], percentages)
        ax.set_title('Action Distribution')
        ax.set_ylabel('Percentage of Time (%)')
        
        # Add percentage labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom')
        
        ax.grid(True, alpha=0.3)
        
        # 2. Decision Transitions (Top Right)
        ax = axes[0, 1]
        transitions = np.zeros((3, 3))
        for i in range(len(decisions)-1):
            transitions[int(decisions[i]), int(decisions[i+1])] += 1
            
        # Normalize transitions
        row_sums = transitions.sum(axis=1, keepdims=True)
        transitions = np.divide(transitions, row_sums, 
                              where=row_sums!=0,
                              out=np.zeros_like(transitions))
        
        sns.heatmap(transitions, ax=ax, annot=True, fmt='.2f', cmap='YlOrRd',
                   xticklabels=['Decrease', 'Maintain', 'Increase'],
                   yticklabels=['Decrease', 'Maintain', 'Increase'])
        ax.set_title('Action Transition Probabilities')
        ax.set_xlabel('Next Action')
        ax.set_ylabel('Current Action')
        
        # 3. Decision Consistency Analysis (Bottom Left)
        ax = axes[1, 0]
        
        # Calculate run lengths of same decision
        run_lengths = []
        current_run = 1
        
        for i in range(1, len(decisions)):
            if decisions[i] == decisions[i-1]:
                current_run += 1
            else:
                run_lengths.append(current_run)
                current_run = 1
        run_lengths.append(current_run)
        
        # Plot run length distribution
        ax.hist(run_lengths, bins=20, alpha=0.7, color='blue',
                edgecolor='black')
        ax.set_title('Decision Consistency')
        ax.set_xlabel('Consecutive Steps Same Action')
        ax.set_ylabel('Frequency')
        
        # Add statistics
        mean_run = np.mean(run_lengths)
        max_run = np.max(run_lengths)
        stats_text = f'Mean Run: {mean_run:.1f}\nMax Run: {max_run:.0f}'
        ax.text(0.95, 0.95, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(facecolor='white', alpha=0.8))
        
        ax.grid(True, alpha=0.3)
        
        # 4. Decision Timing Analysis (Bottom Right)
        ax = axes[1, 1]
        
        # Calculate time between decision changes
        change_points = np.where(np.diff(decisions) != 0)[0]
        intervals = np.diff(change_points)
        
        if len(intervals) > 0:
            # Plot interval distribution
            ax.hist(intervals, bins=20, alpha=0.7, color='green',
                   edgecolor='black')
            ax.set_title('Time Between Decision Changes')
            ax.set_xlabel('Time Steps')
            ax.set_ylabel('Frequency')
            
            # Add statistics
            mean_interval = np.mean(intervals)
            median_interval = np.median(intervals)
            stats_text = (f'Mean Interval: {mean_interval:.1f}\n'
                         f'Median Interval: {median_interval:.1f}')
            ax.text(0.95, 0.95, stats_text,
                   transform=ax.transAxes,
                   verticalalignment='top',
                   horizontalalignment='right',
                   bbox=dict(facecolor='white', alpha=0.8))
        else:
            ax.text(0.5, 0.5, 'No decision changes',
                   ha='center', va='center')
        
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        output_path = output_dir / f'decision_analysis_{variable_name}.png'
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        plt.close()
        
        if logger:
            logger.info(f"Decision analysis plot saved to {output_path}")
            
    except Exception as e:
        if logger:
            logger.error(f"Error generating decision analysis plot: {str(e)}")
        plt.close()

def plot_action_selection(actions: np.ndarray,
                         beliefs: np.ndarray,
                         variable_name: str,
                         output_dir: Path,
                         logger: Optional[logging.Logger] = None) -> None:
    """Plot action selection analysis with improved error handling"""
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Ensure arrays are properly shaped
        actions = np.asarray(actions).flatten()
        if len(beliefs.shape) == 1:
            beliefs = beliefs.reshape(-1, 1)
        
        # Plot action-belief relationship
        belief_max = np.argmax(beliefs, axis=1)
        for action in np.unique(actions):
            mask = actions == action
            if np.any(mask):
                ax1.scatter(belief_max[mask], actions[mask], 
                          alpha=0.5, label=f'Action {action}')
        
        ax1.set_title('Action vs Belief State')
        ax1.set_xlabel('Most Likely Belief State')
        ax1.set_ylabel('Selected Action')
        
        # Plot action frequency over time
        ax2.plot(actions, alpha=0.7)
        ax2.set_title('Action Selection Over Time')
        ax2.set_xlabel('Time Step')
        ax2.set_ylabel('Selected Action')
        
        plt.suptitle(f'Action Selection Analysis for {variable_name}')
        
        # Save plot
        output_path = output_dir / f'action_selection_{variable_name}.png'
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        plt.close()
        
        if logger:
            logger.info(f"Action selection plot saved to {output_path}")
            
    except Exception as e:
        if logger:
            logger.error(f"Error generating action selection plot: {str(e)}")
        plt.close()

def plot_belief_evolution(beliefs: np.ndarray,
                         variable_name: str,
                         output_dir: Path,
                         logger: Optional[logging.Logger] = None) -> None:
    """Plot belief evolution over time with improved error handling"""
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Ensure beliefs is 2D array
        if len(beliefs.shape) == 1:
            beliefs = beliefs.reshape(-1, 1)
        
        # Plot belief probabilities over time
        for i in range(beliefs.shape[1]):
            ax1.plot(beliefs[:, i], label=f'State {i}', alpha=0.7)
        
        ax1.set_title('Belief Evolution')
        ax1.set_xlabel('Time Step')
        ax1.set_ylabel('Belief Probability')
        ax1.legend()
        
        # Plot entropy of belief distribution
        entropy = -np.sum(beliefs * np.log2(beliefs + 1e-10), axis=1)
        ax2.plot(entropy, color='red', alpha=0.7)
        ax2.set_title('Belief Entropy')
        ax2.set_xlabel('Time Step')
        ax2.set_ylabel('Entropy (bits)')
        
        plt.suptitle(f'Belief Evolution Analysis for {variable_name}')
        
        # Save plot
        output_path = output_dir / f'belief_evolution_{variable_name}.png'
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        plt.close()
        
        if logger:
            logger.info(f"Belief evolution plot saved to {output_path}")
            
    except Exception as e:
        if logger:
            logger.error(f"Error generating belief evolution plot: {str(e)}")
        plt.close()

def plot_belief_convergence(beliefs: np.ndarray,
                           variable_name: str,
                           output_dir: Path,
                           logger: Optional[logging.Logger] = None) -> None:
    """Plot belief convergence analysis with improved error handling"""
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Ensure beliefs is 2D array
        if len(beliefs.shape) == 1:
            beliefs = beliefs.reshape(-1, 1)
        
        # Calculate belief changes
        belief_changes = np.abs(np.diff(beliefs, axis=0))
        mean_changes = np.mean(belief_changes, axis=1)
        
        # Plot average belief changes
        ax1.plot(mean_changes, alpha=0.7)
        ax1.set_title('Belief Stability')
        ax1.set_xlabel('Time Step')
        ax1.set_ylabel('Average Belief Change')
        
        # Plot final belief distribution
        final_beliefs = beliefs[-1]
        ax2.bar(range(len(final_beliefs)), final_beliefs, alpha=0.7)
        ax2.set_title('Final Belief Distribution')
        ax2.set_xlabel('Belief State')
        ax2.set_ylabel('Probability')
        
        plt.suptitle(f'Belief Convergence Analysis for {variable_name}')
        
        # Save plot
        output_path = output_dir / f'belief_convergence_{variable_name}.png'
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        plt.close()
        
        if logger:
            logger.info(f"Belief convergence plot saved to {output_path}")
            
    except Exception as e:
        if logger:
            logger.error(f"Error generating belief convergence plot: {str(e)}")
        plt.close()
