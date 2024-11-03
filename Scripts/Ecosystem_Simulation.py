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

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from utils.config_loader import load_ecosystem_config
from Scripts.Visualization_Methods import generate_all_visualizations
from Scripts.Biofirm_Agent import BiofirmAgent
from Scripts.Free_Energy_Minimization import (
    analyze_active_inference_agents,
    generate_comprehensive_report,
    setup_logging as setup_fe_logging
)
from utils.logging_utils import setup_logging, get_component_logger
from utils.ecosystem_utils import (
    calculate_dependencies,
    get_variable_update_order,
    calculate_base_change,
    apply_variable_relationships,
    calculate_stability_score,
    calculate_response_time,
    verify_constraints
)

# Simulation Parameters
SIMULATION_PARAMS = {
    'num_timesteps': 9000,          # Number of simulation steps
    'progress_interval': 100,       # How often to print progress updates
    'random_seed': 115,            # random seed
    'output_dir': "Outputs",      # Default output directory
    
    # Control parameters
    'control_strategies': ['random', 'active_inference'],
    'control_update_frequency': 1,  # How often to update controls
    
    # Logging parameters
    'log_level': logging.INFO,
    'debug_mode': False           # Enable detailed debugging output
}

@dataclass
class EnvironmentState:
    """Dataclass to capture complete environment state"""
    timestamp: str
    timestep: int
    variables: Dict[str, float]
    constraints: Dict[str, Dict[str, float]]
    constraint_verification: Dict[str, int]  # Maps variable names to states (0,1,2)
    controllable_variables: List[str]
    performance_metrics: Dict[str, float]  # Added performance tracking
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary format"""
        return {
            'timestamp': self.timestamp,
            'timestep': self.timestep,
            'variables': self.variables,
            'constraints': self.constraints,
            'constraint_verification': self.constraint_verification,
            'controllable_variables': self.controllable_variables,
            'performance_metrics': self.performance_metrics,
            'metadata': self.metadata,
            # Add summary statistics
            'summary': {
                'satisfied_constraints': sum(1 for state in self.constraint_verification.values() if state == 1),
                'total_constraints': len(self.constraint_verification),
                'satisfaction_rate': sum(1 for state in self.constraint_verification.values() if state == 1) / 
                                   len(self.constraint_verification) * 100 if self.constraint_verification else 0
            }
        }

class Environment:
    """Simulates ecological environment with configurable controllable variables"""
    
    DEFAULT_OUTPUT_DIR = SIMULATION_PARAMS['output_dir']
    DEFAULT_RANDOM_SEED = SIMULATION_PARAMS['random_seed']
    
    def __init__(self, 
                 output_dir: Optional[str] = None,
                 random_seed: Optional[int] = None,
                 config_path: Optional[str] = None):
        """Initialize environment with configuration"""
        self._setup_basics(output_dir, random_seed)
        
        # Setup main logger - Updated to use new interface
        self.logger = setup_logging(
            name='ecosystem',
            log_dir=self.output_dir,
            level=SIMULATION_PARAMS['log_level']
        )
        self.logger.info("\n=== Ecosystem Simulation Initialization ===")
        self.logger.info(f"Simulation ID: {self.simulation_id}")
        self.logger.info(f"Output Directory: {self.output_dir}")
        
        try:
            # Load and validate configuration
            self._load_and_validate_config(config_path)
            
            # Initialize DataFrame with proper columns
            self._init_dataframe()
            
            # Initialize variables and tracking
            self._init_from_config()
            self._init_tracking_system()
            self._save_state()
            
            # Print initialization summary
            self._print_initialization_summary()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize environment: {str(e)}")
            raise

    def _setup_basics(self, output_dir: Optional[str], random_seed: Optional[int]):
        """Setup basic configuration and directories"""
        self.output_dir = Path(output_dir or self.DEFAULT_OUTPUT_DIR)
        self.random_seed = random_seed if random_seed is not None else self.DEFAULT_RANDOM_SEED
        self.simulation_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.output_dir / 'states'
        self.state_dir.mkdir(exist_ok=True)
        
        # Set file paths
        self.history_file = self.output_dir / f'environment_history_{self.simulation_id}.json'
        self.metrics_file = self.output_dir / f'metrics_{self.simulation_id}.json'

    def _load_and_validate_config(self, config_path: Optional[str]):
        """Load and validate configuration"""
        self.config = load_ecosystem_config(config_path)
        
        # Validate relationships
        self._validate_variable_relationships()
        
        # Initialize variables
        self._init_from_config()

    def _validate_variable_relationships(self):
        """Validate variable relationships to prevent cycles and invalid dependencies"""
        relationships = self.config.get('variable_relationships', {})
        all_variables = set(self.config['variables'].keys())
        
        for var_name, rel_config in relationships.items():
            # Verify variable exists
            if var_name not in all_variables:
                raise ValueError(f"Relationship defined for non-existent variable: {var_name}")
            
            # Verify dependencies exist
            dependencies = rel_config.get('depends_on', [])
            for dep in dependencies:
                if dep not in all_variables:
                    raise ValueError(f"Invalid dependency {dep} for variable {var_name}")
            
            # Check for circular dependencies
            self._check_circular_dependencies(var_name, dependencies, set())

    def _check_circular_dependencies(self, var_name: str, dependencies: List[str], 
                                   visited: set):
        """Check for circular dependencies in variable relationships"""
        if var_name in visited:
            raise ValueError(f"Circular dependency detected involving {var_name}")
        
        visited.add(var_name)
        relationships = self.config.get('variable_relationships', {})
        
        for dep in dependencies:
            if dep in relationships:
                next_deps = relationships[dep].get('depends_on', [])
                self._check_circular_dependencies(dep, next_deps, visited.copy())

    def _init_from_config(self):
        """Initialize variables from configuration"""
        self.logger.info("\nInitializing Environmental Variables:")
        
        # Get variable names first
        self.variable_names = list(self.config['variables'].keys())
        
        # Initialize all variables
        for var_name, var_config in self.config['variables'].items():
            setattr(self, var_name, var_config['initial_value'])
            
            # Log initialization with control status
            control_status = "Controllable" if var_config.get('controllable', False) else "Uncontrolled"
            self.logger.info(
                f"  {var_name:25}: {var_config['initial_value']:6.2f} "
                f"{var_config.get('unit', '')} [{control_status}]"
            )
        
        # Get controllable variables - store both as vars and variables for compatibility
        self.controllable_vars = self.controllable_variables = [
            var_name for var_name, var_config in self.config['variables'].items()
            if var_config.get('controllable', False)
        ]
        
        self.logger.info(f"\nControllable Variables: {len(self.controllable_variables)}")
        for var in self.controllable_variables:
            config = self.config['variables'][var]
            self.logger.info(
                f"  - {var} (strength: {config.get('control_strength', 1.0):.1f}, "
                f"trend: {config.get('trend_coefficient', 0.0):+.2f})"
            )

    def run_simulation(self, num_timesteps: int, control_strategy: str = 'random') -> pd.DataFrame:
        """Run simulation with specified control strategy"""
        try:
            # Initialize environment
            self._init_from_config()
            
            # Initialize active inference agent if needed
            self.agent = None
            if control_strategy == 'active_inference':
                try:
                    # Create proper agent config with only essential info
                    agent_config = {
                        'variables': {}
                    }
                    
                    # Add each controllable variable's config
                    for var_name in self.controllable_vars:
                        var_config = self.config['variables'][var_name]
                        agent_config['variables'][var_name] = {
                            'controllable': True,
                            'control_strength': float(var_config['control_strength']),
                            'noise_std': float(var_config.get('noise_std', 0.1))
                        }
                    
                    # Initialize agent
                    self.agent = BiofirmAgent(agent_config, self.logger)
                    self.logger.info(f"Initialized active inference agent for {len(self.controllable_vars)} variables")
                    
                except Exception as e:
                    self.logger.error(f"Failed to initialize active inference agent: {str(e)}")
                    self.logger.debug("Full error:", exc_info=True)
                    raise
            
            self.logger.info(f"\nStarting {control_strategy} simulation for {num_timesteps} steps")
            
            try:
                # Run simulation steps
                for step in range(num_timesteps):
                    if control_strategy == 'random':
                        controls = self._get_random_controls()
                    else:
                        try:
                            # Get observations (0=LOW, 1=HOMEO, 2=HIGH)
                            observations = self._get_observations()
                            
                            # Get agent controls (-1/0/1 multiplied by control_strength)
                            controls = self.agent.get_action(observations)
                            
                            if not controls:  # Fallback to random if agent fails
                                self.logger.warning("Agent failed to provide controls, using random")
                                controls = self._get_random_controls()
                                
                        except Exception as e:
                            self.logger.error(f"Error in active inference step: {str(e)}")
                            self.logger.debug("Full error:", exc_info=True)
                            controls = self._get_random_controls()
                    
                    # Update environment
                    self.step(controls)
                    
                    # Print progress
                    if (step + 1) % SIMULATION_PARAMS['progress_interval'] == 0:
                        verification = self._verify_constraints()
                        self._print_progress_update(step, num_timesteps, verification)
                
                # Save final results
                self._save_final_results(control_strategy)
                
                return self.data
                
            except Exception as e:
                self.logger.error(f"Simulation failed: {str(e)}")
                raise

        except Exception as e:
            self.logger.error(f"Failed to run simulation: {str(e)}")
            raise

    def _get_observations(self) -> Dict[str, int]:
        """Get current state observations for all controllable variables
        
        Returns:
            Dictionary mapping variable names to discrete observations (0=LOW, 1=HOMEO, 2=HIGH)
        """
        observations = {}
        
        for var_name in self.controllable_vars:
            try:
                value = getattr(self, var_name)
                var_config = self.config['variables'][var_name]
                
                # Get constraints
                lower_bound = var_config['constraints']['lower']
                upper_bound = var_config['constraints']['upper']
                
                # Convert to discrete observation using variable-specific constraints
                if value < lower_bound:
                    obs = 0  # LOW
                elif value > upper_bound:
                    obs = 2  # HIGH
                else:
                    obs = 1  # HOMEO
                    
                observations[var_name] = obs
                
                self.logger.debug(
                    f"Variable {var_name}:\n"
                    f"  Value: {value:.2f}\n"
                    f"  Bounds: [{lower_bound}, {upper_bound}]\n"
                    f"  Observation: {['LOW', 'HOMEO', 'HIGH'][obs]}"
                )
                
            except Exception as e:
                self.logger.error(f"Error getting observation for {var_name}: {str(e)}")
                observations[var_name] = 1  # Default to HOMEO
                
        return observations

    def _get_random_controls(self) -> Dict[str, float]:
        """Generate random control signals for controllable variables
        
        Returns:
            Dictionary mapping variable names to control signals
        """
        controls = {}
        for var_name in self.controllable_vars:
            var_config = self.config['variables'][var_name]
            control_strength = var_config['control_strength']
            controls[var_name] = np.random.choice([-1.0, 0.0, 1.0]) * control_strength
        return controls

    def step(self, controls: Dict[str, float]) -> None:
        """Execute one simulation step with controls"""
        try:
            # Store previous state
            prev_observations = self._verify_constraints()
            
            # Update each variable
            for var_name, var_config in self.config['variables'].items():
                current = getattr(self, var_name)
                
                # Apply control if variable is controllable
                if var_name in controls:
                    control_effect = controls[var_name]
                else:
                    control_effect = 0.0
                
                # Add noise
                noise = np.random.normal(0, var_config['noise_std'])
                
                # Calculate total change
                total_change = control_effect + noise
                
                # Update value with bounds
                new_value = np.clip(current + total_change, 0.0, 100.0)
                setattr(self, var_name, new_value)
                
                self.logger.debug(
                    f"{var_name} update:\n"
                    f"  Control effect: {control_effect:+.2f}\n"
                    f"  Noise: {noise:+.2f}\n"
                    f"  Total change: {total_change:+.2f}\n"
                    f"  New value: {new_value:.2f}"
                )
            
            # Update tracking
            new_observations = self._verify_constraints()
            self._record_state()
            
        except Exception as e:
            self.logger.error(f"Step error: {str(e)}")
            raise

    def _calculate_dependencies(self, var_name: str) -> float:
        """Calculate effect of variable dependencies"""
        return calculate_dependencies(
            self.config.get('variable_relationships', {}),
            var_name,
            self.get_variable_value
        )

    def _get_variable_update_order(self) -> List[str]:
        """Determine correct order for updating variables"""
        return get_variable_update_order(self.config)

    def _calculate_base_change(self, var_name: str, current: float, 
                             var_config: Dict) -> float:
        """Calculate base change for a variable"""
        return calculate_base_change(var_name, current, var_config)

    def _apply_variable_relationships(self, var_name: str, base_value: float, 
                                    previous_values: Dict[str, float]) -> float:
        """Apply variable relationships"""
        return apply_variable_relationships(
            var_name, base_value, previous_values, 
            self.config, self.logger
        )

    def _calculate_stability_score(self) -> float:
        """Calculate system stability score"""
        return calculate_stability_score(self.data, self.config)

    def _calculate_response_time(self) -> float:
        """Calculate system response time score"""
        return calculate_response_time(self.data, self.config)

    def _verify_constraints(self) -> Dict[str, int]:
        """Verify if each variable is within constraints"""
        variables = {var: getattr(self, var) for var in self.variable_names}
        return verify_constraints(variables, self.config, self.logger)

    def _update_variables(self):
        """Update all variables based on relationships, trends, and controls"""
        # Get previous values for relationship calculations
        previous = {var: getattr(self, var) for var in self.config['variables']}
        
        # Sort variables by dependency order
        update_order = self._get_variable_update_order()
        
        # Update each variable in correct order
        for var_name in update_order:
            var_config = self.config['variables'][var_name]
            current = previous[var_name]
            
            try:
                # 1. Calculate natural change (trend + noise)
                new_value = self._calculate_base_change(var_name, current, var_config)
                
                # 2. Apply relationships from other variables
                new_value = self._apply_variable_relationships(var_name, new_value, previous)
                
                # 3. Ensure value stays within physical limits
                new_value = np.clip(new_value, 0.0, 100.0)
                
                # Log the update components
                self.logger.debug(
                    f"Updating {var_name}:\n"
                    f"  Previous: {current:.2f}\n"
                    f"  New: {new_value:.2f}\n"
                    f"  Change: {new_value - current:+.2f}"
                )
                
                # Update the variable
                setattr(self, var_name, new_value)
                
            except Exception as e:
                self.logger.error(f"Error updating {var_name}: {str(e)}")
                # Maintain previous value on error
                setattr(self, var_name, current)

    def _init_performance_metrics(self):
        """Initialize performance tracking metrics"""
        self.performance_metrics = {
            'satisfaction_rates': [],    # Tracks percentage of constraints satisfied
            'control_efforts': [],       # Tracks magnitude of control actions
            'stability_scores': [],      # Tracks system stability
            'response_times': [],        # Tracks time to reach targets
            'overall_performance': []    # Composite performance score
        }
        
        # Initialize with zero values to avoid empty lists
        for metric_list in self.performance_metrics.values():
            metric_list.append(0.0)

    def _update_performance_metrics(self, verification: Dict[str, int], 
                                  controls: Dict[str, float]):
        """Update performance tracking metrics
        
        Args:
            verification: Dictionary mapping variables to states (0,1,2)
            controls: Dictionary of control signals applied
        """
        try:
            # Calculate satisfaction rate (% of variables in homeostatic state)
            satisfaction = sum(1 for state in verification.values() if state == 1)
            satisfaction_rate = (satisfaction / len(verification)) * 100
            self.performance_metrics['satisfaction_rates'].append(satisfaction_rate)
            
            # Calculate control effort (sum of absolute control signals)
            control_effort = sum(abs(c) for c in controls.values())
            self.performance_metrics['control_efforts'].append(control_effort)
            
            # Calculate stability (inverse of recent value changes)
            stability = self._calculate_stability_score()
            self.performance_metrics['stability_scores'].append(stability)
            
            # Calculate response time (how quickly system reaches targets)
            response = self._calculate_response_time()
            self.performance_metrics['response_times'].append(response)
            
            # Log metrics
            self.logger.debug(
                f"Performance Metrics:\n"
                f"  Satisfaction Rate: {satisfaction_rate:.1f}%\n"
                f"  Control Effort: {control_effort:.2f}\n"
                f"  Stability Score: {stability:.2f}\n"
                f"  Response Score: {response:.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {str(e)}")

    def _setup_console_output(self):
        """Setup console output handler"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')  # Simplified format for console
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _print_initialization_summary(self):
        """Print initialization summary to console"""
        print("\nEnvironment Configuration Summary:")
        print("---------------------------------")
        
        # Print controllable variables
        print("\nControllable Variables:")
        for var in self.controllable_variables:
            config = self.config['variables'][var]
            print(f"  • {var:25} (strength: {config.get('control_strength', 1.0):.1f}, "
                  f"trend: {config.get('trend_coefficient', 0.0):+.2f})")
        
        # Print uncontrolled variables with dependencies
        print("\nUncontrolled Variables with Dependencies:")
        for var, config in self.config['variables'].items():
            if not config.get('controllable', False):
                deps = self.config.get('variable_relationships', {}).get(var, {}).get('depends_on', [])
                if deps:
                    print(f"  • {var:25} depends on: {', '.join(deps)}")

        print("\nOutput Files:")
        print(f"  • History: {self.history_file.name}")
        print(f"  • Metrics: {self.metrics_file.name}")
        print(f"  • States:  {self.state_dir.name}/")
        print("\nSimulation ready to start.")
        print("=" * 50)

    def _print_progress_update(self, step: int, total_steps: int, 
                             verification: Dict[str, int]):
        """Print progress update with key metrics"""
        homeostatic = sum(1 for state in verification.values() if state == 1)
        total = len(verification)
        satisfaction_rate = (homeostatic / total) * 100
        
        # Get recent performance metrics
        stability = self.performance_metrics['stability_scores'][-1]
        control_effort = self.performance_metrics['control_efforts'][-1]
        
        print(f"\nStep {step+1}/{total_steps} "
              f"({(step+1)/total_steps*100:.1f}%)")
        print(f"  • Satisfaction Rate: {satisfaction_rate:.1f}%")
        print(f"  • Stability Score:   {stability:.2f}")
        print(f"  • Control Effort:    {control_effort:.2f}")

    def _save_final_results(self, control_strategy: str):
        """Save final simulation results"""
        try:
            # Save final state
            final_state = self._get_current_state()
            final_state_file = self.state_dir / f'final_state_{control_strategy}_{self.simulation_id}.json'
            with open(final_state_file, 'w') as f:
                json.dump(final_state.to_dict(), f, indent=2)
            
            # Save performance metrics
            metrics_file = self.output_dir / f'metrics_{control_strategy}_{self.simulation_id}.json'
            with open(metrics_file, 'w') as f:
                json.dump(self.performance_metrics, f, indent=2)
            
            # Save data to CSV
            data_file = self.output_dir / f'data_{control_strategy}_{self.simulation_id}.csv'
            self.data.to_csv(data_file, index=False)
            
            print("\nSimulation Complete!")
            print("Results saved to:")
            print(f"  • Final State: {final_state_file.name}")
            print(f"  • Metrics:     {metrics_file.name}")
            print(f"  • Data:        {data_file.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to save final results: {str(e)}")
            # Save at least the data even if state saving fails
            data_file = self.output_dir / f'data_{control_strategy}_{self.simulation_id}.csv'
            self.data.to_csv(data_file, index=False)
            raise

    def _init_tracking_system(self):
        """Initialize tracking system from configuration"""
        self.logger.info("\nInitializing Tracking System:")
        
        # Initialize performance metrics
        self._init_performance_metrics()
        
        # Initialize constraints DataFrame
        self.logger.info("\nSetting Constraints:")
        constraints_data = {
            'variable': [],
            'lower_constraint': [],
            'upper_constraint': []
        }
        
        for var_name in self.variable_names:
            var_config = self.config['variables'][var_name]
            constraints_data['variable'].append(var_name)
            constraints_data['lower_constraint'].append(var_config['constraints']['lower'])
            constraints_data['upper_constraint'].append(var_config['constraints']['upper'])
            
            self.logger.info(
                f"  {var_name:25}: [{var_config['constraints']['lower']:3.0f}, "
                f"{var_config['constraints']['upper']:3.0f}] {var_config.get('unit', '')}"
            )
        
        self.constraints = pd.DataFrame(constraints_data)
        
        # Initialize state recording
        self._record_state()

    def _record_state(self):
        """Record current state to historical data"""
        try:
            # Create dictionary with current state
            new_data = {
                'timestep': len(self.data)
            }
            
            # Record all variable values
            for var_name in self.config['variables'].keys():
                new_data[var_name] = float(getattr(self, var_name))
            
            # Add new row using DataFrame constructor
            new_row = pd.DataFrame([new_data], columns=self.data.columns)
            self.data = pd.concat([self.data, new_row], ignore_index=True)
            
            self.logger.debug(
                f"Recorded state at timestep {new_data['timestep']}: " + 
                ", ".join(f"{k}: {v:.2f}" for k, v in new_data.items() if k != 'timestep')
            )
            
        except Exception as e:
            self.logger.error(f"Error recording state: {str(e)}")
            raise

    def _save_state(self):
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

    def _get_current_state(self) -> EnvironmentState:
        """Get current environment state"""
        return EnvironmentState(
            timestamp=datetime.now().isoformat(),
            timestep=len(self.data) - 1,
            variables={var: float(getattr(self, var)) for var in self.variable_names},
            constraints={
                var: {
                    'lower': float(self.constraints[self.constraints['variable'] == var]['lower_constraint'].iloc[0]),
                    'upper': float(self.constraints[self.constraints['variable'] == var]['upper_constraint'].iloc[0])
                }
                for var in self.variable_names
            },
            constraint_verification=self._verify_constraints(),
            controllable_variables=self.controllable_variables,
            performance_metrics=self.performance_metrics,
            metadata={
                'control_strategy': getattr(self, 'control_strategy', 'unknown'),
                'simulation_id': self.simulation_id,
                'random_seed': self.random_seed
            }
        )

    def get_variable_value(self, var_name: str) -> float:
        """Get current value of a variable
        
        Args:
            var_name: Name of variable to get value for
            
        Returns:
            Current value of variable
        """
        try:
            if var_name not in self.config['variables']:
                raise ValueError(f"Unknown variable: {var_name}")
                
            value = float(getattr(self, var_name))
            self.logger.debug(f"Got value for {var_name}: {value:.2f}")
            return value
            
        except Exception as e:
            self.logger.error(f"Error getting value for {var_name}: {str(e)}")
            return 0.0

    def _init_dataframe(self):
        """Initialize DataFrame with proper columns"""
        try:
            # Create columns list starting with timestep
            columns = ['timestep']
            
            # Add all variable columns
            columns.extend(self.config['variables'].keys())
            
            # Initialize empty DataFrame with proper columns and dtypes
            self.data = pd.DataFrame(columns=columns)
            self.data['timestep'] = self.data['timestep'].astype(int)
            
            # Set float dtype for all variable columns
            for var in self.config['variables'].keys():
                self.data[var] = self.data[var].astype(float)
                
            self.logger.debug(
                f"Initialized DataFrame with columns: {columns}\n"
                f"Shape: {self.data.shape}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DataFrame: {str(e)}")
            raise

    def initialize_active_inference(self) -> None:
        """Initialize active inference control agent"""
        try:
            self.logger.info(f"Initializing agents for {len(self.controllable_vars)} controllable variables")
            
            # Create minimal config for agent
            agent_config = {
                'variables': {}
            }
            
            # Add each controllable variable's config
            for var_name in self.controllable_vars:
                agent_config['variables'][var_name] = {
                    'constraints': self.constraints[var_name],
                    'observation_confidence': 0.90,
                    'homeostatic_preference': 4.0
                }
            
            # Create agent with simple config
            self.agent = BiofirmAgent(agent_config, self.logger)
            
            self.logger.info("Active inference agent initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize active inference agent: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        # Run separate simulations for each control strategy
        results = {}
        env = None  # Store last environment instance
        
        for strategy in SIMULATION_PARAMS['control_strategies']:
            # Create fresh environment for each strategy
            env = Environment()
            print(f"\nRunning {strategy.title()} Control Simulation...")
            
            # Run single strategy simulation
            results[strategy] = env.run_simulation(
                num_timesteps=SIMULATION_PARAMS['num_timesteps'],
                control_strategy=strategy
            )
            
            print(f"{strategy.title()} simulation complete.")
        
        if env is None:
            raise ValueError("No environment instance created")
            
        # Generate visualizations comparing the strategies
        print("\nGenerating Visualizations...")
        generate_all_visualizations(
            random_data=results['random'],
            active_data=results['active_inference'],
            constraints=env.constraints,
            controllable_vars=env.controllable_variables,
            output_dir=env.output_dir,
            logger=env.logger
        )
        
        # Run Active Inference Analysis only for active inference simulation
        if env.agent is not None:
            print("\nAnalyzing Active Inference Performance...")
            try:
                # Setup specific logging for free energy analysis
                fe_logger = setup_fe_logging(env.output_dir)
                
                # Run analysis
                modality_stats = analyze_active_inference_agents(
                    agent=env.agent,
                    output_dir=env.output_dir,
                    logger=fe_logger
                )
                
                # Generate comprehensive report
                generate_comprehensive_report(
                    modality_stats=modality_stats,
                    output_dir=env.output_dir,
                    logger=fe_logger
                )
                
                print("Active Inference Analysis Complete!")
                
            except Exception as e:
                env.logger.error(f"Error in active inference analysis: {str(e)}")
                env.logger.debug("Traceback:", exc_info=True)
        
        print("\nSimulation Suite Complete!")
        print(f"All outputs saved to: {env.output_dir}")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Check logs for details.")
        sys.exit(1)
