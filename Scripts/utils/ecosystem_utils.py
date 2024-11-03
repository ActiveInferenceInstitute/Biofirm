"""
Utility functions for ecosystem simulation and management.
Contains helper functions extracted from Ecosystem_Simulation.py for better modularity.
"""

import numpy as np
from typing import Dict, List, Any, Tuple
import logging
from pathlib import Path
import pandas as pd

def calculate_dependencies(relationships: Dict, var_name: str, 
                         get_var_value: callable) -> float:
    """Calculate effect of variable dependencies
    
    Args:
        relationships: Dictionary of variable relationships from config
        var_name: Name of variable to calculate dependencies for
        get_var_value: Callable to get current value of a variable
        
    Returns:
        Total dependency effect
    """
    if var_name not in relationships:
        return 0.0
        
    rel_config = relationships[var_name]
    total_effect = 0.0
    
    for dep_var in rel_config['depends_on']:
        dep_value = get_var_value(dep_var)
        strength = float(rel_config['strength'])
        
        # Calculate effect based on relationship type
        if rel_config['type'] == 'positive':
            effect = (dep_value - 50.0) * strength
        else:
            effect = (50.0 - dep_value) * strength
            
        total_effect += effect
        
    return total_effect

def get_variable_update_order(config: Dict) -> List[str]:
    """Determine correct order for updating variables based on dependencies
    
    Args:
        config: Environment configuration dictionary
        
    Returns:
        List of variable names in correct update order
    """
    relationships = config.get('variable_relationships', {})
    variables = list(config['variables'].keys())
    
    # Create dependency graph
    graph = {var: set(relationships.get(var, {}).get('depends_on', [])) 
            for var in variables}
    
    # Topological sort
    result = []
    visited = set()
    
    def visit(var: str):
        if var in visited:
            return
        visited.add(var)
        for dep in graph[var]:
            visit(dep)
        result.append(var)
        
    for var in variables:
        visit(var)
        
    return result

def calculate_base_change(var_name: str, current: float, 
                         var_config: Dict) -> float:
    """Calculate base change for a variable
    
    Args:
        var_name: Name of variable
        current: Current value of variable
        var_config: Configuration for this variable
        
    Returns:
        New base value after applying trends and noise
    """
    # Apply trend
    trend = var_config.get('trend_coefficient', 0.0)
    trend_effect = trend * current if current > 0 else trend
    
    # Apply noise
    noise_std = var_config.get('noise_std', 5.0)
    noise = np.random.normal(0, noise_std)
    
    return current + trend_effect + noise

def apply_variable_relationships(var_name: str, base_value: float,
                               previous_values: Dict[str, float],
                               config: Dict,
                               logger: logging.Logger) -> float:
    """Apply variable relationships with improved dynamics
    
    Args:
        var_name: Name of variable
        base_value: Current base value
        previous_values: Dictionary of previous variable values
        config: Environment configuration
        logger: Logger instance
        
    Returns:
        New value after applying relationships
    """
    if var_name in config.get('variable_relationships', {}):
        rel_config = config['variable_relationships'][var_name]
        
        # Get dependencies and their influence
        for dep_var in rel_config.get('depends_on', []):
            dep_value = previous_values[dep_var]
            strength = float(rel_config.get('strength', 0.1))
            rel_type = rel_config.get('type', 'positive')
            
            # Calculate influence based on relationship type
            if rel_type == 'positive':
                influence = strength * (dep_value / 100.0)
                base_value += influence * base_value
            else:
                influence = strength * (1 - dep_value / 100.0)
                base_value -= influence * base_value
            
            logger.debug(
                f"Relationship {dep_var} → {var_name}:\n"
                f"  Type: {rel_type}\n"
                f"  Strength: {strength:.2f}\n"
                f"  Influence: {influence:+.2f}"
            )
    
    return base_value

def calculate_stability_score(data: pd.DataFrame, config: Dict) -> float:
    """Calculate system stability score
    
    Args:
        data: DataFrame containing historical data
        config: Environment configuration
        
    Returns:
        Stability score between 0 and 1
    """
    if len(data) < 2:
        return 1.0
        
    stability_scores = []
    for var in config['variables']:
        if var in data.columns:
            changes = np.abs(np.diff(data[var].values[-10:]))
            avg_change = np.mean(changes) if len(changes) > 0 else 0
            stability_scores.append(np.exp(-avg_change))
            
    return np.mean(stability_scores)

def calculate_response_time(data: pd.DataFrame, config: Dict) -> float:
    """Calculate system response time score
    
    Args:
        data: DataFrame containing historical data
        config: Environment configuration
        
    Returns:
        Response time score between 0 and 1
    """
    if len(data) < 2:
        return 0.0
        
    response_scores = []
    for var_name, var_config in config['variables'].items():
        if var_name in data.columns:
            target = (var_config['constraints']['upper'] + 
                     var_config['constraints']['lower']) / 2
            current = data[var_name].iloc[-1]
            
            distance = abs(current - target) / target
            response_scores.append(np.exp(-distance))
            
    return np.mean(response_scores)

def verify_constraints(variables: Dict[str, float], 
                      config: Dict,
                      logger: logging.Logger) -> Dict[str, int]:
    """Verify if each variable is within constraints
    
    Args:
        variables: Dictionary of current variable values
        config: Environment configuration
        logger: Logger instance
        
    Returns:
        Dictionary mapping variable names to states (0=LOW, 1=HOMEO, 2=HIGH)
    """
    verification = {}
    for var_name, var_config in config['variables'].items():
        value = float(variables[var_name])
        constraints = var_config['constraints']
        lower = float(constraints['lower'])
        upper = float(constraints['upper'])
        
        if value < lower:
            state = 0
        elif value > upper:
            state = 2
        else:
            state = 1
            
        verification[var_name] = state
        
        if var_config.get('controllable', False):
            logger.debug(
                f"{var_name}: {value:.1f} → state={state} "
                f"(bounds: [{lower}, {upper}])"
            )
    
    return verification 