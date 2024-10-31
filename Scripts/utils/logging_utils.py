import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored output
colorama.init()

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for different log levels"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        # Save original message
        original_msg = record.msg
        
        # Add color to level name and message for non-DEBUG levels
        if record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            if record.levelname != 'DEBUG':  # Keep DEBUG messages uncolored for readability
                record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
            record.levelname = f"{color}{record.levelname:8}{Style.RESET_ALL}"
        
        # Format the record
        result = super().format(record)
        
        # Restore original message
        record.msg = original_msg
        return result

def setup_logging(simulation_id: str, output_dir: Optional[Path] = None) -> logging.Logger:
    """
    Configure enhanced logging with colored output to both console and file
    
    Args:
        simulation_id: Unique identifier for the simulation
        output_dir: Directory for log files (defaults to Outputs/)
        
    Returns:
        Configured logger instance
    """
    output_dir = Path(output_dir or 'Outputs')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(f'ecosystem_simulation_{simulation_id}')
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = ColoredFormatter(
        '%(asctime)s │ %(levelname)-8s │ %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler - captures everything
    log_file = output_dir / f'simulation_{simulation_id}.log'
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler - shows all levels with color
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Changed to DEBUG to show all messages
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log initial setup information
    logger.info(f"{'='*80}")
    logger.info(f"Starting New Simulation: {simulation_id}")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log File: {log_file}")
    logger.info(f"{'='*80}")
    
    return logger

def get_logger(simulation_id: str) -> logging.Logger:
    """
    Get an existing logger for the simulation
    
    Args:
        simulation_id: Unique identifier for the simulation
        
    Returns:
        Existing logger instance
    """
    return logging.getLogger(f'ecosystem_simulation_{simulation_id}')