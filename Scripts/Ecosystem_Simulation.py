import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Union
import json
import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import sys
import logging
import traceback
import matplotlib.pyplot as plt

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Now import using the correct path
from utils.logging_utils import setup_logging
from utils.config_loader import load_ecosystem_config
from Scripts.Visualization_Methods import plot_data, plot_comparison, plot_satisfaction_rates, generate_all_visualizations
from Scripts.Biofirm_Agent import BiofirmAgent

# Simulation Parameters
SIMULATION_PARAMS = {
    'num_timesteps': 200,
    'control_modes': ['random', 'active_inference'],
    'default_control_strategy': 'active_inference',
    'output_interval': 50,
    'control_bounds': {
        'min_adjustment': -5.0,
        'max_adjustment': 5.0
    },
    'visualization': {
        'show_plots': True,
        'save_plots': True
    }
}

@dataclass
class EnvironmentState:
    """Dataclass to capture complete environment state for serialization"""
    timestamp: str
    timestep: int
    variables: Dict[str, float]
    constraints: Dict[str, Dict[str, float]]
    constraint_verification: List[int]
    controllable_variables: List[str]
    metadata: Dict[str, Any]  # New field for additional metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary with added metadata"""
        return {
            **asdict(self),
            'satisfied_constraints': sum(self.constraint_verification),
            'total_constraints': len(self.constraint_verification),
            'satisfaction_rate': sum(self.constraint_verification) / len(self.constraint_verification)
        }

class Environment:
    """
    Simulates a natural resource environment with interdependent variables that evolve over time.
    Tracks both actual variable values and whether they fall within specified constraints.
    """
    
    # Class-level default settings
    DEFAULT_OUTPUT_DIR = "Outputs"
    DEFAULT_RANDOM_SEED = 77
    
    def __init__(self, 
                 output_dir: Optional[str] = None, 
                 random_seed: Optional[int] = None,
                 config_path: Optional[str] = None):
        """
        Initialize environment with configuration and simulation settings
        
        Args:
            output_dir: Directory for output files (default: "Outputs")
            random_seed: Random seed for reproducibility (default: 77)
            config_path: Path to ecosystem configuration file (optional)
        """
        # Set simulation settings
        self.output_dir = Path(output_dir or self.DEFAULT_OUTPUT_DIR)
        self.random_seed = random_seed if random_seed is not None else self.DEFAULT_RANDOM_SEED
        self.simulation_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.output_dir / 'states'
        self.state_dir.mkdir(exist_ok=True)
        
        # Initialize file paths
        self.history_file = self.output_dir / f'environment_history_{self.simulation_id}.json'
        self.metrics_file = self.output_dir / f'metrics_{self.simulation_id}.json'
        
        # Setup enhanced logging
        self.logger = setup_logging(self.simulation_id, self.output_dir)
        self.logger.info(f"Initializing environment simulation {self.simulation_id}")
        
        try:
            # Set random seed
            np.random.seed(self.random_seed)
            self.logger.info(f"Set random seed: {self.random_seed}")
            
            # Load ecosystem configuration
            self.config = load_ecosystem_config(config_path)
            self.logger.info("Successfully loaded ecosystem configuration")
            
            # Initialize from config
            self._init_from_config()
            self._init_tracking_system()
            self._save_state()
            
            self._log_simulation_settings()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize environment: {str(e)}\n{traceback.format_exc()}")
            raise

    def _log_simulation_settings(self):
        """Log simulation settings"""
        # Detailed logging to file
        self.logger.info("\nSimulation Settings:")
        self.logger.info(f"  Output Directory: {self.output_dir}")
        self.logger.info(f"  Random Seed: {self.random_seed}")
        self.logger.info(f"  History File: {self.history_file}")
        self.logger.info(f"  State Directory: {self.state_dir}")
        self.logger.info(f"  Metrics File: {self.metrics_file}")
        
        # Simplified console output
        print(f"\nInitializing Simulation {self.simulation_id}")
        print(f"Output Directory: {self.output_dir}")

    @classmethod
    def with_settings(cls, 
                     output_dir: str = None,
                     random_seed: int = None,
                     config_path: str = None) -> 'Environment':
        """
        Create environment instance with custom settings
        
        Args:
            output_dir: Custom output directory
            random_seed: Custom random seed
            config_path: Custom config path
            
        Returns:
            Configured Environment instance
        """
        return cls(
            output_dir=output_dir,
            random_seed=random_seed,
            config_path=config_path
        )

    def _init_from_config(self):
        """Initialize variables from configuration file"""
        self.logger.info("\nInitializing Environmental Variables from Config:")
        
        try:
            # Initialize variables from config
            for var_name, var_config in self.config['variables'].items():
                setattr(self, var_name, var_config['initial_value'])
                self.logger.info(
                    f"  {var_name:25}: {var_config['initial_value']:6.2f} "
                    f"{var_config.get('unit', '')}"
                )
            
            # Set controllable variables
            self.controllable_variables_list = [
                var_name for var_name, var_config in self.config['variables'].items()
                if var_config.get('controllable', False)
            ]
            
            self.logger.info("\nControllable Variables:")
            for var in self.controllable_variables_list:
                self.logger.info(
                    f"  - {var} ({self.config['variables'][var].get('unit', '')})"
                )
                
        except KeyError as e:
            self.logger.error(f"Missing required configuration key: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing from config: {e}")
            raise

    def _init_tracking_system(self):
        """Initialize tracking system from configuration"""
        self.logger.info("\nInitializing Tracking System:")
        
        # Get variable names from config
        self.variable_names = list(self.config['variables'].keys())
        
        # Initialize empty DataFrame for tracking history
        self.data = pd.DataFrame(columns=['timestep'] + self.variable_names)
        
        # Initialize constraints DataFrame
        self.logger.info("\nSetting Constraints:")
        constraints_data = {
            'variable': self.variable_names,
            'lower_constraint': [self.config['variables'][var]['constraints']['lower'] 
                               for var in self.variable_names],
            'upper_constraint': [self.config['variables'][var]['constraints']['upper'] 
                               for var in self.variable_names]
        }
        
        self.constraints = pd.DataFrame(constraints_data)
        
        for var_name in self.variable_names:
            var_config = self.config['variables'][var_name]
            self.logger.info(
                f"  {var_name:25}: [{var_config['constraints']['lower']:3.0f}, "
                f"{var_config['constraints']['upper']:3.0f}] {var_config['unit']}"
            )
        
        # Initialize constraint verification
        self.constraint_verification = self._verify_constraints()

    def step(self, controllable_health: float, controllable_carbon: float, 
            controllable_buffer: float) -> Tuple[List[int], pd.DataFrame]:
        """Streamlined step function with minimal logging"""
        try:
            # Convert numpy values to Python floats
            health_adj = float(controllable_health)
            carbon_adj = float(controllable_carbon)
            buffer_adj = float(controllable_buffer)
            
            # Execute step logic
            self._update_controllable_variables(health_adj, carbon_adj, buffer_adj)
            self._update_dependent_variables()
            self._record_state()
            self.constraint_verification = self._verify_constraints()
            
            return self.constraint_verification, self.data
            
        except Exception as e:
            self.logger.error(f"Step error: {e}")
            raise

    def _update_controllable_variables(self, health: float, carbon: float, buffer: float):
        """Update controllable variables with validation"""
        updates = {
            'forest_health': (health, self.forest_health),
            'carbon_sequestration': (carbon, self.carbon_sequestration),
            'riparian_buffer_width': (buffer, self.riparian_buffer_width)
        }
        
        for var_name, (adjustment, current) in updates.items():
            new_value = np.clip(current + adjustment, 0, 100)
            setattr(self, var_name, new_value)
            self.logger.debug(
                f"{var_name}: {current:.2f} -> {new_value:.2f} "
                f"(adjustment: {adjustment:+.2f})"
            )

    def _log_state_changes(self, previous_state: Dict[str, float]):
        """Enhanced logging of state variable changes"""
        changes = []
        significant_changes = []
        
        for var in self.variable_names:
            current = getattr(self, var)
            prev = previous_state[var]
            delta = current - prev
            
            if abs(delta) > 0.01:  # Log significant changes only
                change_str = (
                    f"{var.replace('_', ' ').title():25}: "
                    f"{prev:6.2f} → {current:6.2f} ({delta:+.2f})"
                )
                changes.append(change_str)
                
                # Track major changes (>10% change)
                if abs(delta) > (prev * 0.1):
                    significant_changes.append(var)
        
        if changes:
            self.logger.info("\nState Changes:")
            self.logger.info("\n  - " + "\n  - ".join(changes))
            if significant_changes:
                self.logger.warning(
                    f"\nSignificant Changes Detected in: {', '.join(significant_changes)}"
                )

    def _save_detailed_state(self, step_number: int, step_start: datetime):
        """Save detailed state information to JSON"""
        state = self._get_current_state()
        state.metadata = {
            'step_duration': (datetime.now() - step_start).total_seconds(),
            'simulation_id': self.simulation_id,
            'step_number': step_number,
            'control_strategy': self.control_strategy
        }
        
        # Save state to JSON file
        state_file = self.state_dir / f'state_{self.simulation_id}_{step_number:04d}.json'
        try:
            with open(state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
            self.logger.debug(f"Detailed state saved to {state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save detailed state: {str(e)}")

    def _update_dependent_variables(self):
        """Update all dependent variables based on current state and random factors"""
        self.logger.info("\nUpdating Dependent Variables:")
        
        # Store previous values
        previous = {var: getattr(self, var) for var in self.variable_names}
        
        # Update variables with logging
        updates = [
            ('wildlife_habitat_quality', 
             lambda: np.clip(self.forest_health * 0.5 + np.random.normal(0, 5), 0, 100)),
            ('water_quality',
             lambda: np.clip(self.riparian_buffer_width * 1.5 + np.random.normal(0, 5), 0, 100)),
            ('soil_health',
             lambda: np.clip(self.forest_health * 0.6 + np.random.normal(0, 5), 0, 100)),
            ('invasive_species_count',
             lambda: int(np.clip(self.invasive_species_count - self.riparian_buffer_width/10 + 
                               np.random.randint(-5, 5), 0, None))),
            ('biodiversity_index',
             lambda: np.clip(self.wildlife_habitat_quality * 0.4 + np.random.normal(0, 5), 0, 100)),
            ('hazard_trees_count',
             lambda: int(np.clip(self.hazard_trees_count + np.random.randint(-2, 3), 0, None))),
            ('recreational_access_score',
             lambda: np.clip(self.recreational_access_score + np.random.randint(-3, 3), 0, 100))
        ]
        
        for var_name, update_func in updates:
            old_value = previous[var_name]
            new_value = update_func()
            setattr(self, var_name, new_value)
            delta = new_value - old_value
            self.logger.info(
                f"  {var_name:25}: {old_value:6.2f} → {new_value:6.2f} "
                f"({delta:+.2f})"
            )

    def _record_state(self):
        """Record current state to historical data and save to JSON"""
        # Record to DataFrame with explicit dtypes
        new_data = pd.DataFrame({
            'timestep': [len(self.data)],
            **{var: [float(getattr(self, var))] for var in self.variable_names}
        })
        
        # Ensure consistent dtypes during concatenation
        if len(self.data) == 0:
            self.data = new_data
        else:
            self.data = pd.concat([self.data, new_data], ignore_index=True)
        
        # Save detailed state to JSON history
        state = self._get_current_state()
        state.metadata.update({
            'step_number': len(self.data) - 1,
            'timestamp': datetime.now().isoformat(),
            'constraint_status': {
                var: (1 if self.constraint_verification[i] else 0)
                for i, var in enumerate(self.variable_names)
            }
        })
        
        try:
            # Load existing history or create new
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Append new state
            history.append(state.to_dict())
            
            # Save updated history
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save state history: {str(e)}")
            raise

    def _verify_constraints(self) -> List[int]:
        """
        Verify if each variable is within constraints, returning LOW (0), HOMEOSTATIC (1), or HIGH (2)
        
        Returns:
            List of state indicators (0: LOW, 1: HOMEOSTATIC, 2: HIGH)
        """
        states = []
        for name in self.variable_names:
            value = getattr(self, name)
            constraints = self.constraints[self.constraints['variable'] == name].iloc[0]
            lower = constraints['lower_constraint']
            upper = constraints['upper_constraint']
            homeostatic_center = (lower + upper) / 2
            homeostatic_range = (upper - lower) * 1  # can have a homeostatic zone within the constraints
            
            if value < lower:
                states.append(0)  # LOW
            elif value > upper:
                states.append(2)  # HIGH
            else:
                # Check if in homeostatic range around center
                if abs(value - homeostatic_center) <= homeostatic_range:
                    states.append(1)  # HOMEOSTATIC
                elif value < homeostatic_center:
                    states.append(0)  # LOW side of valid range
                else:
                    states.append(2)  # HIGH side of valid range
        
        return states

    def print_state(self):
        """Print current environmental state with enhanced details"""
        state_lines = [
            "\n=== Environmental State Report ===",
            f"Simulation ID: {self.simulation_id}",
            f"Timestep: {len(self.data) - 1}",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-" * 75,
            "Variable Status:",
            "-" * 75
        ]
        
        # Track constraint satisfaction for summary
        satisfied_constraints = 0
        critical_variables = []
        
        for var in self.variable_names:
            value = getattr(self, var)
            constraints = self.constraints[self.constraints['variable'] == var].iloc[0]
            is_satisfied = self.constraint_verification[self.variable_names.index(var)]
            status = "✓" if is_satisfied else "⚠"
            
            # Track satisfaction
            if is_satisfied:
                satisfied_constraints += 1
            else:
                critical_variables.append(var)
            
            # Add control indicator
            control_indicator = "[C]" if var in self.controllable_variables_list else "   "
            
            state_lines.append(
                f"{control_indicator} {var.replace('_', ' ').title():25} = {value:6.2f} "
                f"[{constraints['lower_constraint']:3.0f}, {constraints['upper_constraint']:3.0f}] {status}"
            )
        
        # Add summary section
        satisfaction_rate = (satisfied_constraints / len(self.variable_names)) * 100
        state_lines.extend([
            "-" * 75,
            "Summary:",
            f"Constraint Satisfaction: {satisfied_constraints}/{len(self.variable_names)} ({satisfaction_rate:.1f}%)",
            f"Variables Needing Attention: {', '.join(critical_variables) if critical_variables else 'None'}",
            "Legend: [C] = Controllable Variable, ✓ = Within Constraints, ⚠ = Outside Constraints",
            "=" * 75
        ])
        
        # Print to console and log
        print("\n".join(state_lines))
        self.logger.info("\n".join(state_lines))

    def _get_current_state(self) -> EnvironmentState:
        """Capture current environment state in serializable format"""
        return EnvironmentState(
            timestamp=datetime.now().isoformat(),
            timestep=len(self.data) - 1,
            variables={var: float(getattr(self, var)) for var in self.variable_names},
            constraints={
                row['variable']: {
                    'lower': float(row['lower_constraint']),
                    'upper': float(row['upper_constraint'])
                }
                for _, row in self.constraints.iterrows()
            },
            constraint_verification=self.constraint_verification,
            controllable_variables=self.controllable_variables_list,
            metadata={}
        )

    def _save_state(self) -> None:
        """Save current state to JSON history file"""
        state = self._get_current_state()
        
        try:
            # Load existing history or create new
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
                
            # Append new state
            history.append(asdict(state))
            
            # Save updated history
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
            self.logger.debug(f"State saved to {self.history_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {str(e)}")
            raise

    def get_simulation_summary(self) -> Dict[str, Any]:
        """Generate summary statistics for the simulation"""
        return {
            'simulation_id': self.simulation_id,
            'total_timesteps': len(self.data),
            'final_state': asdict(self._get_current_state()),
            'variable_descriptions': VARIABLE_DESCRIPTIONS,
            'history_file': str(self.history_file)
        }

    def run_simulation(self, 
                      num_timesteps: int = SIMULATION_PARAMS['num_timesteps'],
                      control_strategy: str = SIMULATION_PARAMS['default_control_strategy']) -> pd.DataFrame:
        """Run simulation with enhanced visualization and safety checks"""
        self.logger.info(f"\nStarting {num_timesteps}-step simulation with {control_strategy} control")
        self.control_strategy = control_strategy
        
        try:
            # Initialize agent if using active inference
            agent = None
            if control_strategy == 'active_inference':
                agent = BiofirmAgent(num_variables=len(self.variable_names))
                self.logger.info("Initialized BiofirmAgent")
            
            # Initialize metrics tracking
            metrics = self._init_simulation_metrics(control_strategy, num_timesteps)
            
            # Run simulation steps
            for step in range(num_timesteps):
                step_start = datetime.now()
                try:
                    # Generate and execute control actions
                    controls = self._get_control_actions(control_strategy, agent)
                    verification, _ = self.step(
                        controllable_health=controls['health'],
                        controllable_carbon=controls['carbon'],
                        controllable_buffer=controls['buffer']
                    )
                    
                    # Update agent if using active inference
                    if agent:
                        agent.update_beliefs(verification)
                    
                    # Save detailed state every 50 steps and at start/end
                    if step == 0 or step == num_timesteps-1 or step % 50 == 0:
                        self._save_detailed_state(step, step_start)
                    
                    # Record metrics
                    self._record_step_metrics(metrics, step, controls, verification)
                    
                    # Only log at start, end, and major intervals
                    if step == 0 or step == num_timesteps-1 or step % (num_timesteps//10) == 0:
                        satisfaction_rate = sum(verification) / len(verification) * 100
                        self.logger.info(
                            f"Step {step+1}/{num_timesteps} - "
                            f"Satisfaction Rate: {satisfaction_rate:.1f}%"
                        )
                        
                except Exception as e:
                    self.logger.error(f"Error in step {step}: {e}")
                    raise
            
            # Save final metrics
            self._save_simulation_metrics(metrics)
            self.logger.info(f"Completed {control_strategy} simulation")
            
            return self.data
            
        except Exception as e:
            self.logger.error(f"Simulation failed: {e}")
            raise

    def run_comparison(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Run both random and active inference simulations and generate comparison visualizations"""
        self.logger.info("\nStarting simulation comparison...")
        
        try:
            # Run both strategies
            self.logger.info("Running random control simulation...")
            random_data = self.run_simulation(control_strategy='random')
            
            self.logger.info("\nRunning active inference simulation...")
            active_data = self.run_simulation(control_strategy='active_inference')
            
            # Generate all visualizations
            self.logger.info("\nGenerating visualizations...")
            success = generate_all_visualizations(
                random_data=random_data,
                active_data=active_data,
                constraints=self.constraints,
                controllable_vars=self.controllable_variables_list,
                output_dir=self.output_dir,
                logger=self.logger
            )
            
            if success:
                self.logger.info(f"\nAll visualizations saved to: {self.output_dir}/visualizations")
            else:
                self.logger.warning("Some visualizations may not have been generated successfully")
                
            return random_data, active_data
            
        except Exception as e:
            self.logger.error(f"Comparison failed: {e}")
            plt.close('all')
            raise

    def _get_control_actions(self, strategy: str, agent: Optional[BiofirmAgent]) -> Dict[str, float]:
        """Get control actions based on strategy"""
        if strategy == 'random':
            return self._generate_random_controls()
        elif strategy == 'active_inference':
            if not agent:
                raise ValueError("Agent not initialized for active inference")
            return agent.get_action(self.constraint_verification)
        else:
            raise ValueError(f"Unknown control strategy: {strategy}")

    def _generate_visualizations(self):
        """Generate and save visualization plots without display"""
        try:
            self.logger.info("\nGenerating visualization plots...")
            
            # Create plots using Visualization_Methods
            plot_data(self.data, self.constraints, self.controllable_variables_list, 
                     self.control_strategy, self.output_dir)
            
            self.logger.info(f"Plots saved to {self.output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error generating visualizations: {e}")
            self.logger.warning("Continuing simulation without visualizations")

    def _print_progress(self, step: int, total_steps: int, verification: List[int]):
        """Print simulation progress with metrics"""
        satisfaction_rate = sum(verification) / len(verification) * 100
        self.logger.info(
            f"Step {step+1}/{total_steps} - "
            f"Constraint Satisfaction: {satisfaction_rate:.1f}%"
        )

    def _init_simulation_metrics(self, control_strategy: str, num_timesteps: int) -> Dict:
        """Initialize metrics tracking dictionary"""
        return {
            'simulation_id': self.simulation_id,
            'start_time': datetime.now().isoformat(),
            'control_strategy': control_strategy,
            'num_timesteps': num_timesteps,
            'config_path': str(self.config),
            'timesteps': []
        }

    def _generate_random_controls(self) -> Dict[str, float]:
        """Generate random control actions within bounds"""
        bounds = SIMULATION_PARAMS['control_bounds']
        return {
            'health': np.random.uniform(bounds['min_adjustment'], bounds['max_adjustment']),
            'carbon': np.random.uniform(bounds['min_adjustment'], bounds['max_adjustment']),
            'buffer': np.random.uniform(bounds['min_adjustment'], bounds['max_adjustment'])
        }

    def _record_step_metrics(self, metrics: Dict, step: int, controls: Dict[str, float], verification: List[int]):
        """Record metrics for current simulation step with 3-state verification"""
        try:
            # Get current state
            current_state = {var: float(getattr(self, var)) for var in self.variable_names}
            
            # Calculate satisfaction rate (count HOMEOSTATIC states)
            homeostatic = sum(1 for state in verification if state == 1)
            total = len(verification)
            satisfaction_rate = (homeostatic / total) * 100
            
            # Record step metrics
            step_metrics = {
                'step_number': step,
                'timestamp': datetime.now().isoformat(),
                'controls': {
                    'health': float(controls['health']),
                    'carbon': float(controls['carbon']),
                    'buffer': float(controls['buffer'])
                },
                'variables': current_state,
                'states': {
                    var: ('LOW' if verification[i] == 0 else 
                          'HOMEOSTATIC' if verification[i] == 1 else 'HIGH')
                    for i, var in enumerate(self.variable_names)
                },
                'homeostatic_rate': satisfaction_rate
            }
            
            # Append to metrics
            metrics['timesteps'].append(step_metrics)
            
        except Exception as e:
            self.logger.error(f"Error recording step metrics: {e}")
            raise

    def _save_simulation_metrics(self, metrics: Dict):
        """Save simulation metrics to file"""
        try:
            # Add final metrics
            metrics.update({
                'end_time': datetime.now().isoformat(),
                'final_state': self._get_current_state().to_dict(),
                'final_satisfaction_rate': sum(self.constraint_verification) / len(self.constraint_verification)
            })
            
            # Save to file
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
                
            self.logger.info(f"Simulation metrics saved to {self.metrics_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving simulation metrics: {e}")
            raise

def initialize_environment(
    output_dir: Optional[str] = None,
    random_seed: Optional[int] = None,
    config_path: Optional[str] = None
) -> Environment:
    """
    Initialize and return a new environment instance with optional custom settings
    
    Args:
        output_dir: Custom output directory
        random_seed: Custom random seed
        config_path: Custom config path
        
    Returns:
        Configured Environment instance
    """
    return Environment.with_settings(
        output_dir=output_dir,
        random_seed=random_seed,
        config_path=config_path
    )

# Variable descriptions for documentation
VARIABLE_DESCRIPTIONS: Dict[str, str] = {
    'forest_health': "Forest health index (0-100). Target: 50-100. Measures overall forest ecosystem health.",
    'carbon_sequestration': "Carbon storage (tons/acre). Target: 30-100. Amount of carbon captured by forest.",
    'wildlife_habitat_quality': "Habitat quality (0-100). Target: 50-100. Suitability for wildlife.",
    'water_quality': "Water quality index (0-100). Target: 70-100. Water cleanliness and health.",
    'soil_health': "Soil health index (0-100). Target: 60-100. Soil quality and sustainability.",
    'invasive_species_count': "Invasive species count. Target: 0-50. Number of unwanted species.",
    'riparian_buffer_width': "Buffer width (feet). Target: 25-100. Width of waterway protection zone.",
    'biodiversity_index': "Biodiversity score (0-100). Target: 60-100. Species variety measure.",
    'hazard_trees_count': "Hazard tree count. Target: 0-15. Number of risk-posing trees.",
    'recreational_access_score': "Access quality (0-100). Target: 30-100. Recreational accessibility."
}

# Add main execution
if __name__ == "__main__":
    try:
        # Initialize environment
        env = initialize_environment()
        
        # Run comparison of both strategies
        random_data, active_data = env.run_comparison()
        
        print("\nSimulation complete. Visualizations saved to:", env.output_dir)
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Check logs for details.")
        sys.exit(1)