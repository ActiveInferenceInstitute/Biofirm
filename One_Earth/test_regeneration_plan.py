#!/usr/bin/env python3
"""
Test script to generate an ecological regeneration plan for a single bioregion.
This script uses the functionality from 2_OneEarth_Regeneration_Plan.py to process
a single specified bioregion.
"""

import os
import argparse
import logging
from importlib.util import spec_from_file_location, module_from_spec

def setup_logging():
    """Set up logging with a basic configuration."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger = logging.getLogger('')
    logger.handlers = [console_handler]
    return logger

def main():
    """Main function to run the test."""
    logger = setup_logging()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate an ecological regeneration plan for a specific bioregion")
    parser.add_argument("bioregion", help="Name of the bioregion to process (directory name in Outputs)")
    parser.add_argument("--model", choices=["testing", "production"], default="testing",
                       help="Model to use: 'testing' (cheaper) or 'production' (better results)")
    args = parser.parse_args()
    
    # Get the path to the current directory and the main script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script_path = os.path.join(script_dir, "2_OneEarth_Regeneration_Plan.py")
    
    # Load the main script as a module
    spec = spec_from_file_location("regeneration_plan_module", main_script_path)
    regeneration_module = module_from_spec(spec)
    spec.loader.exec_module(regeneration_module)
    
    try:
        # Initialize API client
        key_file_path = os.path.join(script_dir, "OneEarth_Perplexity_keys.key")
        perplexity_api_key = regeneration_module.load_api_key(key_file_path)
        
        # Load system prompts
        system_prompts = regeneration_module.load_json_file(os.path.join(script_dir, 'OneEarth_System_Prompts.json'))
        
        # Get model configuration
        model_config = args.model
        model_name = system_prompts.get("config", {}).get("models", {}).get(model_config, "sonar")
        logger.info(f"Using Perplexity model: {model_name} ({model_config} mode)")
        
        # Find the bioregion directory
        outputs_dir = os.path.join(script_dir, 'Outputs')
        
        # Try various formats of the bioregion name to find a match
        bioregion_dir = None
        possible_names = [
            args.bioregion,
            args.bioregion.replace(' ', '_'),
            args.bioregion.replace('_', ' ')
        ]
        
        for name in possible_names:
            potential_dir = os.path.join(outputs_dir, name)
            if os.path.isdir(potential_dir):
                bioregion_dir = potential_dir
                logger.info(f"Found bioregion directory: {name}")
                break
        
        if not bioregion_dir:
            logger.error(f"Could not find directory for bioregion: {args.bioregion}")
            logger.info("Available bioregions:")
            for d in os.listdir(outputs_dir):
                if os.path.isdir(os.path.join(outputs_dir, d)):
                    logger.info(f"  - {d}")
            return
        
        # Process the bioregion
        logger.info(f"Processing bioregion: {os.path.basename(bioregion_dir)}")
        regeneration_module.process_region_regeneration_plan(
            perplexity_api_key, 
            system_prompts, 
            outputs_dir, 
            bioregion_dir, 
            model_name
        )
        
        logger.info(f"✅ Completed ecological regeneration plan for {os.path.basename(bioregion_dir)}")
        
    except Exception as e:
        logger.error(f"Error processing bioregion: {e}")
        raise

if __name__ == "__main__":
    main() 