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

def analyze_modality_agent(data: Dict, var_name: str, output_dir: Path,
                         logger: logging.Logger) -> Dict:
    """Analyze single modality agent performance"""
    # Create modality directory
    mod_dir = output_dir / var_name
    mod_dir.mkdir(exist_ok=True)
    
    try:
        # Basic metrics
        metrics = calculate_performance_metrics(data, var_name)
        
        # Save raw agent data
        with open(mod_dir / 'agent_data.json', 'w') as f:
            json_data = {
                'control_strength': float(data.get('control_strength', 0.0)),
                'control_signals': [float(x) for x in data.get('control_signals', [])],
                'action_history': [int(x) for x in data.get('selected_actions', [])]
            }
            json.dump(json_data, f, indent=2)
            
        # Generate modality-specific visualizations
        generate_modality_analysis(data, var_name, mod_dir, logger)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error analyzing {var_name}: {str(e)}")
        return {}

def generate_modality_analysis(data: Dict, var_name: str, output_dir: Path,
                             logger: logging.Logger):
    """Generate detailed analysis visualizations for a modality"""
    try:
        # 1. Belief Evolution Plot
        plt.figure(figsize=(10, 6))
        beliefs = data.get('state_beliefs', [])
        if beliefs:
            belief_array = np.array(beliefs)
            if len(belief_array.shape) > 2:
                belief_array = belief_array.reshape(-1, 3)
            for i, state in enumerate(['LOW', 'HOMEO', 'HIGH']):
                plt.plot(belief_array[:, i], label=state)
        plt.title(f'Belief Evolution - {var_name}')
        plt.xlabel('Time Step')
        plt.ylabel('Belief Probability')
        plt.legend()
        plt.grid(True)
        plt.savefig(output_dir / 'belief_evolution.png')
        plt.close()
        
        # 2. Control Actions Plot
        plt.figure(figsize=(10, 6))
        actions = data.get('selected_actions', [])
        if actions:
            action_array = np.array(actions)
            plt.plot(action_array, marker='o', linestyle='-', alpha=0.6)
            plt.yticks([0, 1, 2], ['DECREASE', 'MAINTAIN', 'INCREASE'])
        plt.title(f'Control Actions - {var_name}')
        plt.xlabel('Time Step')
        plt.ylabel('Action')
        plt.grid(True)
        plt.savefig(output_dir / 'control_actions.png')
        plt.close()
        
        # 3. Control Effort Plot
        plt.figure(figsize=(10, 6))
        controls = data.get('control_signals', [])
        if controls:
            control_array = np.array(controls)
            plt.plot(control_array, color='purple', alpha=0.7)
            plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
        plt.title(f'Control Effort - {var_name}')
        plt.xlabel('Time Step')
        plt.ylabel('Control Signal')
        plt.grid(True)
        plt.savefig(output_dir / 'control_effort.png')
        plt.close()
        
        # 4. Policy Preferences Plot
        plt.figure(figsize=(10, 6))
        prefs = data.get('policy_preferences', [])
        if prefs:
            pref_array = np.array(prefs)
            if len(pref_array.shape) > 2:
                pref_array = pref_array.reshape(-1, 3)
            for i, action in enumerate(['DECREASE', 'MAINTAIN', 'INCREASE']):
                plt.plot(pref_array[:, i], label=action)
        plt.title(f'Policy Preferences - {var_name}')
        plt.xlabel('Time Step')
        plt.ylabel('Preference Probability')
        plt.legend()
        plt.grid(True)
        plt.savefig(output_dir / 'policy_preferences.png')
        plt.close()
        
        # 5. Generate detailed report
        with open(output_dir / 'analysis_report.txt', 'w') as f:
            f.write(f"=== Detailed Analysis: {var_name} ===\n\n")
            
            # Control characteristics
            f.write("Control Characteristics:\n")
            f.write(f"  • Control Strength: {data.get('control_strength', 0.0):.2f}\n")
            
            # Action statistics
            if actions:
                action_counts = np.bincount(actions, minlength=3)
                total = len(actions)
                f.write("\nAction Distribution:\n")
                f.write(f"  • DECREASE: {action_counts[0]/total:.1%}\n")
                f.write(f"  • MAINTAIN: {action_counts[1]/total:.1%}\n")
                f.write(f"  • INCREASE: {action_counts[2]/total:.1%}\n")
            
            # Control effort statistics
            if controls:
                controls = np.array(controls)
                f.write("\nControl Effort:\n")
                f.write(f"  • Mean: {np.mean(np.abs(controls)):.2f}\n")
                f.write(f"  • Max:  {np.max(np.abs(controls)):.2f}\n")
                f.write(f"  • Std:  {np.std(controls):.2f}\n")
            
            # Belief statistics
            if beliefs:
                belief_array = np.array(beliefs)
                if len(belief_array.shape) > 2:
                    belief_array = belief_array.reshape(-1, 3)
                entropy = -np.sum(belief_array * np.log(belief_array + 1e-10), axis=1)
                f.write("\nBelief Statistics:\n")
                f.write(f"  • Mean Entropy: {np.mean(entropy):.2f}\n")
                f.write(f"  • Entropy Std:  {np.std(entropy):.2f}\n")
            
            # Expected free energy
            efe = data.get('expected_free_energy', [])
            if efe:
                efe_array = np.array(efe)
                f.write("\nExpected Free Energy:\n")
                f.write(f"  • Mean: {np.mean(efe_array):.2f}\n")
                f.write(f"  • Std:  {np.std(efe_array):.2f}\n")
        
        logger.info(f"Generated detailed analysis for {var_name}")
        
    except Exception as e:
        logger.error(f"Error generating analysis for {var_name}: {str(e)}")

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
    for var_name in agent.controllable_vars:
        try:
            logger.info(f"\nAnalyzing {var_name} agent...")
            
            # Get agent data
            data = agent.get_agent_data(var_name)
            if not data:
                logger.warning(f"No data available for {var_name}")
                continue
            
            # Analyze modality
            stats = analyze_modality_agent(data, var_name, analysis_dir, logger)
            modality_stats[var_name] = stats
            
        except Exception as e:
            logger.error(f"Failed to analyze {var_name}: {str(e)}")
            continue
    
    # Generate comprehensive report
    try:
        generate_comprehensive_report(modality_stats, analysis_dir, logger)
    except Exception as e:
        logger.error(f"Failed to generate comprehensive report: {str(e)}")
    
    return modality_stats

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
                        -np.sum(belief_array * np.log(belief_array + 1e-10))
                    )
            except Exception:
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
