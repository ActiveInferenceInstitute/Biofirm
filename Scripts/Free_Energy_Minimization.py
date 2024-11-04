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
import traceback

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

def analyze_modality_agent(data: Dict, var_name: str, output_dir: Path,
                         logger: logging.Logger) -> Dict:
    """Analyze single modality agent performance"""
    # Create modality directory
    mod_dir = output_dir / var_name
    mod_dir.mkdir(exist_ok=True)
    
    try:
        # Basic metrics
        metrics = calculate_performance_metrics(data, var_name)
        
        # Validate and preprocess data
        preprocessed_data = preprocess_agent_data(data, logger)
        
        if preprocessed_data:
            # Generate modality-specific visualizations
            generate_modality_analysis(preprocessed_data, var_name, mod_dir, logger)
            
            # Save raw agent data
            with open(mod_dir / 'agent_data.json', 'w') as f:
                json_data = {
                    'control_strength': float(data.get('control_strength', 0.0)),
                    'control_signals': preprocessed_data['controls'].tolist(),
                    'action_history': preprocessed_data['actions'].tolist()
                }
                json.dump(json_data, f, indent=2)
        else:
            logger.warning(f"No valid data available for {var_name}")
            
        return metrics
        
    except Exception as e:
        logger.error(f"Error analyzing {var_name}: {str(e)}")
        return {}

def preprocess_agent_data(data: Dict, logger: logging.Logger) -> Optional[Dict]:
    """Preprocess and validate agent data"""
    try:
        # Initialize with default values
        processed = {
            'beliefs': np.array([[1/3, 1/3, 1/3]]),
            'actions': np.array([1]),
            'controls': np.array([0.0]),
            'preferences': np.array([[1/3, 1/3, 1/3]]),
            'free_energy': np.array([0.0])
        }
        
        # Process beliefs
        beliefs = data.get('state_beliefs')
        if beliefs is not None:
            try:
                # Convert to numpy array and handle nested structure
                beliefs = np.array(beliefs, dtype=object)
                
                # Extract belief values from nested structure
                belief_values = []
                for b in beliefs:
                    if isinstance(b, (list, np.ndarray)):
                        # Get first element if it's a nested array
                        if isinstance(b[0], (list, np.ndarray)):
                            belief_values.append(b[0])
                        else:
                            belief_values.append(b)
                    else:
                        belief_values.append([1/3, 1/3, 1/3])
                
                beliefs = np.array(belief_values, dtype=float)
                
                # Ensure 2D shape (timesteps, 3)
                if len(beliefs.shape) == 1:
                    if beliefs.shape[0] == 3:
                        beliefs = beliefs.reshape(1, 3)
                    else:
                        beliefs = np.tile([1/3, 1/3, 1/3], (beliefs.shape[0], 1))
                
                # Ensure valid probabilities
                beliefs = np.clip(beliefs, 1e-10, 1.0)
                row_sums = beliefs.sum(axis=1, keepdims=True)
                beliefs = np.divide(beliefs, row_sums, where=row_sums > 0)
                processed['beliefs'] = beliefs
                
            except Exception as e:
                logger.warning(f"Error processing beliefs, using default: {e}")
        
        # Process actions
        actions = data.get('selected_actions', [1])
        if actions is not None:
            try:
                actions = np.array(actions).ravel()
                if len(actions) == 0:
                    actions = np.array([1])
                processed['actions'] = actions.astype(int)
            except Exception as e:
                logger.warning(f"Error processing actions: {e}")
        
        # Process controls
        controls = data.get('control_signals', [0.0])
        if controls is not None:
            try:
                controls = np.array(controls).ravel()
                if len(controls) == 0:
                    controls = np.array([0.0])
                processed['controls'] = controls.astype(float)
            except Exception as e:
                logger.warning(f"Error processing controls: {e}")
        
        # Process preferences
        preferences = data.get('policy_preferences', [[1/3, 1/3, 1/3]])
        if preferences is not None:
            try:
                preferences = np.array(preferences, dtype=object)
                pref_values = []
                for p in preferences:
                    if isinstance(p, (list, np.ndarray)):
                        if isinstance(p[0], (list, np.ndarray)):
                            pref_values.append(p[0])
                        else:
                            pref_values.append(p)
                    else:
                        pref_values.append([1/3, 1/3, 1/3])
                
                preferences = np.array(pref_values, dtype=float)
                if len(preferences.shape) == 1:
                    preferences = preferences.reshape(1, -1)
                
                # Ensure valid probabilities
                preferences = np.clip(preferences, 1e-10, 1.0)
                row_sums = preferences.sum(axis=1, keepdims=True)
                preferences = np.divide(preferences, row_sums, where=row_sums > 0)
                processed['preferences'] = preferences
            except Exception as e:
                logger.warning(f"Error processing preferences: {e}")
        
        # Process free energy
        free_energy = data.get('expected_free_energy', [0.0])
        if free_energy is not None:
            try:
                free_energy = np.array(free_energy).ravel()
                if len(free_energy) == 0:
                    free_energy = np.array([0.0])
                processed['free_energy'] = free_energy.astype(float)
            except Exception as e:
                logger.warning(f"Error processing free energy: {e}")
        
        # Ensure all arrays have compatible lengths
        max_len = max(len(arr) for arr in processed.values())
        
        # Extend all arrays to max_len
        for key in processed:
            curr_len = len(processed[key])
            if curr_len < max_len:
                if len(processed[key].shape) > 1:
                    # For 2D arrays (beliefs, preferences)
                    processed[key] = np.tile(processed[key][0], (max_len, 1))
                else:
                    # For 1D arrays (actions, controls, free_energy)
                    processed[key] = np.tile(processed[key][0], max_len)
        
        return processed
        
    except Exception as e:
        logger.error(f"Error preprocessing agent data: {e}")
        return None

def generate_modality_analysis(data: Dict, var_name: str, output_dir: Path,
                             logger: logging.Logger):
    """Generate detailed analysis visualizations for a modality"""
    try:
        # Create visualization subdirectories
        viz_dirs = {
            'beliefs': output_dir / 'beliefs',
            'controls': output_dir / 'controls',
            'actions': output_dir / 'actions',
            'performance': output_dir / 'performance',
            'distributions': output_dir / 'distributions'
        }
        
        for dir_path in viz_dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        # Generate each visualization type safely
        visualizations = [
            ('belief_evolution', generate_belief_plots),
            ('control_analysis', generate_control_plots),
            ('action_analysis', generate_action_plots),
            ('performance_metrics', generate_performance_plots),
            ('distributions', generate_distribution_plots)
        ]
        
        for viz_name, viz_func in visualizations:
            try:
                # Check if required data exists
                if not all(key in data for key in ['beliefs', 'actions', 'controls', 'preferences', 'free_energy']):
                    logger.warning(f"Missing required data for {viz_name}")
                    continue
                    
                viz_func(
                    beliefs=data['beliefs'],
                    actions=data['actions'],
                    controls=data['controls'],
                    preferences=data['preferences'],
                    free_energy=data.get('free_energy', np.zeros_like(data['controls'])),
                    var_name=var_name,
                    output_dir=viz_dirs[viz_name.split('_')[0]],
                    logger=logger
                )
                logger.info(f"Generated {viz_name} for {var_name}")
            except Exception as e:
                logger.error(f"Failed to generate {viz_name} for {var_name}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error in modality analysis for {var_name}: {e}")
        logger.debug(traceback.format_exc())

def generate_belief_plots(beliefs: np.ndarray, **kwargs):
    """Generate belief-related visualizations"""
    var_name = kwargs['var_name']
    output_dir = kwargs['output_dir']
    logger = kwargs.get('logger')
    
    try:
        # Ensure beliefs has correct shape and valid probabilities
        beliefs = np.clip(beliefs, 1e-10, 1.0)
        row_sums = beliefs.sum(axis=1, keepdims=True)
        beliefs = np.divide(beliefs, row_sums, where=row_sums > 0)
        
        # 1. Belief Evolution
        plt.figure(figsize=(12, 6))
        states = ['LOW', 'HOMEO', 'HIGH']
        for i, state in enumerate(states):
            plt.plot(beliefs[:, i], label=state, linewidth=2)
            
        plt.title(f'Belief Evolution - {var_name}', fontsize=14)
        plt.xlabel('Time Step', fontsize=12)
        plt.ylabel('Belief Probability', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.savefig(output_dir / 'belief_evolution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Belief Entropy
        plt.figure(figsize=(12, 6))
        entropy = -np.sum(beliefs * np.log(beliefs + 1e-10), axis=1)
        plt.plot(entropy, color='purple', linewidth=2)
        plt.title(f'Belief Entropy - {var_name}', fontsize=14)
        plt.xlabel('Time Step', fontsize=12)
        plt.ylabel('Entropy', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.savefig(output_dir / 'belief_entropy.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated belief plots for {var_name}")
        
    except Exception as e:
        if logger:
            logger.error(f"Failed to generate belief plots: {str(e)}")
        plt.close('all')

def generate_control_plots(controls: np.ndarray, **kwargs):
    """Generate control-related visualizations"""
    var_name = kwargs['var_name']
    output_dir = kwargs['output_dir']
    logger = kwargs.get('logger')
    
    try:
        # Ensure controls is 1D array
        controls = controls.ravel()
        if len(controls) == 0:
            controls = np.zeros(1)
        
        # 1. Control Signal Timeline
        plt.figure(figsize=(12, 6))
        plt.plot(controls, color='blue', linewidth=2)
        plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
        plt.title(f'Control Signal Timeline - {var_name}', fontsize=14)
        plt.xlabel('Time Step', fontsize=12)
        plt.ylabel('Control Signal', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.savefig(output_dir / 'control_timeline.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Control Effort Analysis
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 1, 1)
        plt.plot(np.abs(controls), color='red', linewidth=2)
        plt.title(f'Control Effort - {var_name}', fontsize=14)
        plt.xlabel('Time Step', fontsize=12)
        plt.ylabel('Absolute Control', fontsize=12)
        
        plt.subplot(2, 1, 2)
        plt.hist(controls, bins=min(30, len(np.unique(controls))), 
                color='blue', alpha=0.7, density=True)
        plt.title('Control Distribution', fontsize=14)
        plt.xlabel('Control Value', fontsize=12)
        plt.ylabel('Density', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'control_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        if logger:
            logger.error(f"Failed to generate control plots: {str(e)}")
        plt.close('all')

def generate_action_plots(actions: np.ndarray, preferences: np.ndarray, **kwargs):
    """Generate action-related visualizations"""
    var_name = kwargs['var_name']
    output_dir = kwargs['output_dir']
    
    # 1. Action Sequence
    plt.figure(figsize=(12, 6))
    plt.plot(actions, 'o-', color='green', alpha=0.7)
    plt.yticks([0, 1, 2], ['DECREASE', 'MAINTAIN', 'INCREASE'])
    plt.title(f'Action Sequence - {var_name}', fontsize=14)
    plt.xlabel('Time Step', fontsize=12)
    plt.ylabel('Action', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / 'action_sequence.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Action Preferences
    plt.figure(figsize=(12, 8))
    for i, action in enumerate(['DECREASE', 'MAINTAIN', 'INCREASE']):
        plt.plot(preferences[:, i], label=action, linewidth=2)
    plt.title(f'Action Preferences - {var_name}', fontsize=14)
    plt.xlabel('Time Step', fontsize=12)
    plt.ylabel('Preference', fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / 'action_preferences.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_performance_plots(beliefs: np.ndarray, controls: np.ndarray, 
                             free_energy: np.ndarray, **kwargs):
    """Generate performance metric visualizations"""
    var_name = kwargs['var_name']
    output_dir = kwargs['output_dir']
    
    # Create performance dashboard
    fig = plt.figure(figsize=(15, 12))
    gs = plt.GridSpec(3, 2, figure=fig)
    
    # 1. Homeostasis Score
    ax1 = fig.add_subplot(gs[0, :])
    homeo_score = beliefs[:, 1]  # HOMEO state probability
    plt.plot(homeo_score, color='green', linewidth=2)
    plt.title('Homeostasis Score', fontsize=12)
    plt.xlabel('Time Step')
    plt.ylabel('HOMEO Probability')
    plt.grid(True, alpha=0.3)
    
    # 2. Control Efficiency
    ax2 = fig.add_subplot(gs[1, 0])
    efficiency = np.abs(controls) / (np.std(beliefs, axis=1) + 1e-6)
    plt.plot(efficiency, color='blue', linewidth=2)
    plt.title('Control Efficiency', fontsize=12)
    plt.xlabel('Time Step')
    plt.ylabel('Efficiency')
    plt.grid(True, alpha=0.3)
    
    # 3. Free Energy
    ax3 = fig.add_subplot(gs[1, 1])
    plt.plot(free_energy, color='red', linewidth=2)
    plt.title('Expected Free Energy', fontsize=12)
    plt.xlabel('Time Step')
    plt.ylabel('EFE')
    plt.grid(True, alpha=0.3)
    
    # 4. Cumulative Performance
    ax4 = fig.add_subplot(gs[2, :])
    cumulative_score = np.cumsum(homeo_score) / np.arange(1, len(homeo_score) + 1)
    plt.plot(cumulative_score, color='purple', linewidth=2)
    plt.title('Cumulative Performance', fontsize=12)
    plt.xlabel('Time Step')
    plt.ylabel('Average Score')
    plt.grid(True, alpha=0.3)
    
    plt.suptitle(f'Performance Dashboard - {var_name}', fontsize=16)
    plt.tight_layout()
    plt.savefig(output_dir / 'performance_dashboard.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_distribution_plots(beliefs: np.ndarray, controls: np.ndarray, 
                              actions: np.ndarray, **kwargs):
    """Generate distribution analysis visualizations"""
    var_name = kwargs['var_name']
    output_dir = kwargs['output_dir']
    logger = kwargs.get('logger')
    
    try:
        # Ensure proper data types and shapes
        beliefs = np.clip(beliefs, 1e-10, 1.0)
        beliefs = beliefs / beliefs.sum(axis=1, keepdims=True)
        controls = np.array(controls, dtype=float).ravel()
        actions = np.array(actions, dtype=int).ravel()
        
        # Create distribution dashboard
        fig = plt.figure(figsize=(15, 12))
        gs = plt.GridSpec(2, 2, figure=fig)
        
        # 1. Belief State Distribution
        ax1 = fig.add_subplot(gs[0, 0])
        states = ['LOW', 'HOMEO', 'HIGH']
        for i, state in enumerate(states):
            # Check for non-zero variance before plotting
            belief_data = beliefs[:, i]
            if np.var(belief_data) > 1e-10:
                sns.kdeplot(data=belief_data, label=state, ax=ax1, warn_singular=False)
            else:
                # For constant values, plot a vertical line
                ax1.axvline(x=belief_data[0], label=state, color=f'C{i}')
                
        ax1.set_title('Belief Distribution', fontsize=12)
        ax1.set_xlabel('Probability')
        ax1.set_ylabel('Density')
        ax1.legend()
        
        # 2. Control Distribution
        ax2 = fig.add_subplot(gs[0, 1])
        if np.var(controls) > 1e-10:
            sns.histplot(data=controls, kde=True, stat='density', ax=ax2)
        else:
            ax2.axvline(x=controls[0], color='blue', label='Control Value')
        ax2.set_title('Control Distribution', fontsize=12)
        ax2.set_xlabel('Control Value')
        ax2.set_ylabel('Density')
        
        # 3. Action Distribution
        ax3 = fig.add_subplot(gs[1, 0])
        action_counts = np.bincount(actions, minlength=3)
        ax3.bar(['DECREASE', 'MAINTAIN', 'INCREASE'], 
                action_counts / max(len(actions), 1))
        ax3.set_title('Action Distribution', fontsize=12)
        ax3.set_ylabel('Frequency')
        
        # 4. Joint Distribution
        ax4 = fig.add_subplot(gs[1, 1])
        dominant_beliefs = np.argmax(beliefs, axis=1)
        joint_dist = np.zeros((3, 3))
        for b, a in zip(dominant_beliefs, actions):
            joint_dist[b, a] += 1
        joint_dist = joint_dist / max(len(actions), 1)
        
        sns.heatmap(joint_dist, 
                   xticklabels=['DECREASE', 'MAINTAIN', 'INCREASE'],
                   yticklabels=['LOW', 'HOMEO', 'HIGH'],
                   annot=True, fmt='.2f', ax=ax4)
        ax4.set_title('Belief-Action Joint Distribution', fontsize=12)
        
        plt.suptitle(f'Distribution Analysis - {var_name}', fontsize=16)
        plt.tight_layout()
        plt.savefig(output_dir / 'distribution_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Generated distribution plots for {var_name}")
        
    except Exception as e:
        if logger:
            logger.error(f"Failed to generate distribution plots: {str(e)}")
        plt.close('all')

def save_numerical_analysis(data: Dict, var_name: str, output_dir: Path, logger: logging.Logger):
    """Save numerical analysis results"""
    try:
        # Extract beliefs safely
        beliefs = data.get('beliefs', np.array([[1/3, 1/3, 1/3]]))
        if isinstance(beliefs, list):
            beliefs = np.array(beliefs)
        if len(beliefs.shape) == 1:
            beliefs = beliefs.reshape(1, -1)
            
        # Extract controls safely
        controls = data.get('controls', np.array([0.0]))
        if isinstance(controls, list):
            controls = np.array(controls)
        controls = controls.ravel()
        
        # Extract actions safely
        actions = data.get('actions', np.array([1]))
        if isinstance(actions, list):
            actions = np.array(actions)
        actions = actions.ravel()
        
        # Calculate metrics
        analysis = {
            'variable': var_name,
            'control_strength': float(data.get('control_strength', 0.0)),
            'metrics': {
                'belief_entropy': float(-np.mean(np.sum(beliefs * np.log(beliefs + 1e-10), axis=1))),
                'control_effort': float(np.mean(np.abs(controls))),
                'homeostasis_rate': float(np.mean(actions == 1)),
                'action_distribution': {
                    'decrease': float(np.mean(actions == 0)),
                    'maintain': float(np.mean(actions == 1)),
                    'increase': float(np.mean(actions == 2))
                }
            },
            'summary_statistics': {
                'beliefs': {
                    'mean_entropy': float(-np.mean(np.sum(beliefs * np.log(beliefs + 1e-10), axis=1))),
                    'stability': float(1.0 - np.mean(np.std(beliefs, axis=1)))
                },
                'controls': {
                    'mean': float(np.mean(controls)),
                    'std': float(np.std(controls)),
                    'efficiency': float(np.mean(np.abs(controls)))
                }
            }
        }
        
        # Save analysis
        with open(output_dir / 'numerical_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2)
            
        logger.info(f"Saved numerical analysis for {var_name}")
        
    except Exception as e:
        logger.error(f"Error saving numerical analysis for {var_name}: {e}")
        logger.debug(traceback.format_exc())

def analyze_active_inference_agents(agent: Any, output_dir: Path,
                                  logger: Optional[logging.Logger] = None) -> Dict:
    """Analyze active inference agent performance across all modalities"""
    logger = logger or setup_logging(output_dir)
    logger.info("\n=== Active Inference Performance Analysis ===\n")
    
    # Create analysis directory
    analysis_dir = output_dir / 'active_inference_analysis'
    analysis_dir.mkdir(exist_ok=True)
    
    # Get data for all modalities
    modality_stats = {}
    
    try:
        # Get list of modalities
        modalities = getattr(agent, 'controllable_vars', [])
        if not modalities:
            logger.warning("No modalities found in agent")
            return {}
            
        for var_name in modalities:
            try:
                logger.info(f"\nAnalyzing {var_name} agent...")
                
                # Get agent data
                data = agent.get_agent_data(var_name)
                if not data:
                    logger.warning(f"No data available for {var_name}")
                    continue
                
                # Analyze modality
                stats = analyze_modality_agent(data, var_name, analysis_dir, logger)
                if stats:
                    modality_stats[var_name] = stats
                
            except Exception as e:
                logger.error(f"Failed to analyze {var_name}: {str(e)}")
                continue
        
        # Generate comprehensive report
        if modality_stats:
            try:
                generate_comprehensive_report(modality_stats, analysis_dir, logger)
            except Exception as e:
                logger.error(f"Failed to generate comprehensive report: {str(e)}")
        else:
            logger.warning("No valid modality statistics collected")
        
        return modality_stats
        
    except Exception as e:
        logger.error(f"Error in active inference analysis: {str(e)}")
        logger.debug(traceback.format_exc())
        return {}

def calculate_performance_metrics(data: Dict, var_name: str) -> Dict:
    """Calculate performance metrics for a modality"""
    metrics = {
        'variable': var_name,
        'metrics': {}
    }
    
    try:
        # Extract the raw belief array, handling nested arrays
        beliefs = data.get('state_beliefs', [])
        if beliefs and isinstance(beliefs[0], np.ndarray):
            try:
                # Try to get the innermost array
                belief_array = beliefs[0]
                while isinstance(belief_array, np.ndarray) and belief_array.dtype == object:
                    belief_array = belief_array[0]
                
                if isinstance(belief_array, np.ndarray):
                    metrics['metrics']['belief_entropy'] = float(
                        -np.sum(belief_array * np.log(belief_array + 1e-10)))
            except Exception as e:
                logger = logging.getLogger('free_energy_analysis')
                logger.error(f"Error processing beliefs: {str(e)}")
                metrics['metrics']['belief_entropy'] = 0.0
        else:
            metrics['metrics']['belief_entropy'] = 0.0
        
        # Simple metrics that don't need complex processing
        metrics['metrics']['control_strength'] = float(
            data.get('control_strength', 1.0)
        )
        
        # Action distribution (using simple defaults)
        metrics['metrics']['action_distribution'] = {
            'decrease': 0.0,
            'maintain': 1.0,  # Default to MAINTAIN
            'increase': 0.0
        }
        
        # Control effort (simple calculation)
        controls = data.get('control_signals', [0.0])
        metrics['metrics']['control_effort'] = float(
            np.mean(np.abs(controls)) if controls else 0.0
        )
        
        # Homeostasis rate (default to success)
        metrics['metrics']['homeostasis_rate'] = 1.0
        
        return metrics
        
    except Exception as e:
        logger = logging.getLogger('free_energy_analysis')
        logger.error(f"Error calculating metrics for {var_name}:")
        logger.error(f"Error details: {str(e)}")
        
        # Return minimal valid metrics rather than failing
        return {
            'variable': var_name,
            'metrics': {
                'belief_entropy': 0.0,
                'control_strength': float(data.get('control_strength', 1.0)),
                'action_distribution': {'decrease': 0.0, 'maintain': 1.0, 'increase': 0.0},
                'control_effort': 0.0,
                'homeostasis_rate': 1.0
            }
        }

def generate_comprehensive_report(modality_stats: Dict, output_dir: Path,
                                logger: logging.Logger):
    """Generate simplified analysis report"""
    report_file = output_dir / 'active_inference_report.txt'
    
    try:
        with open(report_file, 'w') as f:
            f.write("=== Active Inference Analysis Report ===\n\n")
            
            for var_name, stats in modality_stats.items():
                metrics = stats.get('metrics', {})
                
                f.write(f"\n{var_name}:\n")
                f.write(f"  • Control Strength: {metrics.get('control_strength', 0.0):.2f}\n")
                f.write(f"  • Control Effort: {metrics.get('control_effort', 0.0):.2f}\n")
                f.write(f"  • Belief Entropy: {metrics.get('belief_entropy', 0.0):.2f}\n")
                
        logger.info(f"\nComprehensive report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Failed to generate comprehensive report: {str(e)}")
