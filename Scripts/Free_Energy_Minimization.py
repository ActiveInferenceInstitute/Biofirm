"""Analysis and visualization of active inference performance"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Optional, Union, Tuple, List, Any
from pathlib import Path
import pandas as pd
import logging
import json
from datetime import datetime

def setup_logging(output_dir: Path) -> logging.Logger:
    """Setup logging for free energy analysis"""
    logger = logging.getLogger('free_energy_analysis')
    logger.setLevel(logging.INFO)
    
    # Create handlers
    log_dir = output_dir / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(
        log_dir / f'free_energy_analysis_{datetime.now():%Y%m%d_%H%M%S}.log'
    )
    console_handler = logging.StreamHandler()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_formatter = logging.Formatter('%(message)s')
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def analyze_active_inference_agents(agent: Any, output_dir: Path,
                                  logger: Optional[logging.Logger] = None) -> Dict:
    """Analyze active inference agent performance across all modalities
    
    Args:
        agent: BiofirmAgent instance containing all modality agents
        output_dir: Directory for saving analysis outputs
        logger: Optional logger instance
    
    Returns:
        Dictionary containing analysis results
    """
    logger = logger or setup_logging(output_dir)
    logger.info("\n=== Active Inference Performance Analysis ===\n")
    
    # Create analysis directory
    analysis_dir = output_dir / 'active_inference_analysis'
    analysis_dir.mkdir(exist_ok=True)
    
    # Get data for all modalities
    modality_stats = {}
    for var_name in agent.controllable_vars:
        try:
            # Get agent data including history and matrices
            data = agent.get_agent_data(var_name)
            if not data:
                logger.warning(f"No data available for {var_name}")
                continue
                
            # Analyze modality
            stats = analyze_modality_agent(data, var_name, analysis_dir, logger)
            modality_stats[var_name] = stats
            
        except Exception as e:
            logger.error(f"Failed to analyze {var_name}: {str(e)}")
    
    # Generate comprehensive report
    try:
        generate_comprehensive_report(modality_stats, analysis_dir, logger)
    except Exception as e:
        logger.error(f"Failed to generate comprehensive report: {str(e)}")
    
    return modality_stats

def analyze_modality_agent(data: Dict, var_name: str, output_dir: Path,
                         logger: logging.Logger) -> Dict:
    """Analyze single modality agent performance"""
    logger.info(f"\nAnalyzing {var_name} agent...")
    
    # Create modality directory
    mod_dir = output_dir / var_name
    mod_dir.mkdir(exist_ok=True)
    
    try:
        # Calculate performance metrics
        metrics = calculate_performance_metrics(data, var_name)
        
        # Generate visualizations
        generate_modality_visualizations(data, var_name, mod_dir, logger)
        
        # Save metrics
        with open(mod_dir / 'metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error analyzing {var_name}: {str(e)}")
        return {}

def calculate_performance_metrics(data: Dict, var_name: str) -> Dict:
    """Calculate performance metrics for a modality"""
    metrics = {
        'variable': var_name,
        'timesteps': len(data['selected_actions']),
        'metrics': {}
    }
    
    try:
        # Belief metrics
        beliefs = np.array(data['state_beliefs'])
        metrics['metrics']['belief_entropy_mean'] = float(
            -np.mean(np.sum(beliefs * np.log(beliefs + 1e-10), axis=1))
        )
        metrics['metrics']['belief_stability'] = float(
            1 - np.mean(np.abs(np.diff(beliefs, axis=0)))
        )
        
        # Action metrics
        actions = np.array(data['selected_actions'])
        action_counts = np.bincount(actions, minlength=3)
        metrics['metrics']['action_distribution'] = {
            'decrease': float(action_counts[0] / len(actions)),
            'maintain': float(action_counts[1] / len(actions)),
            'increase': float(action_counts[2] / len(actions))
        }
        
        # State achievement
        if 'state_values' in data:
            state_values = np.array(data['state_values'])
            metrics['metrics']['homeostasis_rate'] = float(
                np.mean((state_values >= 40) & (state_values <= 60))
            )
        
        # Control effort
        if 'control_signals' in data:
            control_signals = np.array(data['control_signals'])
            metrics['metrics']['control_effort'] = float(
                np.mean(np.abs(control_signals))
            )
        
        return metrics
        
    except Exception as e:
        raise ValueError(f"Error calculating metrics: {str(e)}")

def generate_modality_visualizations(data: Dict, var_name: str, 
                                   output_dir: Path, logger: logging.Logger,
                                   constraints: Optional[Dict[str, Tuple[float, float]]] = None):
    """Generate visualizations for a modality"""
    try:
        # Create visualization directory
        viz_dir = output_dir / 'visualizations'
        viz_dir.mkdir(exist_ok=True)
        
        # Generate each visualization type
        visualizations = [
            ('belief_dynamics', plot_belief_dynamics),
            ('action_selection', plot_action_selection),
            ('state_control', plot_state_control),
            ('free_energy', plot_free_energy),
            ('decision_analysis', lambda d, v, o: plot_decision_analysis(d, v, o, constraints))
        ]
        
        for name, plot_func in visualizations:
            try:
                if name == 'decision_analysis' and constraints is None:
                    logger.warning("Skipping decision analysis: no constraints provided")
                    continue
                    
                plot_func(data, var_name, viz_dir)
                logger.info(f"  ✓ Generated {name} plot")
            except Exception as e:
                logger.error(f"  ✗ Failed to generate {name} plot: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error generating visualizations: {str(e)}")

def plot_belief_dynamics(data: Dict, var_name: str, output_dir: Path):
    """Plot belief dynamics visualization"""
    try:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Belief Dynamics - {var_name}', fontsize=14)
        
        # Get beliefs and actions
        beliefs = np.array(data['state_beliefs'])
        actions = np.array(data['selected_actions'])
        
        # 1. Belief trajectories
        ax = axes[0, 0]
        for i, state in enumerate(['LOW', 'HOMEO', 'HIGH']):
            ax.plot(beliefs[:, i], label=state)
        ax.set_title('Belief Evolution')
        ax.set_xlabel('Time Step')
        ax.set_ylabel('Belief Probability')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. Belief entropy
        ax = axes[0, 1]
        entropy = -np.sum(beliefs * np.log(beliefs + 1e-10), axis=1)
        ax.plot(entropy, color='purple')
        ax.set_title('Belief Uncertainty')
        ax.set_xlabel('Time Step')
        ax.set_ylabel('Entropy (nats)')
        ax.grid(True, alpha=0.3)
        
        # 3. State-Action mapping
        ax = axes[1, 0]
        state_estimates = np.argmax(beliefs, axis=1)
        state_action_map = np.zeros((3, 3))
        valid_indices = ~np.isnan(state_estimates) & ~np.isnan(actions)
        for state, action in zip(state_estimates[valid_indices], actions[valid_indices]):
            state_action_map[int(state), int(action)] += 1
            
        # Normalize if any non-zero values exist
        row_sums = state_action_map.sum(axis=1, keepdims=True)
        state_action_map = np.divide(state_action_map, row_sums, 
                                   out=np.zeros_like(state_action_map),
                                   where=row_sums != 0)
        
        sns.heatmap(state_action_map, ax=ax, annot=True, fmt='.2f',
                    xticklabels=['DECREASE', 'MAINTAIN', 'INCREASE'],
                    yticklabels=['LOW', 'HOMEO', 'HIGH'])
        ax.set_title('State-Action Mapping')
        
        # 4. Belief changes
        ax = axes[1, 1]
        belief_changes = np.abs(np.diff(beliefs, axis=0))
        for i, state in enumerate(['LOW', 'HOMEO', 'HIGH']):
            ax.plot(belief_changes[:, i], alpha=0.5, label=state)
        ax.set_title('Belief Stability')
        ax.set_xlabel('Time Step')
        ax.set_ylabel('Absolute Belief Change')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'belief_dynamics.png')
        plt.close()
        
        return True
        
    except Exception as e:
        plt.close()
        raise ValueError(f"Error plotting belief dynamics: {str(e)}")

def plot_action_selection(data: Dict, var_name: str, output_dir: Path):
    """Plot action selection visualization"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'Action Selection Analysis - {var_name}', fontsize=14)
    
    # 1. Action distribution over time
    ax = axes[0, 0]
    actions = np.array(data['selected_actions'])
    for i, action in enumerate(['DECREASE', 'MAINTAIN', 'INCREASE']):
        mask = actions == i
        ax.scatter(np.where(mask)[0], [i] * mask.sum(), 
                  alpha=0.6, label=action)
    ax.set_title('Action Selection Over Time')
    ax.set_xlabel('Time Step')
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(['DECREASE', 'MAINTAIN', 'INCREASE'])
    ax.grid(True, alpha=0.3)
    
    # 2. Policy preferences evolution
    ax = axes[0, 1]
    policy_prefs = np.array(data['policy_preferences'])
    for i, action in enumerate(['DECREASE', 'MAINTAIN', 'INCREASE']):
        ax.plot(policy_prefs[:, i], label=action)
    ax.set_title('Policy Preferences Evolution')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Preference Probability')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Control signals
    ax = axes[1, 0]
    controls = np.array(data['control_signals'])
    ax.plot(controls, color='blue')
    ax.set_title('Control Signals')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Control Signal')
    ax.grid(True, alpha=0.3)
    
    # 4. Free energy
    ax = axes[1, 1]
    free_energy = np.array(data['expected_free_energy'])
    ax.plot(free_energy, color='red')
    ax.set_title('Expected Free Energy')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('EFE')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'action_selection.png')
    plt.close()

def plot_state_control(data: Dict, var_name: str, output_dir: Path):
    """Plot state control visualization"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'State Control Analysis - {var_name}', fontsize=14)
    
    # Get data
    states = np.array(data['state_values'])
    controls = np.array(data['control_signals'])
    actions = np.array(data['selected_actions'])
    
    # 1. State trajectory with bounds
    ax = axes[0, 0]
    ax.plot(states, color='blue', label='State')
    ax.axhline(y=40, color='r', linestyle='--', alpha=0.5, label='Bounds')
    ax.axhline(y=60, color='r', linestyle='--', alpha=0.5)
    ax.fill_between(range(len(states)), 40, 60, color='g', alpha=0.1)
    ax.set_title('State Trajectory')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('State Value')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. State-Control relationship
    ax = axes[0, 1]
    for i, action in enumerate(['DECREASE', 'MAINTAIN', 'INCREASE']):
        mask = actions == i
        ax.scatter(states[mask], controls[mask], alpha=0.6, label=action)
    ax.set_title('State-Control Relationship')
    ax.set_xlabel('State Value')
    ax.set_ylabel('Control Signal')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Control distribution
    ax = axes[1, 0]
    ax.hist(controls, bins=20, color='blue', alpha=0.6)
    ax.set_title('Control Distribution')
    ax.set_xlabel('Control Signal')
    ax.set_ylabel('Frequency')
    ax.grid(True, alpha=0.3)
    
    # 4. State stability
    ax = axes[1, 1]
    state_changes = np.abs(np.diff(states))
    ax.plot(state_changes, color='purple')
    ax.set_title('State Stability')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Absolute State Change')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'state_control.png')
    plt.close()

def plot_free_energy(data: Dict, var_name: str, output_dir: Path):
    """Plot free energy visualization"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'Free Energy Analysis - {var_name}', fontsize=14)
    
    # Get data
    free_energy = np.array(data['expected_free_energy'])
    policy_prefs = np.array(data['policy_preferences'])
    
    # 1. Free energy over time
    ax = axes[0, 0]
    ax.plot(free_energy, color='red')
    ax.set_title('Expected Free Energy Evolution')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('EFE')
    ax.grid(True, alpha=0.3)
    
    # 2. Free energy distribution
    ax = axes[0, 1]
    ax.hist(free_energy, bins=20, color='red', alpha=0.6)
    ax.set_title('Free Energy Distribution')
    ax.set_xlabel('EFE')
    ax.set_ylabel('Frequency')
    ax.grid(True, alpha=0.3)
    
    # 3. Policy entropy
    ax = axes[1, 0]
    policy_entropy = -np.sum(policy_prefs * np.log(policy_prefs + 1e-10), axis=1)
    ax.plot(policy_entropy, color='purple')
    ax.set_title('Policy Entropy')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Entropy (nats)')
    ax.grid(True, alpha=0.3)
    
    # 4. Free energy vs policy entropy
    ax = axes[1, 1]
    ax.scatter(free_energy, policy_entropy, alpha=0.6, color='blue')
    ax.set_title('Free Energy vs Policy Entropy')
    ax.set_xlabel('Expected Free Energy')
    ax.set_ylabel('Policy Entropy')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'free_energy.png')
    plt.close()

def generate_comprehensive_report(modality_stats: Dict, output_dir: Path,
                                logger: logging.Logger):
    """Generate comprehensive analysis report"""
    report_file = output_dir / 'active_inference_report.txt'
    
    try:
        with open(report_file, 'w') as f:
            f.write("=== Active Inference Analysis Report ===\n\n")
            
            # Overall statistics
            f.write("Overall Performance:\n")
            f.write("-" * 50 + "\n")
            
            total_homeostasis = 0
            total_control_effort = 0
            num_modalities = len(modality_stats)
            
            if num_modalities == 0:
                raise ValueError("No modality statistics available")
            
            for var_name, stats in modality_stats.items():
                metrics = stats.get('metrics', {})
                homeostasis = metrics.get('homeostasis_rate', 0)
                control_effort = metrics.get('control_effort', 0)
                
                total_homeostasis += homeostasis
                total_control_effort += control_effort
                
                f.write(f"\n{var_name}:\n")
                f.write(f"  • Homeostasis Rate: {homeostasis:.1%}\n")
                f.write(f"  • Control Effort: {control_effort:.2f}\n")
                f.write(f"  • Belief Stability: {metrics.get('belief_stability', 0):.2f}\n")
                
            # Summary statistics
            f.write("\nSummary Statistics:\n")
            f.write("-" * 50 + "\n")
            f.write(f"Average Homeostasis Rate: {total_homeostasis/num_modalities:.1%}\n")
            f.write(f"Average Control Effort: {total_control_effort/num_modalities:.2f}\n")
            
        logger.info(f"\nComprehensive report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Failed to generate comprehensive report: {str(e)}")

def plot_decision_analysis(data: Dict, var_name: str, output_dir: Path, constraints: Dict[str, Tuple[float, float]]):
    """Plot decision analysis visualization
    
    Args:
        data: Dictionary containing agent data
        var_name: Name of the variable being analyzed
        output_dir: Directory to save visualization
        constraints: Dictionary mapping variable names to (lower, upper) constraint bounds
    """
    try:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Decision Analysis - {var_name}', fontsize=14)
        
        # Get data
        states = np.array(data['state_values'])
        actions = np.array(data['selected_actions'])
        policy_prefs = np.array(data['policy_preferences'])
        
        # Get constraints for this variable
        lower_bound, upper_bound = constraints.get(var_name, (40, 60))
        
        # 1. State-conditioned action probabilities
        ax = axes[0, 0]
        state_bins = np.linspace(0, 100, 21)  # 20 bins
        state_centers = (state_bins[:-1] + state_bins[1:]) / 2
        
        action_probs = np.zeros((3, len(state_centers)))  # 3 actions
        for i, (low, high) in enumerate(zip(state_bins[:-1], state_bins[1:])):
            mask = (states >= low) & (states < high)
            if np.any(mask):
                action_counts = np.bincount(actions[mask], minlength=3)
                action_probs[:, i] = action_counts / len(actions[mask])
        
        for i, action in enumerate(['DECREASE', 'MAINTAIN', 'INCREASE']):
            ax.plot(state_centers, action_probs[i], label=action)
            
        # Add constraint bounds
        ax.axvline(x=lower_bound, color='r', linestyle='--', alpha=0.5)
        ax.axvline(x=upper_bound, color='r', linestyle='--', alpha=0.5)
        ax.fill_between([lower_bound, upper_bound], 0, 1, color='g', alpha=0.1)
        
        ax.set_title('State-Conditioned Action Probabilities')
        ax.set_xlabel('State Value')
        ax.set_ylabel('Action Probability')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. Decision confidence
        ax = axes[0, 1]
        policy_entropy = -np.sum(policy_prefs * np.log(policy_prefs + 1e-10), axis=1)
        confidence = 1 - policy_entropy / np.log(3)  # Normalize by max entropy
        
        # Color points by whether state is in bounds
        in_bounds = (states >= lower_bound) & (states <= upper_bound)
        ax.scatter(states[in_bounds], confidence[in_bounds], 
                  color='green', alpha=0.6, label='In Bounds')
        ax.scatter(states[~in_bounds], confidence[~in_bounds], 
                  color='red', alpha=0.6, label='Out of Bounds')
        
        ax.set_title('Decision Confidence vs State')
        ax.set_xlabel('State Value')
        ax.set_ylabel('Decision Confidence')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 3. Action transitions
        ax = axes[1, 0]
        transition_matrix = np.zeros((3, 3))
        for prev, curr in zip(actions[:-1], actions[1:]):
            transition_matrix[prev, curr] += 1
            
        # Normalize rows
        row_sums = transition_matrix.sum(axis=1, keepdims=True)
        transition_matrix = np.divide(transition_matrix, row_sums,
                                    out=np.zeros_like(transition_matrix),
                                    where=row_sums != 0)
        
        sns.heatmap(transition_matrix, ax=ax, annot=True, fmt='.2f',
                   xticklabels=['DECREASE', 'MAINTAIN', 'INCREASE'],
                   yticklabels=['DECREASE', 'MAINTAIN', 'INCREASE'])
        ax.set_title('Action Transition Probabilities')
        ax.set_xlabel('Next Action')
        ax.set_ylabel('Current Action')
        
        # 4. Decision timing
        ax = axes[1, 1]
        decision_times = []
        current_time = 0
        current_action = actions[0]
        
        for action in actions[1:]:
            current_time += 1
            if action != current_action:
                decision_times.append(current_time)
                current_time = 0
                current_action = action
        
        if decision_times:
            ax.hist(decision_times, bins=20, color='purple', alpha=0.6)
            ax.set_title('Time Between Action Changes')
            ax.set_xlabel('Time Steps')
            ax.set_ylabel('Frequency')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No Action Changes', 
                   ha='center', va='center', transform=ax.transAxes)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'decision_analysis.png')
        plt.close()
        
        return True
        
    except Exception as e:
        plt.close()
        raise ValueError(f"Error in plot_decision_analysis: {str(e)}")
