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
                "controllable": True,  # Required for BiofirmAgent
                # Add POMDP parameters
                "observation_confidence": 0.90,
                "homeostatic_preference": 4.0,
                "state_transition_confidence": 0.85,
                "constraints": {
                    "lower": 45,
                    "upper": 55
                }
            }
        }
    }

class NoiseControlSweepAnalysis:
    def __init__(self):
        """Initialize sweep analysis"""
        # Setup logging - using only component name
        self.logger = get_component_logger('sweep')
        
        # Create sweep directory structure
        self.sweep_dir = Path("Outputs/sweep")
        self.sweep_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped run directory inside sweep
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = self.sweep_dir / f"run_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Add file handler for this specific run
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
        total_combinations = len(self.noise_range) * len(self.control_range) * n_repeats
        completed = 0
        
        # Print sweep configuration
        print("\nStarting Parameter Sweep")
        print("=" * 50)
        print(f"Total Combinations: {len(self.noise_range) * len(self.control_range)}")
        print(f"Repeats per Combination: {n_repeats}")
        print(f"Total Simulations: {total_combinations}")
        print("=" * 50 + "\n")
        
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
            for future in concurrent.futures.as_completed(futures):
                try:
                    metrics = future.result()
                    if metrics:
                        results.append(metrics)
                        
                    # Update progress
                    completed += 1
                    progress = completed / total_combinations * 100
                    
                    # Print progress with current metrics
                    if metrics:
                        print(
                            f"\rProgress: {progress:5.1f}% | "
                            f"N={metrics['noise_std']:.2f} C={metrics['control_strength']:.2f} | "
                            f"SR={metrics.get('satisfaction_rate', 0):5.1f}% "
                            f"CE={metrics.get('control_effort', 0):5.2f}",
                            end="", flush=True
                        )
                    else:
                        print(f"\rProgress: {progress:5.1f}%", end="", flush=True)
                    
                except Exception as e:
                    self.logger.error(f"Error in simulation: {str(e)}")
                    self.logger.error(traceback.format_exc())
        
        print("\n\nParameter sweep complete!")
        
        # Create final results DataFrame
        if results:
            results_df = pd.DataFrame(results)
            self.save_final_results(results_df)
            
            # Log summary statistics
            print("\nSweep Summary:")
            print("-" * 20)
            for metric in ['satisfaction_rate', 'control_effort', 'belief_entropy']:
                mean = results_df[metric].mean()
                std = results_df[metric].std()
                print(f"  • {metric.replace('_', ' ').title()}: {mean:.1f} ± {std:.1f}")
            
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
                
                # Log completion with metrics
                self.logger.info(
                    f"\nCompleted N={noise_std:.3f}, C={control_strength:.3f}, "
                    f"Repeat {repeat + 1}/{NUM_REPEATS}\n"
                    f"  • Satisfaction Rate: {metrics.get('satisfaction_rate', 0):.1f}%\n"
                    f"  • Control Effort: {metrics.get('control_effort', 0):.2f}\n"
                    f"  • Belief Entropy: {metrics.get('belief_entropy', 0):.2f}"
                )
                
                return metrics
                
        except Exception as e:
            self.logger.error(
                f"Error in combination N={noise_std:.3f}, C={control_strength:.3f}, "
                f"Repeat {repeat}: {str(e)}"
            )
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
                'beliefs': np.array([[1/3, 1/3, 1/3]]),
                'free_energy': []
            }
            
            # Create config and initialize agent
            config = create_sweep_config(noise_std, control_strength)
            agent = BiofirmAgent(config, self.logger)
            
            start_time = time.time()
            
            # Log simulation start
            self.logger.info(
                f"\nStarting Simulation:\n"
                f"  • Noise: {noise_std:.3f}\n"
                f"  • Control: {control_strength:.3f}\n"
                f"  • Repeat: {repeat + 1}/{NUM_REPEATS}"
            )
            
            # Run simulation steps
            for step in range(self.n_timesteps):
                try:
                    # Get discrete observation from current state
                    obs_state = 0 if state < 45 else (2 if state > 55 else 1)
                    observation = {"sweep_var": obs_state}
                    
                    # Get action from agent
                    action_dict = agent.get_action(observation)
                    
                    # Process action and control
                    if action_dict and "sweep_var" in action_dict:
                        control = action_dict["sweep_var"]  # Already scaled by control_strength
                    else:
                        control = 0.0
                    
                    # Add noise and update state
                    noise = np.random.normal(0, noise_std)
                    state = np.clip(state + control + noise, 0.0, 100.0)
                    
                    # Get agent data
                    agent_data = agent.get_agent_data("sweep_var")
                    
                    # Update history
                    history['timesteps'].append(step)
                    history['states'].append(float(state))
                    history['observations'].append(int(obs_state))
                    history['controls'].append(float(control))
                    history['satisfaction'].append(bool(45.0 <= state <= 55.0))
                    
                    # Update beliefs and free energy
                    if agent_data:
                        if 'state_beliefs' in agent_data:
                            beliefs = np.array(agent_data['state_beliefs'][0], dtype=float)
                            history['beliefs'] = np.vstack([history['beliefs'], beliefs])
                        
                        if 'expected_free_energy' in agent_data:
                            history['free_energy'].append(float(agent_data['expected_free_energy'][0]))
                        else:
                            history['free_energy'].append(0.0)
                    
                    # Log progress periodically
                    if step % 25 == 0:
                        satisfaction_rate = np.mean(history['satisfaction']) * 100
                        self.logger.debug(
                            f"Step {step:3d}: State={state:6.2f}, Obs={obs_state}, "
                            f"Control={control:+6.2f}, SR={satisfaction_rate:5.1f}%"
                        )
                        
                except Exception as e:
                    self.logger.error(f"Error in step {step}: {str(e)}")
                    continue
            
            # Calculate metrics
            satisfaction_rate = float(np.mean(history['satisfaction'])) * 100
            control_effort = float(np.mean(np.abs(history['controls'])))
            belief_entropy = float(np.mean([
                -np.sum(b * np.log(b + 1e-10)) for b in history['beliefs']
            ]))
            
            metrics = {
                'noise_std': noise_std,
                'control_strength': control_strength,
                'satisfaction_rate': satisfaction_rate,
                'control_effort': control_effort,
                'belief_entropy': belief_entropy,
                'mean_free_energy': float(np.mean(history['free_energy'])),
                'final_state': history['states'][-1],
                'mean_state': float(np.mean(history['states'])),
                'state_std': float(np.std(history['states']))
            }
            
            # Log simulation results
            self.logger.info(
                f"\nSimulation Complete:\n"
                f"  • Satisfaction Rate: {satisfaction_rate:5.1f}%\n"
                f"  • Control Effort: {control_effort:.3f}\n"
                f"  • Belief Entropy: {belief_entropy:.3f}"
            )
            
            # Save simulation data
            self.save_simulation_history(history, output_dir, repeat)
            
            return metrics
            
        except Exception as e:
            self.logger.error(
                f"Error in simulation (N={noise_std:.3f}, C={control_strength:.3f}, "
                f"R={repeat}):\n  {str(e)}"
            )
            self.logger.debug(traceback.format_exc())
            return None

    def save_simulation_history(self, history: Dict, output_dir: Path, repeat: int):
        """Save simulation history and create visualization subfolder"""
        try:
            # Save raw history data
            history_file = output_dir / f"history_repeat_{repeat}.json"
            with open(history_file, 'w') as f:
                # Convert numpy arrays to lists for JSON serialization
                json_history = {
                    k: [float(x) if isinstance(x, (np.floating, float)) else x 
                        for x in v]
                    for k, v in history.items()
                }
                json.dump(json_history, f, indent=2)
                
            self.logger.info(f"Saved simulation history to {history_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving simulation history: {str(e)}")

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
        print("\nGenerating Final Results and Visualizations...")
        print("=" * 50)
        
        try:
            # Create visualization directories
            viz_dirs = {
                'summary': self.viz_dir / 'summary',
                'comparisons': self.viz_dir / 'comparisons',
                'heatmaps': self.viz_dir / 'heatmaps',
                'distributions': self.viz_dir / 'distributions',
                'analysis': self.viz_dir / 'analysis'
            }
            
            for dir_path in viz_dirs.values():
                dir_path.mkdir(exist_ok=True, parents=True)
            
            # Save raw results
            results_file = self.data_dir / "final_results.csv"
            results_df.to_csv(results_file, index=False)
            print(f"✓ Saved raw results to {results_file}")
            
            # Generate visualizations
            print("\nGenerating Visualization Sets:")
            
            # 1. Parameter Space Overview
            print("\n1. Parameter Space Analysis")
            print("  • Generating heatmap...", end='', flush=True)
            self._create_parameter_space_plot(results_df, viz_dirs['heatmaps'])
            print(" ✓")
            
            # 2. Performance Surface Plots
            print("\n2. Performance Surface Analysis")
            metrics = {
                'satisfaction_rate': 'Satisfaction Rate (%)',
                'control_effort': 'Control Effort',
                'belief_entropy': 'Belief Entropy'
            }
            for metric, title in metrics.items():
                print(f"  • Generating {title} surface...", end='', flush=True)
                self._create_surface_plots(results_df, viz_dirs['analysis'], metric, title)
                print(" ✓")
            
            # 3. Distribution Analysis
            print("\n3. Distribution Analysis")
            print("  • Generating satisfaction distributions...", end='', flush=True)
            self._create_satisfaction_analysis(results_df, viz_dirs['distributions'])
            print(" ✓")
            
            # 4. Interaction Analysis
            print("\n4. Interaction Analysis")
            print("  • Generating noise-control interactions...", end='', flush=True)
            self._create_interaction_analysis(results_df, viz_dirs['analysis'])
            print(" ✓")
            
            # 5. Generate Report
            print("\n5. Analysis Report")
            print("  • Generating comprehensive report...", end='', flush=True)
            self.generate_enhanced_report(results_df)
            print(" ✓")
            
            # Print summary of outputs
            print("\nVisualization Files Generated:")
            for dir_name, dir_path in viz_dirs.items():
                files = list(dir_path.glob('*.png'))
                print(f"\n{dir_name.title()} Visualizations:")
                for file in files:
                    print(f"  • {file.name}")
            
            print("\nAnalysis Files:")
            print(f"  • Results: {results_file}")
            print(f"  • Report:  {self.output_dir / 'sweep_analysis_report.txt'}")
            
        except Exception as e:
            print("\n✗ Error generating visualizations:")
            print(f"  {str(e)}")
            self.logger.error(f"Error in visualization generation: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _create_parameter_space_plot(self, results_df: pd.DataFrame, output_dir: Path):
        """Create enhanced parameter space overview plot"""
        try:
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
            
            # 1. Satisfaction Rate Heatmap
            pivot = results_df.pivot_table(
                values='satisfaction_rate',
                index='noise_std',
                columns='control_strength',
                aggfunc='mean'
            )
            
            sns.heatmap(
                pivot,
                ax=ax1,
                cmap='viridis',
                annot=True,
                fmt='.1f',
                cbar_kws={'label': 'Satisfaction Rate (%)'}
            )
            ax1.set_title('Satisfaction Rate by Parameter Combination')
            ax1.set_xlabel('Control Strength')
            ax1.set_ylabel('Noise Standard Deviation')
            
            # Log optimal regions
            optimal_idx = np.unravel_index(np.argmax(pivot.values), pivot.values.shape)
            optimal_noise = pivot.index[optimal_idx[0]]
            optimal_control = pivot.columns[optimal_idx[1]]
            self.logger.info(
                f"Optimal parameter combination found:\n"
                f"  Noise: {optimal_noise:.3f}\n"
                f"  Control: {optimal_control:.3f}\n"
                f"  Satisfaction Rate: {pivot.values[optimal_idx]:.1f}%"
            )
            
            # 2. Control Effort vs Satisfaction Scatter
            scatter = ax2.scatter(
                results_df['control_effort'],
                results_df['satisfaction_rate'],
                c=results_df['noise_std'],
                s=100 * results_df['control_strength'],
                alpha=0.6,
                cmap='viridis'
            )
            
            # Add colorbar and legend
            cbar = plt.colorbar(scatter, ax=ax2)
            cbar.set_label('Noise Level')
            
            # Add size legend
            legend_elements = [
                plt.scatter([], [], s=100*c, c='gray', alpha=0.6, 
                           label=f'Control={c:.1f}')
                for c in np.linspace(min(results_df['control_strength']), 
                                   max(results_df['control_strength']), 4)
            ]
            ax2.legend(handles=legend_elements, title='Control Strength',
                      bbox_to_anchor=(1.15, 1))
            
            ax2.set_title('Control Effort vs Satisfaction')
            ax2.set_xlabel('Control Effort')
            ax2.set_ylabel('Satisfaction Rate (%)')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plot_path = output_dir / 'parameter_space_overview.png'
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Generated parameter space overview plot: {plot_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating parameter space plot: {str(e)}")
            plt.close('all')

    def _create_surface_plots(self, results_df: pd.DataFrame, output_dir: Path, 
                             metric: str, title: str):
        """Create enhanced 3D surface plots for key metrics"""
        try:
            fig = plt.figure(figsize=(15, 10))
            ax = fig.add_subplot(111, projection='3d')
            
            # Create pivot table for surface
            pivot = results_df.pivot_table(
                values=metric,
                index='noise_std',
                columns='control_strength',
                aggfunc='mean'
            )
            
            X, Y = np.meshgrid(pivot.columns, pivot.index)
            
            # Plot surface with enhanced styling
            surf = ax.plot_surface(
                X, Y, pivot.values,
                cmap='viridis',
                edgecolor='none',
                alpha=0.8,
                antialiased=True
            )
            
            # Add contour projection
            ax.contour(X, Y, pivot.values, zdir='z', 
                      offset=pivot.values.min(), cmap='viridis', alpha=0.5)
            
            # Find optimal point
            optimal_idx = np.unravel_index(np.argmax(pivot.values), pivot.values.shape)
            optimal_control = pivot.columns[optimal_idx[1]]
            optimal_noise = pivot.index[optimal_idx[0]]
            optimal_value = pivot.values[optimal_idx]
            
            # Log optimal point
            self.logger.info(
                f"\nOptimal point for {title}:\n"
                f"  Control: {optimal_control:.3f}\n"
                f"  Noise: {optimal_noise:.3f}\n"
                f"  Value: {optimal_value:.3f}"
            )
            
            # Customize labels and title
            ax.set_xlabel('Control Strength', labelpad=10)
            ax.set_ylabel('Noise Std', labelpad=10)
            ax.set_zlabel(title, labelpad=10)
            
            plt.title(f'{title} Surface\nNoise vs Control Strength', 
                     pad=20, size=14)
            
            # Add colorbar
            fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label=title)
            
            # Adjust view angle for better visualization
            ax.view_init(elev=30, azim=45)
            
            plt.tight_layout()
            plot_path = output_dir / f'{metric}_surface.png'
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Generated surface plot for {metric}: {plot_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating surface plot for {metric}: {str(e)}")

    def _create_satisfaction_analysis(self, results_df: pd.DataFrame, output_dir: Path):
        """Create detailed satisfaction rate analysis"""
        try:
            fig = plt.figure(figsize=(15, 10))
            gs = plt.GridSpec(2, 2)
            
            # 1. Satisfaction Rate Distribution
            ax1 = fig.add_subplot(gs[0, 0])
            sns.histplot(
                data=results_df,
                x='satisfaction_rate',
                bins=20,
                kde=True,
                ax=ax1
            )
            ax1.set_title('Distribution of Satisfaction Rates')
            ax1.set_xlabel('Satisfaction Rate')
            
            # 2. Satisfaction vs Noise
            ax2 = fig.add_subplot(gs[0, 1])
            sns.boxplot(
                data=results_df,
                x=pd.qcut(results_df['noise_std'], q=5),
                y='satisfaction_rate',
                ax=ax2
            )
            ax2.set_title('Satisfaction Rate vs Noise Level')
            ax2.set_xlabel('Noise Level (Quintiles)')
            
            # 3. Satisfaction vs Control
            ax3 = fig.add_subplot(gs[1, 0])
            sns.boxplot(
                data=results_df,
                x=pd.qcut(results_df['control_strength'], q=5),
                y='satisfaction_rate',
                ax=ax3
            )
            ax3.set_title('Satisfaction Rate vs Control Strength')
            ax3.set_xlabel('Control Strength (Quintiles)')
            
            # 4. Satisfaction Rate Heatmap
            ax4 = fig.add_subplot(gs[1, 1])
            pivot = results_df.pivot_table(
                values='satisfaction_rate',
                index=pd.qcut(results_df['noise_std'], q=5),
                columns=pd.qcut(results_df['control_strength'], q=5),
                aggfunc='mean'
            )
            sns.heatmap(
                pivot,
                annot=True,
                fmt='.2f',
                cmap='viridis',
                ax=ax4
            )
            ax4.set_title('Satisfaction Rate Heatmap')
            ax4.set_xlabel('Control Strength (Quintiles)')
            ax4.set_ylabel('Noise Level (Quintiles)')
            
            plt.tight_layout()
            plt.savefig(output_dir / 'satisfaction_analysis.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"Error creating satisfaction analysis: {str(e)}")

    def _create_interaction_analysis(self, results_df: pd.DataFrame, output_dir: Path):
        """Create analysis of noise-control interactions"""
        try:
            fig = plt.figure(figsize=(15, 10))
            gs = plt.GridSpec(2, 2)
            
            # 1. Control Effectiveness
            ax1 = fig.add_subplot(gs[0, 0])
            effectiveness = results_df['satisfaction_rate'] / (results_df['control_effort'] + 1e-10)
            sns.scatterplot(
                data=results_df,
                x='noise_std',
                y='control_strength',
                size='satisfaction_rate',
                hue=effectiveness,
                ax=ax1
            )
            ax1.set_title('Control Effectiveness')
            
            # 2. Optimal Control Strength
            ax2 = fig.add_subplot(gs[0, 1])
            optimal_control = results_df.groupby('noise_std')['satisfaction_rate'].idxmax()
            optimal_points = results_df.loc[optimal_control]
            sns.scatterplot(
                data=optimal_points,
                x='noise_std',
                y='control_strength',
                ax=ax2
            )
            ax2.set_title('Optimal Control Strength per Noise Level')
            
            # 3. Performance Stability
            ax3 = fig.add_subplot(gs[1, 0])
            stability = results_df.groupby(['noise_std', 'control_strength'])['satisfaction_rate'].std().reset_index()
            pivot_stability = stability.pivot(
                index='noise_std',
                columns='control_strength',
                values='satisfaction_rate'
            )
            sns.heatmap(
                pivot_stability,
                cmap='viridis_r',
                ax=ax3,
                cbar_kws={'label': 'Standard Deviation'}
            )
            ax3.set_title('Performance Stability')
            
            # 4. Trade-off Analysis
            ax4 = fig.add_subplot(gs[1, 1])
            sns.scatterplot(
                data=results_df,
                x='control_effort',
                y='satisfaction_rate',
                hue='noise_std',
                size='control_strength',
                ax=ax4
            )
            ax4.set_title('Control Effort vs Satisfaction Trade-off')
            
            plt.tight_layout()
            plt.savefig(output_dir / 'interaction_analysis.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"Error creating interaction analysis: {str(e)}")

    def generate_enhanced_report(self, results_df: pd.DataFrame):
        """Generate comprehensive analysis report with enhanced statistics"""
        report_path = self.output_dir / "sweep_analysis_report.txt"
        
        with open(report_path, 'w') as f:
            f.write("Active Inference Parameter Sweep Analysis Report\n")
            f.write("=" * 50 + "\n\n")
            
            # Simulation Parameters
            f.write("Simulation Parameters:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Noise range: {self.noise_range[0]:.3f} to {self.noise_range[-1]:.3f}\n")
            f.write(f"Control range: {self.control_range[0]:.3f} to {self.control_range[-1]:.3f}\n")
            f.write(f"Total combinations: {len(self.noise_range) * len(self.control_range)}\n")
            f.write(f"Repeats per combination: {NUM_REPEATS}\n\n")
            
            # Overall Performance
            f.write("Overall Performance:\n")
            f.write("-" * 20 + "\n")
            metrics = ['satisfaction_rate', 'control_effort', 'belief_entropy']
            for metric in metrics:
                mean = results_df[metric].mean()
                std = results_df[metric].std()
                min_val = results_df[metric].min()
                max_val = results_df[metric].max()
                f.write(f"\n{metric.replace('_', ' ').title()}:\n")
                f.write(f"  Mean ± Std: {mean:.3f} ± {std:.3f}\n")
                f.write(f"  Range: [{min_val:.3f}, {max_val:.3f}]\n")
            
            # Best Configurations
            f.write("\nOptimal Configurations:\n")
            f.write("-" * 20 + "\n")
            
            # Best for satisfaction rate
            best_satisfaction = results_df.loc[results_df['satisfaction_rate'].idxmax()]
            f.write("\nBest for Satisfaction Rate:\n")
            f.write(f"  Noise: {best_satisfaction['noise_std']:.3f}\n")
            f.write(f"  Control: {best_satisfaction['control_strength']:.3f}\n")
            f.write(f"  Satisfaction Rate: {best_satisfaction['satisfaction_rate']:.3f}%\n")
            
            # Best efficiency (satisfaction/effort ratio)
            results_df['efficiency'] = results_df['satisfaction_rate'] / (results_df['control_effort'] + 1e-10)
            best_efficiency = results_df.loc[results_df['efficiency'].idxmax()]
            f.write("\nBest for Efficiency:\n")
            f.write(f"  Noise: {best_efficiency['noise_std']:.3f}\n")
            f.write(f"  Control: {best_efficiency['control_strength']:.3f}\n")
            f.write(f"  Efficiency: {best_efficiency['efficiency']:.3f}\n")
            
            # Parameter Sensitivity Analysis
            f.write("\nParameter Sensitivity Analysis:\n")
            f.write("-" * 20 + "\n")
            
            # Effect of noise
            noise_effect = results_df.groupby('noise_std')['satisfaction_rate'].mean()
            f.write("\nEffect of Noise Level:\n")
            for noise, satisfaction in noise_effect.items():
                f.write(f"  Noise {noise:.3f}: {satisfaction:.1f}%\n")
            
            # Effect of control strength
            control_effect = results_df.groupby('control_strength')['satisfaction_rate'].mean()
            f.write("\nEffect of Control Strength:\n")
            for control, satisfaction in control_effect.items():
                f.write(f"  Control {control:.3f}: {satisfaction:.1f}%\n")
            
            self.logger.info(f"Generated comprehensive report: {report_path}")

def main():
    """Run noise and control parameter sweep analysis"""
    try:
        print("\nStarting Active Inference Parameter Sweep Analysis")
        print("=" * 50)
        
        # Initialize sweep analysis
        sweep = NoiseControlSweepAnalysis()
        
        # Run parameter sweep
        results_df = sweep.run_parameter_sweep(n_repeats=NUM_REPEATS)
        
        if results_df.empty:
            print("\n✗ Error: No valid results collected")
            return
            
        print("\nGenerating Analysis and Visualizations...")
        print("=" * 50)
        
        # Create visualization directories
        viz_dirs = {
            'summary': sweep.viz_dir / 'summary',
            'comparisons': sweep.viz_dir / 'comparisons',
            'heatmaps': sweep.viz_dir / 'heatmaps',
            'distributions': sweep.viz_dir / 'distributions',
            'analysis': sweep.viz_dir / 'analysis'
        }
        
        for dir_path in viz_dirs.values():
            dir_path.mkdir(exist_ok=True, parents=True)
        
        # 1. Parameter Space Overview
        print("\n1. Parameter Space Analysis")
        print("  • Generating heatmap...", end='', flush=True)
        sweep._create_parameter_space_plot(results_df, viz_dirs['heatmaps'])
        print(" ✓")
        
        # 2. Performance Surface Plots
        print("\n2. Performance Surface Analysis")
        metrics = {
            'satisfaction_rate': 'Satisfaction Rate (%)',
            'control_effort': 'Control Effort',
            'belief_entropy': 'Belief Entropy'
        }
        for metric, title in metrics.items():
            print(f"  • Generating {title} surface...", end='', flush=True)
            sweep._create_surface_plots(results_df, viz_dirs['analysis'], metric, title)
            print(" ✓")
        
        # 3. Distribution Analysis
        print("\n3. Distribution Analysis")
        print("  • Generating satisfaction distributions...", end='', flush=True)
        sweep._create_satisfaction_analysis(results_df, viz_dirs['distributions'])
        print(" ✓")
        
        # 4. Interaction Analysis
        print("\n4. Interaction Analysis")
        print("  • Generating noise-control interactions...", end='', flush=True)
        sweep._create_interaction_analysis(results_df, viz_dirs['analysis'])
        print(" ✓")
        
        # 5. Generate Report
        print("\n5. Analysis Report")
        print("  • Generating comprehensive report...", end='', flush=True)
        sweep.generate_enhanced_report(results_df)
        print(" ✓")
        
        # Print summary of outputs
        print("\nVisualization Files Generated:")
        for dir_name, dir_path in viz_dirs.items():
            files = list(dir_path.glob('*.png'))
            if files:
                print(f"\n{dir_name.title()} Visualizations:")
                for file in files:
                    print(f"  • {file.name}")
        
        print("\nAnalysis Files:")
        print(f"  • Results: {sweep.data_dir}/final_results.csv")
        print(f"  • Report:  {sweep.output_dir}/sweep_analysis_report.txt")
        
        # Print key findings
        print("\nKey Findings:")
        best_config = results_df.loc[results_df['satisfaction_rate'].idxmax()]
        print(f"  • Best Configuration:")
        print(f"    - Noise: {best_config['noise_std']:.3f}")
        print(f"    - Control: {best_config['control_strength']:.3f}")
        print(f"    - Satisfaction Rate: {best_config['satisfaction_rate']:.1f}%")
        
        mean_satisfaction = results_df['satisfaction_rate'].mean()
        std_satisfaction = results_df['satisfaction_rate'].std()
        print(f"\n  • Overall Performance:")
        print(f"    - Mean Satisfaction: {mean_satisfaction:.1f}% ± {std_satisfaction:.1f}%")
        
        print("\nAnalysis Complete! ✓")
        print(f"All outputs saved to: {sweep.output_dir}")
        
    except Exception as e:
        print(f"\n✗ Error in sweep analysis: {str(e)}")
        logging.error(f"Error in sweep analysis: {str(e)}")
        logging.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
