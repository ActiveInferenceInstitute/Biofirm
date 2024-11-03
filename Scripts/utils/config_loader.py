import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def load_ecosystem_config(config_path: Optional[str] = None) -> Dict:
    """Load and validate ecosystem configuration"""
    if config_path is None:
        config_path = Path(__file__).parent / 'ecosystem_config.json'
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ['variables', 'variable_relationships']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate each variable configuration
        for var_name, var_config in config['variables'].items():
            required_var_fields = [
                'initial_value', 'constraints', 'controllable',
                'control_strength', 'trend_coefficient', 'noise_std'
            ]
            for field in required_var_fields:
                if field not in var_config:
                    raise ValueError(f"Missing field {field} for variable {var_name}")
        
        return config
        
    except Exception as e:
        raise ValueError(f"Failed to load config: {str(e)}")