import json
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def load_ecosystem_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load ecosystem configuration from JSON file
    
    Args:
        config_path: Path to configuration file (optional)
        
    Returns:
        Dictionary containing ecosystem configuration
    """
    if config_path is None:
        config_path = Path(__file__).parent / 'ecosystem_config.json'
    else:
        config_path = Path(config_path)
        
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.info(f"Loaded ecosystem configuration from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Failed to load ecosystem configuration: {str(e)}")
        raise 