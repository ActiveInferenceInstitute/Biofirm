"""Unified logging utility for ecosystem simulation"""

import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logging(name: str, log_dir: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger with file and console output
    
    Args:
        name: Logger name/component identifier
        log_dir: Directory for log files (default: project_root/logs)
        level: Logging level (default: INFO)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Setup log directory
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / 'logs'
    else:
        log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fh = logging.FileHandler(log_dir / f'{name}_{timestamp}.log')
        fh.setLevel(level)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
    
    return logger

# Alias for backward compatibility
setup_logger = setup_logging

def get_component_logger(component_name: str) -> logging.Logger:
    """Get a logger for a specific component"""
    return logging.getLogger(component_name)