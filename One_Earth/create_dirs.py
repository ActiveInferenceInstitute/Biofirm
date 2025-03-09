#!/usr/bin/env python3
"""
Helper script to create the necessary directory structure for the OneEarth project.
This ensures all required directories exist before running the main scripts.
"""

import os
import argparse
import logging

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def create_directory_structure(base_dir=None):
    """Create the necessary directory structure for the OneEarth project."""
    logger = setup_logging()
    
    # Use current directory if base_dir not provided
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create main output directories
    output_dir = os.path.join(base_dir, 'Outputs')
    vis_dir = os.path.join(base_dir, 'Visualizations')
    
    # Create main directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(vis_dir, exist_ok=True)
    logger.info(f"Created main output directories: {output_dir}, {vis_dir}")
    
    # Create visualization subdirectories
    for subdir in ['regional', 'comparative', 'topic_analysis', 'network_analysis']:
        os.makedirs(os.path.join(vis_dir, subdir), exist_ok=True)
    logger.info(f"Created visualization subdirectories")
    
    # Check for required files
    required_files = [
        'oneearth_bioregion_ecoregions.json',
        'OneEarth_System_Prompts.json'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(base_dir, file)):
            missing_files.append(file)
    
    if missing_files:
        logger.warning(f"The following required files are missing: {', '.join(missing_files)}")
    
    # Check for API key file
    key_file = os.path.join(base_dir, 'OneEarth_Perplexity_keys.key')
    
    if not os.path.exists(key_file):
        logger.warning(f"API key file not found. Please create {key_file} with your API key.")
    
    logger.info("Directory structure setup complete. Ready to run OneEarth scripts.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create directory structure for OneEarth project")
    parser.add_argument("--base-dir", help="Base directory for the project (default: script directory)")
    args = parser.parse_args()
    
    create_directory_structure(args.base_dir) 