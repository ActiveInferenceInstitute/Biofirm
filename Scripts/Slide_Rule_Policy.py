"""Slide Rule Policy for ecosystem control using dual-slider mechanism"""

import numpy as np
from typing import Dict, Optional, Union, Tuple, List, Any
import logging
from dataclasses import dataclass
from Scripts.utils.logging_utils import setup_logging

@dataclass
class SliderState:
    """State of a single slider"""
    position: float  # Current position (0-100)
    velocity: float  # Current velocity (-1 to 1)
    target: float   # Target position
    
class SlideRuleAgent:
    """Dual-slider control mechanism for ecosystem variables
    
    Implements a control policy based on two coordinated sliders:
    1. Value Slider: Tracks the actual variable value
    2. Control Slider: Moves in opposition to generate control signals
    
    The sliders move at proportional but opposite velocities to maintain
    dynamic equilibrium while generating appropriate control responses.
    """
    
    def __init__(self, 
                 config: Dict[str, Any],
                 logger: Optional[logging.Logger] = None) -> None:
        """Initialize slide rule controllers for each variable
        
        Args:
            config: Configuration dictionary with variable settings
            logger: Optional logger instance
        """
        self.logger = logger or setup_logging('slide_rule_agent')
        self.config = config
        
        # Store controllable variables
        self.controllable_vars = list(config['variables'].keys())
        
        # Initialize sliders for each variable
        self.sliders = {}
        
        self.logger.info("\nInitializing Slide Rule Controllers:")
        self.logger.info(f"Number of variables: {len(self.controllable_vars)}")
        
        try:
            # Create slider pairs for each controllable variable
            for var_name, var_config in self.config['variables'].items():
                control_strength = float(var_config['control_strength'])
                
                # Initialize value and control sliders
                self.sliders[var_name] = {
                    'value': SliderState(
                        position=50.0,  # Start at midpoint
                        velocity=0.0,
                        target=50.0
                    ),
                    'control': SliderState(
                        position=50.0,  # Start at midpoint
                        velocity=0.0,
                        target=50.0
                    ),
                    'control_strength': control_strength,
                    'damping': 0.1,  # Damping factor for smooth motion
                    'response_rate': 0.2  # How quickly sliders respond
                }
                
                self.logger.info(
                    f"  • Created slide rule controller for {var_name}:\n"
                    f"    - Control strength: {control_strength:.2f}\n"
                    f"    - Response rate: {self.sliders[var_name]['response_rate']:.2f}\n"
                    f"    - Damping: {self.sliders[var_name]['damping']:.2f}"
                )
                
        except Exception as e:
            self.logger.error(f"Error in SlideRuleAgent initialization: {str(e)}")
            raise

    def get_action(self, observations: Dict[str, int]) -> Dict[str, float]:
        """Get control signals from slide rule controllers
        
        Args:
            observations: Dict mapping variable names to discrete states (0,1,2)
            
        Returns:
            Dict mapping variable names to control signals (-control_strength to +control_strength)
        """
        try:
            controls = {}
            
            # Process each variable's slide rule
            for var_name, slider_data in self.sliders.items():
                try:
                    # Get current observation state
                    obs_state = observations[var_name]
                    
                    # Update value slider target based on observation
                    if obs_state == 0:  # LOW
                        target = 75.0  # Move up
                    elif obs_state == 2:  # HIGH
                        target = 25.0  # Move down
                    else:  # HOMEO
                        target = 50.0  # Center
                    
                    # Update value slider
                    value_slider = slider_data['value']
                    value_slider.target = target
                    
                    # Calculate value slider velocity
                    distance_to_target = value_slider.target - value_slider.position
                    value_slider.velocity = (
                        distance_to_target * slider_data['response_rate'] * 
                        (1.0 - slider_data['damping'])
                    )
                    
                    # Update value slider position
                    value_slider.position += value_slider.velocity
                    value_slider.position = np.clip(value_slider.position, 0.0, 100.0)
                    
                    # Update control slider (opposite motion)
                    control_slider = slider_data['control']
                    control_slider.velocity = -value_slider.velocity
                    control_slider.position += control_slider.velocity
                    control_slider.position = np.clip(control_slider.position, 0.0, 100.0)
                    
                    # Calculate control signal from slider positions
                    relative_position = (control_slider.position - value_slider.position) / 100.0
                    control_signal = relative_position * slider_data['control_strength']
                    
                    # Apply control limits
                    control_signal = np.clip(
                        control_signal, 
                        -slider_data['control_strength'],
                        slider_data['control_strength']
                    )
                    
                    controls[var_name] = control_signal
                    
                    self.logger.debug(
                        f"{var_name} slide rule:\n"
                        f"  Observation: {['LOW', 'HOMEO', 'HIGH'][obs_state]}\n"
                        f"  Value Slider: pos={value_slider.position:.1f}, vel={value_slider.velocity:+.2f}\n"
                        f"  Control Slider: pos={control_slider.position:.1f}, vel={control_slider.velocity:+.2f}\n"
                        f"  Control Signal: {control_signal:+.2f}"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error processing {var_name}: {str(e)}")
                    controls[var_name] = 0.0  # Safe default
                    
            return controls
            
        except Exception as e:
            self.logger.error(f"Error in get_action: {str(e)}")
            return {}

    def get_agent_data(self, var_name: str) -> Dict[str, Any]:
        """Get controller data for analysis
        
        Args:
            var_name: Name of variable/modality
            
        Returns:
            Dictionary containing controller data:
                - value_slider: Value slider state history
                - control_slider: Control slider state history
                - control_signals: List of control signals sent
                - control_strength: Controller's control strength
        """
        try:
            if var_name not in self.sliders:
                self.logger.warning(f"No controller data for {var_name}")
                return {}
                
            slider_data = self.sliders[var_name]
            
            return {
                'value_slider': {
                    'positions': [slider_data['value'].position],
                    'velocities': [slider_data['value'].velocity],
                    'targets': [slider_data['value'].target]
                },
                'control_slider': {
                    'positions': [slider_data['control'].position],
                    'velocities': [slider_data['control'].velocity],
                    'targets': [slider_data['control'].target]
                },
                'control_signals': [0.0],  # Initialize with no control
                'control_strength': slider_data['control_strength'],
                'response_rate': slider_data['response_rate'],
                'damping': slider_data['damping']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting controller data for {var_name}: {str(e)}")
            return {}