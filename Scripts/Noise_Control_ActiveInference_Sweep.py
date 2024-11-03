"""
Noise and Controllability Parameter Sweep Analysis for Active Inference Control
"""

import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from typing import Dict, List
import logging
import traceback
import seaborn as sns
import matplotlib
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

matplotlib.use('Agg')  # Use non-interactive backend
sns.set_style("whitegrid")  # Set consistent style

# Use absolute imports
from Scripts.Biofirm_Agent import BiofirmAgent
from Scripts.utils.logging_utils import get_component_logger

# Configuration Parameters
NUM_CPUS = 8  # Number of parallel threads
NOISE_RANGE = np.linspace(0.1, 2.0, 10)  # Range of noise levels
CONTROL_RANGE = np.linspace(0.5, 3.0, 10)  # Range of control strengths
TIMESTEPS = 100  # Shorter runs for sweep
NUM_REPEATS = 3  # Repeats per parameter combination

POMDP_CONFIG = {
    'observation_confidence': 0.90,
    'homeostatic_preference': 4.0
}

def create_sweep_config(noise_std: float, control_strength: float) -> Dict:
    """Create configuration for sweep simulation"""
    return {
        "variables": {
            "sweep_var": {
                "initial_value": 50.0,
                "control_strength": control_strength,
                "noise_std": noise_std,
                "trend": 0.0,
                "constraints": {
                    "lower": 45,  # Match current constraints
                    "upper": 55
                }
            }
        }
    }

class NoiseControlSweepAnalysis:
    def __init__(self):
        """Initialize sweep analysis"""
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = get_component_logger(logging.getLogger(__name__), 'sweep')
        
        # Create sweep directory structure
        self.sweep_dir = Path("Outputs/sweep")
        self.sweep_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped run directory inside sweep
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = self.sweep_dir / f"run_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file logging
        fh = logging.FileHandler(self.output_dir / "sweep.log")
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # Create subdirectories for different outputs
        self.viz_dir = self.output_dir / "visualizations"
        self.data_dir = self.output_dir / "data"
        self.results_dir = self.output_dir / "results"
        
        for directory in [self.viz_dir, self.data_dir, self.results_dir]:
            directory.mkdir(exist_ok=True)
        
        # Use global parameters
        self.noise_range = NOISE_RANGE
        self.control_range = CONTROL_RANGE
        self.n_timesteps = TIMESTEPS
        
        # Print configuration
        self.logger.info("\nActive Inference Parameter Sweep")
        self.logger.info("=" * 40)
        self.logger.info(f"Using {NUM_CPUS} CPU threads")
        self.logger.info(f"Noise range: {self.noise_range[0]:.3f} to {self.noise_range[-1]:.3f}")
        self.logger.info(f"Control range: {self.control_range[0]:.3f} to {self.control_range[-1]:.3f}")
        self.logger.info(f"Number of noise levels: {len(self.noise_range)}")
        self.logger.info(f"Number of control levels: {len(self.control_range)}")
        self.logger.info(f"Total parameter combinations: {len(self.noise_range) * len(self.control_range)}")
        self.logger.info(f"Repeats per combination: {NUM_REPEATS}")
        self.logger.info(f"Timesteps per simulation: {self.n_timesteps}")
        self.logger.info(f"Output directory: {self.output_dir}\n")

    def run_parameter_sweep(self, n_repeats: int = NUM_REPEATS) -> pd.DataFrame:
        """Run full parameter sweep across noise and control ranges"""
        results = []
        total_combinations = len(self.noise_range) * len(self.control_range)
        
        # Create combinations directory
        combinations_dir = self.results_dir / "combinations"
        combinations_dir.mkdir(exist_ok=True)
        
        # Create parameter combinations
        param_combinations = [
            (noise, control, combinations_dir, repeat)
            for noise in self.noise_range
            for control in self.control_range
            for repeat in range(n_repeats)
        ]
        
        # Run simulations in parallel
        with ThreadPoolExecutor(max_workers=NUM_CPUS) as executor:
            futures = []
            for params in param_combinations:
                future = executor.submit(self._run_single_combination, *params)
                futures.append(future)
            
            # Process results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    metrics = future.result()
                    if metrics:
                        results.append(metrics)
                        
                    # Log progress
                    progress = (i + 1) / len(param_combinations) * 100
                    self.logger.info(f"Progress: {progress:.1f}% ({i + 1}/{len(param_combinations)})")
                    
                except Exception as e:
                    self.logger.error(f"Error in simulation: {str(e)}")
                    self.logger.error(traceback.format_exc())
        
        # Create final results DataFrame
        if results:
            results_df = pd.DataFrame(results)
            self.save_final_results(results_df)
            return results_df
        else:
            self.logger.error("No valid results collected")
            return pd.DataFrame()

    def _run_single_combination(self, noise_std: float, control_strength: float, 
                              combinations_dir: Path, repeat: int) -> Dict:
        """Run single parameter combination"""
        try:
            # Create directory for this combination
            combo_dir = combinations_dir / f"N{noise_std:.3f}_C{control_strength:.3f}"
            combo_dir.mkdir(exist_ok=True)
            
            # Run simulation
            metrics = self.run_single_simulation(
                noise_std, control_strength, combo_dir, repeat
            )
            
            if metrics:
                metrics.update({
                    'noise_std': noise_std,
                    'control_strength': control_strength,
                    'repeat': repeat
                })
                
                # Log completion
                self.logger.info(
                    f"Completed N={noise_std:.3f}, C={control_strength:.3f}, "
                    f"Repeat {repeat + 1}/{NUM_REPEATS}"
                )
                
                return metrics
                
        except Exception as e:
            self.logger.error(
                f"Error in combination N={noise_std:.3f}, C={control_strength:.3f}, "
                f"Repeat {repeat}: {str(e)}"
            )
            self.logger.error(traceback.format_exc())
            return None

    def run_single_simulation(self, noise_std: float, control_strength: float, 
                            output_dir: Path, repeat: int) -> Dict:
        """Run single simulation with active inference control"""
        try:
            # Initialize state and history
            state = 50.0  # Initial state
            history = {
                'timesteps': [],
                'states': [state],
                'actions': [],
                'observations': [],
                'controls': [],
                'satisfaction': [],
                'beliefs': [],
                'free_energy': []
            }
            
            # Create config and initialize agent
            config = create_sweep_config(noise_std, control_strength)
            agent = BiofirmAgent(config, self.logger)
            
            start_time = time.time()
            
            # Run active inference loop
            self.logger.info(
                f"\nStarting Active Inference Loop - "
                f"N={noise_std:.3f}, C={control_strength:.3f}, "
                f"Repeat {repeat + 1}"
            )
            
            for step in range(self.n_timesteps):
                # Get discrete observation from current state
                obs_state = 0 if state < 45 else (2 if state > 55 else 1)
                observation = {"sweep_var": obs_state}
                
                # Get action from agent
                action_dict = agent.get_action(observation)
                
                # Process action and control
                if action_dict and "sweep_var" in action_dict:
                    control = action_dict["sweep_var"]  # Already scaled by control_strength
                else:
                    control = 0.0  # Default to MAINTAIN
                
                # Add noise and update state
                noise = np.random.normal(0, noise_std)
                state = np.clip(state + control + noise, 0.0, 100.0)
                
                # Get agent data for analysis
                agent_data = agent.get_agent_data("sweep_var")
                
                # Update history
                history['timesteps'].append(step)
                history['states'].append(float(state))
                history['observations'].append(int(obs_state))
                history['controls'].append(float(control))
                history['satisfaction'].append(bool(45.0 <= state <= 55.0))
                
                # Store agent internal states
                if agent_data:
                    history['beliefs'].append(
                        agent_data.get('state_beliefs', [[1/3, 1/3, 1/3]])[0]
                    )
                    history['free_energy'].append(
                        agent_data.get('expected_free_energy', [0.0])[0]
                    )
                
                # Log detailed state every 10 steps
                if step % 10 == 0:
                    self.logger.info(
                        f"Step {step}: State={state:.2f}, Obs={obs_state}, "
                        f"Control={control:+.2f}"
                    )
            
            # Calculate metrics
            runtime = time.time() - start_time
            satisfaction_rate = float(np.mean(history['satisfaction']))
            control_effort = float(np.mean(np.abs(history['controls'])))
            belief_entropy = float(np.mean([
                -np.sum(b * np.log(b + 1e-10)) for b in history['beliefs']
            ]))
            
            metrics = {
                'noise_std': noise_std,
                'control_strength': control_strength,
                'runtime': runtime,
                'satisfaction_rate': satisfaction_rate,
                'control_effort': control_effort,
                'belief_entropy': belief_entropy,
                'mean_free_energy': float(np.mean(history['free_energy'])),
                'final_state': history['states'][-1],
                'mean_state': float(np.mean(history['states'])),
                'state_std': float(np.std(history['states']))
            }
            
            # Save detailed results
            self.save_simulation_history(history, output_dir, repeat)
            self.create_simulation_plots(history, output_dir, repeat)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error in simulation: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    def save_simulation_history(self, history: Dict, output_dir: Path, repeat: int):
        """Save simulation history and create visualization subfolder"""
        # Create visualization subfolder
        viz_dir = output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        # Save raw history data
        history_file = output_dir / f"history_repeat_{repeat}.json"
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def create_simulation_plots(self, history: Dict, output_dir: Path, repeat: int):
        """Create detailed plots for single simulation run"""
        viz_dir = output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        try:
            # Convert data types explicitly
            states = np.array(history['states'], dtype=float)
            controls = np.array(history['controls'], dtype=float)
            beliefs = np.array(history['beliefs'], dtype=float)
            observations = np.array(history['observations'], dtype=int)
            timesteps = np.arange(len(states))
            
            # 1. State trajectory with control signals
            plt.figure(figsize=(15, 8))
            plt.subplot(2, 1, 1)
            plt.plot(timesteps, states, label='State', linewidth=2)
            plt.axhline(y=40, color='r', linestyle='--', alpha=0.3, label='Bounds')
            plt.axhline(y=60, color='r', linestyle='--', alpha=0.3)
            plt.axhline(y=50, color='g', linestyle=':', alpha=0.3, label='Target')
            plt.title(f'State Trajectory and Control Signals - Repeat {repeat}')
            plt.xlabel('Timestep')
            plt.ylabel('State Value')
            plt.legend()
            plt.grid(True)

            plt.subplot(2, 1, 2)
            plt.plot(timesteps[1:], controls, label='Control Signal', color='orange')
            plt.title('Control Actions')
            plt.xlabel('Timestep')
            plt.ylabel('Control Magnitude')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            
            plot_path = viz_dir / f"state_and_control_repeat_{repeat}.png"
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            self.logger.info(f"Saved state and control plot to {plot_path}")

            # 2. Belief evolution with observations
            plt.figure(figsize=(15, 8))
            
            # Plot beliefs
            plt.subplot(2, 1, 1)
            labels = ['LOW', 'HOMEO', 'HIGH']
            for i, label in enumerate(labels):
                plt.plot(timesteps[1:], beliefs[:, i], label=label, alpha=0.7)
            plt.title(f'Belief Evolution - Repeat {repeat}')
            plt.xlabel('Timestep')
            plt.ylabel('Belief Probability')
            plt.legend()
            plt.grid(True)

            # Plot observations
            plt.subplot(2, 1, 2)
            obs_colors = ['blue', 'green', 'red']
            plt.scatter(timesteps[1:], observations, 
                       c=[obs_colors[obs] for obs in observations],
                       label='Observations', alpha=0.5)
            plt.yticks([0, 1, 2], labels)
            plt.title('Observations Over Time')
            plt.xlabel('Timestep')
            plt.ylabel('Observation')
            plt.grid(True)
            plt.tight_layout()
            
            plot_path = viz_dir / f"beliefs_and_obs_repeat_{repeat}.png"
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            self.logger.info(f"Saved beliefs and observations plot to {plot_path}")

            # 3. Performance metrics over time
            plt.figure(figsize=(15, 8))
            
            # Rolling satisfaction rate
            window = max(5, len(history['satisfaction']) // 20)
            satisfaction = np.array(history['satisfaction'], dtype=float)
            rolling_satisfaction = pd.Series(satisfaction).rolling(window).mean()
            
            plt.subplot(2, 1, 1)
            plt.plot(timesteps[1:], rolling_satisfaction, 
                    label=f'Rolling Satisfaction (window={window})')
            plt.axhline(y=np.mean(satisfaction), color='r', linestyle='--', 
                       label=f'Mean={np.mean(satisfaction):.2f}')
            plt.title(f'Performance Metrics - Repeat {repeat}')
            plt.xlabel('Timestep')
            plt.ylabel('Satisfaction Rate')
            plt.legend()
            plt.grid(True)

            # Control effectiveness (rolling inverse std)
            plt.subplot(2, 1, 2)
            rolling_std = pd.Series(states).rolling(window).std()
            rolling_effectiveness = 1 / (rolling_std + 1e-6)
            plt.plot(timesteps, rolling_effectiveness, 
                    label='Control Effectiveness', color='purple')
            plt.title('Control Effectiveness Over Time')
            plt.xlabel('Timestep')
            plt.ylabel('Effectiveness (1/std)')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            
            plot_path = viz_dir / f"performance_metrics_repeat_{repeat}.png"
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            self.logger.info(f"Saved performance metrics plot to {plot_path}")

        except Exception as e:
            self.logger.error(f"Error creating simulation plots: {str(e)}")
            self.logger.error(traceback.format_exc())

    def save_intermediate_results(self, results: List[Dict], output_dir: Path, prefix: str):
        """Save intermediate results to file"""
        results_file = output_dir / f"{prefix}_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

    def summarize_combination(self, results: List[Dict], output_dir: Path):
        """Create summary for parameter combination"""
        summary = {
            'n_repeats': len(results),
            'metrics': {
                metric: {
                    'mean': float(np.mean([r[metric] for r in results])),
                    'std': float(np.std([r[metric] for r in results]))
                }
                for metric in ['satisfaction_rate', 'control_effectiveness', 'runtime']
            }
        }
        
        # Save summary
        with open(output_dir / "summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Log summary
        self.logger.info("\nCombination Summary:")
        for metric, stats in summary['metrics'].items():
            self.logger.info(
                f"{metric}: {stats['mean']:.3f} ± {stats['std']:.3f}"
            )

    def save_final_results(self, results_df: pd.DataFrame):
        """Save and visualize final results"""
        # Save raw results
        results_df.to_csv(self.data_dir / "final_results.csv", index=False)
        
        # Create summary visualizations
        self.create_summary_plots(results_df)
        
        # Generate final report
        self.generate_final_report(results_df)

    def create_summary_plots(self, results_df: pd.DataFrame):
        """Create comprehensive summary visualizations"""
        # Create visualization subdirectories
        heatmap_dir = self.viz_dir / "heatmaps"
        analysis_dir = self.viz_dir / "analysis"
        dist_dir = self.viz_dir / "distributions"
        
        for directory in [heatmap_dir, analysis_dir, dist_dir]:
            directory.mkdir(exist_ok=True)
        
        metrics = ['satisfaction_rate', 'control_effectiveness', 'runtime']
        
        for metric in metrics:
            try:
                self._create_metric_heatmap(results_df, metric, heatmap_dir)
                self._create_metric_analysis_plots(results_df, metric, analysis_dir)
                self._create_metric_distribution_plots(results_df, metric, dist_dir)
            except Exception as e:
                self.logger.error(f"Error creating plots for {metric}: {str(e)}")

    def _create_metric_heatmap(self, results_df: pd.DataFrame, metric: str, output_dir: Path):
        """Create detailed heatmap for metric"""
        try:
            plt.figure(figsize=(12, 10))
            
            # Convert to numeric and sort
            results_df = results_df.copy()
            results_df['noise_std'] = pd.to_numeric(results_df['noise_std'])
            results_df['control_strength'] = pd.to_numeric(results_df['control_strength'])
            
            # Calculate means and standard deviations
            mean_df = results_df.groupby(['noise_std', 'control_strength'])[metric].mean()
            std_df = results_df.groupby(['noise_std', 'control_strength'])[metric].std()
            
            # Get unique sorted values for axes
            noise_levels = sorted(results_df['noise_std'].unique())
            control_levels = sorted(results_df['control_strength'].unique())
            
            # Create 2D arrays for heatmap
            heatmap_data = np.zeros((len(noise_levels), len(control_levels)))
            std_data = np.zeros((len(noise_levels), len(control_levels)))
            
            # Fill arrays
            for i, noise in enumerate(noise_levels):
                for j, control in enumerate(control_levels):
                    idx = (noise, control)
                    if idx in mean_df.index:
                        heatmap_data[i, j] = mean_df[idx]
                        std_data[i, j] = std_df[idx]
            
            # Create heatmap
            ax = sns.heatmap(
                heatmap_data,
                annot=True,
                fmt='.3f',
                cmap='viridis',
                xticklabels=[f'{x:.3f}' for x in control_levels],
                yticklabels=[f'{x:.3f}' for x in noise_levels],
                cbar_kws={'label': f'{metric.replace("_", " ").title()} (Mean)'}
            )
            
            # Add std values
            for i in range(len(noise_levels)):
                for j in range(len(control_levels)):
                    if not np.isnan(std_data[i, j]):
                        plt.text(
                            j + 0.5, i + 0.7,
                            f'±{std_data[i,j]:.3f}',
                            ha='center', va='center',
                            color='white', fontsize=8
                        )
            
            # Improve labels and title
            plt.title(f'{metric.replace("_", " ").title()} vs Noise and Control\n'
                     f'Mean ± Std across {len(results_df)} simulations',
                     pad=20)
            plt.xlabel('Control Strength (log scale)')
            plt.ylabel('Noise Standard Deviation (log scale)')
            
            # Rotate axis labels
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            
            # Save plot
            plt.tight_layout()
            plot_path = output_dir / f"{metric}_heatmap.png"
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            
            # Save data
            data_df = pd.DataFrame(
                heatmap_data,
                index=noise_levels,
                columns=control_levels
            )
            data_df.to_csv(output_dir / f"{metric}_data.csv")
            
            self.logger.info(f"Saved heatmap for {metric} to {plot_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating heatmap for {metric}: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _create_metric_line_plots(self, results_df: pd.DataFrame, metric: str, output_dir: Path):
        """Create line plots showing metric trends"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
            
            # Convert to numeric
            results_df = results_df.copy()
            results_df['noise_std'] = pd.to_numeric(results_df['noise_std'])
            results_df['control_strength'] = pd.to_numeric(results_df['control_strength'])
            
            # Plot vs noise for different control values
            for control in sorted(results_df['control_strength'].unique()):
                mask = results_df['control_strength'] == control
                data = results_df[mask].groupby('noise_std').agg({
                    metric: ['mean', 'std']
                })
                
                ax1.errorbar(
                    data.index,
                    data[metric]['mean'],
                    yerr=data[metric]['std'],
                    label=f'Control={control:.3f}',
                    marker='o',
                    capsize=5
                )
            
            ax1.set_xscale('log')
            ax1.set_xlabel('Noise Standard Deviation')
            ax1.set_ylabel(metric.replace('_', ' ').title())
            ax1.set_title(f'{metric.title()} vs Noise\nfor different Control values')
            ax1.grid(True, which="both", ls="-", alpha=0.2)
            ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Plot vs control for different noise values
            for noise in sorted(results_df['noise_std'].unique()):
                mask = results_df['noise_std'] == noise
                data = results_df[mask].groupby('control_strength').agg({
                    metric: ['mean', 'std']
                })
                
                ax2.errorbar(
                    data.index,
                    data[metric]['mean'],
                    yerr=data[metric]['std'],
                    label=f'Noise={noise:.3f}',
                    marker='o',
                    capsize=5
                )
            
            ax2.set_xscale('log')
            ax2.set_xlabel('Control Strength')
            ax2.set_ylabel(metric.replace('_', ' ').title())
            ax2.set_title(f'{metric.title()} vs Control\nfor different Noise values')
            ax2.grid(True, which="both", ls="-", alpha=0.2)
            ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            plt.tight_layout()
            plot_path = output_dir / f"{metric}_analysis.png"
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            
        except Exception as e:
            self.logger.error(f"Error creating line plots for {metric}: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _create_metric_analysis_plots(self, results_df: pd.DataFrame, metric: str, output_dir: Path):
        """Create detailed analysis plots for metric"""
        plt.figure(figsize=(20, 8))
        
        # Plot vs noise with error bars
        plt.subplot(1, 2, 1)
        for control in results_df['control_strength'].unique():
            mask = results_df['control_strength'] == control
            means = results_df[mask].groupby('noise_std')[metric].mean()
            stds = results_df[mask].groupby('noise_std')[metric].std()
            
            plt.errorbar(means.index, means.values, yerr=stds.values,
                        label=f'Control={control:.3f}', marker='o')
        
        plt.xscale('log')
        plt.xlabel('Noise Standard Deviation')
        plt.ylabel(metric.replace('_', ' ').title())
        plt.title(f'{metric.title()} vs Noise\nwith Error Bars')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True)
        
        # Plot vs control with error bars
        plt.subplot(1, 2, 2)
        for noise in results_df['noise_std'].unique():
            mask = results_df['noise_std'] == noise
            means = results_df[mask].groupby('control_strength')[metric].mean()
            stds = results_df[mask].groupby('control_strength')[metric].std()
            
            plt.errorbar(means.index, means.values, yerr=stds.values,
                        label=f'Noise={noise:.3f}', marker='o')
        
        plt.xscale('log')
        plt.xlabel('Control Strength')
        plt.ylabel(metric.replace('_', ' ').title())
        plt.title(f'{metric.title()} vs Control\nwith Error Bars')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(
            output_dir / f"{metric}_analysis.png",
            bbox_inches='tight',
            dpi=300
        )
        plt.close()

    def _create_metric_distribution_plots(self, results_df: pd.DataFrame, metric: str, output_dir: Path):
        """Create distribution plots for metric"""
        try:
            plt.figure(figsize=(15, 10))
            
            # Convert to numeric and get unique values
            results_df = results_df.copy()
            results_df['noise_std'] = pd.to_numeric(results_df['noise_std'])
            results_df['control_strength'] = pd.to_numeric(results_df['control_strength'])
            
            # Format metric name for display
            metric_display = metric.replace('_', ' ').title()
            
            # Overall distribution
            plt.subplot(2, 2, 1)
            sns.histplot(data=results_df, x=metric, kde=True)
            plt.title(f'Overall Distribution of {metric_display}')
            plt.xlabel(metric_display)
            plt.ylabel('Count')
            
            # Distribution by noise level
            plt.subplot(2, 2, 2)
            sns.boxplot(
                data=results_df,
                x='noise_std',
                y=metric,
                order=sorted(results_df['noise_std'].unique())
            )
            plt.title(f'{metric_display} Distribution by Noise Level')
            plt.xlabel('Noise Standard Deviation')
            plt.ylabel(metric_display)
            plt.xticks(rotation=45)
            
            # Distribution by control strength
            plt.subplot(2, 2, 3)
            sns.boxplot(
                data=results_df,
                x='control_strength',
                y=metric,
                order=sorted(results_df['control_strength'].unique())
            )
            plt.title(f'{metric_display} Distribution by Control Strength')
            plt.xlabel('Control Strength')
            plt.ylabel(metric_display)
            plt.xticks(rotation=45)
            
            # Violin plot of interaction using manual binning
            plt.subplot(2, 2, 4)
            
            # Create manual bins for noise and control
            noise_bins = np.percentile(results_df['noise_std'].unique(), 
                                     np.linspace(0, 100, 6))  # 5 bins
            control_bins = np.percentile(results_df['control_strength'].unique(), 
                                       np.linspace(0, 100, 6))  # 5 bins
            
            # Create bin labels
            results_df['noise_bin'] = pd.cut(
                results_df['noise_std'],
                bins=noise_bins,
                labels=[f'N{i+1}' for i in range(len(noise_bins)-1)],
                include_lowest=True,
                duplicates='drop'
            )
            
            results_df['control_bin'] = pd.cut(
                results_df['control_strength'],
                bins=control_bins,
                labels=[f'C{i+1}' for i in range(len(control_bins)-1)],
                include_lowest=True,
                duplicates='drop'
            )
            
            # Create violin plot
            sns.violinplot(
                data=results_df,
                x='noise_bin',
                y=metric,
                hue='control_bin'
            )
            plt.title(f'{metric_display} Distribution by Parameters')
            plt.xlabel('Noise Level Bins')
            plt.ylabel(metric_display)
            plt.xticks(rotation=45)
            
            # Adjust layout and save
            plt.tight_layout()
            plot_path = output_dir / f"{metric}_distributions.png"
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            
            # Save binning information for reference
            bin_info = {
                'noise_bins': noise_bins.tolist(),
                'control_bins': control_bins.tolist(),
                'noise_labels': [f'N{i+1}' for i in range(len(noise_bins)-1)],
                'control_labels': [f'C{i+1}' for i in range(len(control_bins)-1)]
            }
            
            with open(output_dir / f"{metric}_bin_info.json", 'w') as f:
                json.dump(bin_info, f, indent=2)
            
            self.logger.info(f"Saved distribution plots for {metric} to {plot_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating distribution plots for {metric}: {str(e)}")
            self.logger.error(traceback.format_exc())

    def generate_final_report(self, results_df: pd.DataFrame):
        """Generate comprehensive analysis report"""
        report_path = self.output_dir / "sweep_analysis_report.txt"
        
        with open(report_path, 'w') as f:
            f.write("Active Inference Parameter Sweep Analysis Report\n")
            f.write("=" * 50 + "\n\n")
            
            # Simulation parameters
            f.write("Simulation Parameters:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Noise range: {self.noise_range[0]:.3f} to {self.noise_range[-1]:.3f}\n")
            f.write(f"Control range: {self.control_range[0]:.3f} to {self.control_range[-1]:.3f}\n")
            f.write(f"Number of noise levels: {len(self.noise_range)}\n")
            f.write(f"Number of control levels: {len(self.control_range)}\n")
            f.write(f"Total parameter combinations: {len(self.noise_range) * len(self.control_range)}\n")
            f.write(f"Repeats per combination: {NUM_REPEATS}\n")
            f.write(f"Timesteps per simulation: {self.n_timesteps}\n")
            f.write(f"Output directory: {self.output_dir}\n\n")
            
            # Overall statistics
            f.write("Overall Performance:\n")
            f.write("-" * 20 + "\n")
            for metric in ['satisfaction_rate', 'control_effectiveness', 'runtime']:
                mean = results_df[metric].mean()
                std = results_df[metric].std()
                min_val = results_df[metric].min()
                max_val = results_df[metric].max()
                
                f.write(f"\n{metric.replace('_', ' ').title()}:\n")
                f.write(f"  Mean ± Std: {mean:.3f} ± {std:.3f}\n")
                f.write(f"  Range: [{min_val:.3f}, {max_val:.3f}]\n")
            
            # Best parameter combinations
            f.write("\nOptimal Parameter Combinations:\n")
            f.write("-" * 20 + "\n")
            
            for metric in ['satisfaction_rate', 'control_effectiveness']:
                best_idx = results_df.groupby(
                    ['noise_std', 'control_strength']
                )[metric].mean().idxmax()
                
                best_val = results_df.groupby(
                    ['noise_std', 'control_strength']
                )[metric].mean().max()
                
                f.write(f"\nBest for {metric.replace('_', ' ').title()}:\n")
                f.write(f"  Noise: {best_idx[0]:.3f}\n")
                f.write(f"  Control: {best_idx[1]:.3f}\n")
                f.write(f"  Value: {best_val:.3f}\n")

def main():
    """Run noise and control parameter sweep analysis"""
    try:
        sweep = NoiseControlSweepAnalysis()
        sweep.logger.info("Starting parameter sweep analysis...")
        
        results = sweep.run_parameter_sweep(n_repeats=NUM_REPEATS)
        
        if not results.empty:
            sweep.logger.info("\nSweep Analysis Complete!")
            sweep.logger.info(f"Results saved to: {sweep.output_dir}")
            
            # Print summary statistics
            sweep.logger.info("\nOverall Results:")
            for metric in ['satisfaction_rate', 'control_effectiveness', 'runtime']:
                mean_val = results[metric].mean()
                std_val = results[metric].std()
                sweep.logger.info(f"{metric}: {mean_val:.3f} ± {std_val:.3f}")
        else:
            sweep.logger.error("Sweep analysis failed to collect valid results")
        
    except Exception as e:
        logging.error(f"Error in sweep analysis: {str(e)}")
        logging.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
