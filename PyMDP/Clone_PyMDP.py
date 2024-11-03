import os
import subprocess
import logging
import sys
from pathlib import Path

def setup_logging():
    """Configure basic logging to console with timestamp formatting"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger('clone_pymdp')

def clone_repo(logger):
    """
    Clone the PyMDP repository to study active inference implementations.
    
    This function downloads the PyMDP codebase which provides examples and implementations
    of active inference for Markov Decision Processes. The code can be used by:
    
    1. LLMs/RAG systems to learn implementation patterns for:
        - Active inference algorithms
        - Markov Decision Process modeling
        - Belief updating and inference
        - Policy selection and action sampling
        
    2. Developers looking to:
        - Study working examples of active inference
        - Understand PyMDP's modular architecture
        - Learn best practices for implementing AI algorithms
        - Reference tested mathematical operations
    
    The repository contains tutorials, examples and core algorithm implementations
    that can be analyzed programmatically or studied manually.
    
    Args:
        logger: Logger object for tracking clone progress
        
    Returns:
        bool: True if clone successful, False otherwise
    """
    repo_url = "https://github.com/infer-actively/pymdp.git"
    target_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "pymdp"
    
    logger.info("Starting PyMDP repository clone...")
    
    try:
        # Clone with progress output
        process = subprocess.run(
            ["git", "clone", "--progress", repo_url, str(target_dir)],
            stderr=subprocess.PIPE,  # Capture progress messages
            text=True
        )
        
        # Log the git progress output
        if process.stderr:
            for line in process.stderr.splitlines():
                if "Receiving objects" in line or "Resolving deltas" in line:
                    logger.info(line.strip())
        
        if target_dir.exists():
            logger.info("Clone completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Clone failed: {str(e)}")
        return False

if __name__ == "__main__":
    logger = setup_logging()
    success = clone_repo(logger)
    sys.exit(0 if success else 1)