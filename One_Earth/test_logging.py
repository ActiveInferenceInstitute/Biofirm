#!/usr/bin/env python3
"""
Test script to verify logging improvements.
"""

import os
import logging
import time
from datetime import datetime
from run_pipeline import log_file_operation

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@log_file_operation
def save_test_file(output_dir, filename, content):
    """Save test file to specified directory."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Successfully saved test file to: {file_path}")
    except Exception as e:
        logger.error(f"Error saving test file to {file_path}: {str(e)}")
        raise

def simulate_perplexity_response():
    """Simulate a perplexity API response with timing."""
    logger.info("Starting perplexity API call simulation...")
    
    # Simulate API call
    start_time = time.time()
    time.sleep(1.5)  # Simulate API call taking 1.5 seconds
    
    # Generate test content
    content = "This is a test perplexity response."
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Log perplexity response details
    bioregion_name = "Test_Bioregion"
    persona_name = "test_persona"
    logger.info(f"📄 Perplexity response for {bioregion_name} ({persona_name}): {elapsed_time:.2f} seconds")
    
    # Save test files
    output_dir = os.path.join('test_logging')
    json_filename = f"{bioregion_name}_{persona_name}.json"
    markdown_filename = f"{bioregion_name}_{persona_name}.md"
    
    logger.info(f"📝 Saving to: {markdown_filename} (Processing time: {elapsed_time:.2f} seconds)")
    
    # Create test result
    test_result = {
        "timestamp": datetime.now().isoformat(),
        "bioregion_id": "test-id-123",
        "persona": persona_name,
        "research_data": content,
        "processing_time": f"{elapsed_time:.2f} seconds"
    }
    
    # Save test files
    save_test_file(output_dir, markdown_filename, 
                  f"# Test Report\n\n**Research Persona:** {persona_name}\n**Date:** {datetime.now().isoformat()[:10]}\n**Processing Time:** {elapsed_time:.2f} seconds\n\n---\n\n{content}")
    
    logger.info("Test completed successfully!")

if __name__ == "__main__":
    # Create test directory
    os.makedirs('test_logging', exist_ok=True)
    
    # Run test
    simulate_perplexity_response() 