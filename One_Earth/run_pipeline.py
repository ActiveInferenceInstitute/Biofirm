#!/usr/bin/env python3
"""
OneEarth Processing Pipeline Runner

This script orchestrates the complete OneEarth processing pipeline:
1. Runs bioregion research
2. Generates business cases
3. Creates visualizations and analysis

Run with: python run_pipeline.py [--skip-research] [--skip-business] [--skip-visualization] [--model testing|production]
"""

import os
import sys
import argparse
import subprocess
import logging
import time
import functools
from pathlib import Path
from datetime import datetime
import threading
import queue
import traceback
import json
import glob
import re

def format_elapsed_time(seconds):
    """Format seconds into a readable time string."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s"

# Utility function to time file operations
def log_file_operation(func):
    """Decorator to log file operations with timing information and provide live updates."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger = logging.getLogger(__name__)
        
        # Get the file path from args or kwargs
        file_path = None
        
        # Define a max length for file paths to prevent content being treated as a path
        MAX_PATH_LENGTH = 500
        
        if len(args) >= 2 and isinstance(args[1], str):
            # Check if this looks like a valid file path and not content
            potential_path = args[1]
            if (len(potential_path) < MAX_PATH_LENGTH and 
                (potential_path.endswith('.md') or 
                 potential_path.endswith('.json') or 
                 potential_path.endswith('.txt') or 
                 '.' in potential_path) and 
                not potential_path.startswith('#') and  # Skip markdown headings
                not potential_path.startswith('**') and  # Skip markdown formatting
                '\n' not in potential_path):  # Skip multiline content
                file_path = potential_path
            # This is likely a (output_dir, filename) pattern
            elif 'output_dir' in kwargs or (len(args) >= 1 and isinstance(args[0], str)):
                output_dir = kwargs.get('output_dir') or args[0]
                filename = args[1]
                # Check if filename looks like a valid filename
                if len(filename) < MAX_PATH_LENGTH and '\n' not in filename and not filename.startswith('#'):
                    file_path = os.path.join(output_dir, filename)
        elif 'file_path' in kwargs:
            potential_path = kwargs['file_path']
            if len(potential_path) < MAX_PATH_LENGTH and '\n' not in potential_path:
                file_path = potential_path
        elif 'filename' in kwargs and 'output_dir' in kwargs:
            filename = kwargs['filename']
            output_dir = kwargs['output_dir']
            if len(filename) < MAX_PATH_LENGTH and '\n' not in filename:
                file_path = os.path.join(output_dir, filename)
            
        if file_path and len(file_path) < MAX_PATH_LENGTH:
            logger.info(f"🔄 Starting operation on file: {file_path}")
            
        # Call the original function
        result = func(*args, **kwargs)
        
        elapsed_time = time.time() - start_time
        if file_path and len(file_path) < MAX_PATH_LENGTH:
            abs_path = os.path.abspath(file_path)
            # Check if file was created/modified and get its size
            file_status = "✅ Created" if os.path.exists(abs_path) else "❌ Failed to create"
            if os.path.exists(abs_path):
                file_size = os.path.getsize(abs_path)
                file_size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB"
                logger.info(f"{file_status} file: {abs_path} ({file_size_str}, took {elapsed_time:.2f} seconds)")
            else:
                logger.warning(f"{file_status} file: {abs_path} (took {elapsed_time:.2f} seconds)")
            
        return result
    return wrapper

def setup_logging(debug=False):
    """Set up logging configuration with colored output and more detailed format."""
    level = logging.DEBUG if debug else logging.INFO
    
    # Define custom formatter with colors for terminal output
    class ColoredFormatter(logging.Formatter):
        """Custom formatter with colored output for terminal."""
        COLORS = {
            'DEBUG': '\033[94m',  # Blue
            'INFO': '\033[92m',   # Green
            'WARNING': '\033[93m', # Yellow
            'ERROR': '\033[91m',   # Red
            'CRITICAL': '\033[91m\033[1m',  # Bold Red
            'ENDC': '\033[0m'     # Reset
        }
        
        def format(self, record):
            levelname = record.levelname
            message = super().format(record)
            if levelname in self.COLORS:
                # Only color messages going to console
                return f"{self.COLORS[levelname]}{message}{self.COLORS['ENDC']}"
            return message
    
    # Create a filter to ensure emoji messages are logged at INFO level
    class EmojiFilter(logging.Filter):
        """Filter to ensure messages with emoji are logged at INFO level."""
        EMOJI_CHARS = ['⏳', '✅', '📊', '📂', '🕒', '─', '═', '🔄', '💾', '🔢', '📝', '⏱️', '🌍', '📁', '⚡']
        
        def filter(self, record):
            # Check if the message contains any emoji characters or separator patterns
            if (any(emoji in str(record.msg) for emoji in self.EMOJI_CHARS) or 
                '=' * 10 in str(record.msg) or 
                '-' * 10 in str(record.msg)):
                # Force the level to INFO
                record.levelno = logging.INFO
                record.levelname = 'INFO'
            return True
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Create handlers
    file_handler = logging.FileHandler("pipeline.log")
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(EmojiFilter())
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(EmojiFilter())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)

def run_command(cmd, description):
    """Run a command as a subprocess and capture output in real-time."""
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting: {description}")
    
    success = False
    errors_found = False
    non_critical_warnings = [
        "scikit-learn not available",
        "spaCy not available",
        "sklearn is not installed",
        "networkx is not installed",
        "wordcloud is not installed",
        "plotly is not installed",
        "WARNING:",
        "Some visualization features will be limited",
        "Using basic text processing instead",
        "Network visualization will be disabled",
        "Word cloud generation will be disabled",
        "Interactive visualizations will be disabled"
    ]
    
    # Common patterns that should be INFO not ERROR, even if they come from stderr
    info_patterns = [
        "Processing region",
        "Loaded research for",
        "Generating ecological regeneration plan",
        "Using Perplexity model",
        "Ecological regeneration plan generated successfully",
        "SUCCESS:",
        "✅",
        "🔄",
        "📊",
        "⏱️",
        "💾",
        "📑",
        "📝",
        "🌍",
        "📍",
        "Completed:",
        "COMPLETED:",
        "Found",
        "Starting research",
        "Saved",
        "Generated",
        "Loading",
        "Loaded",
        "Starting",
        "Perplexity API Key loaded successfully",
        "All ecological regeneration plans completed",
        "BIOREGION"
    ]
    
    try:
        process = subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Create queues for stdout and stderr
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        
        # Create and start threads for reading stdout/stderr
        def enqueue_output(stream, is_error=False):
            for line in iter(stream.readline, ''):
                if is_error:
                    stderr_queue.put(line)
                else:
                    stdout_queue.put(line)
            stream.close()
        
        stdout_thread = threading.Thread(target=enqueue_output, args=(process.stdout, False))
        stderr_thread = threading.Thread(target=enqueue_output, args=(process.stderr, True))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        start_time = time.time()
        
        # Process output while the process is running
        while process.poll() is None:
            # Processing stdout
            try:
                while not stdout_queue.empty():
                    output = stdout_queue.get_nowait().strip()
                    if output:
                        # Determine if this is a non-critical warning
                        is_non_critical = any(warning in output for warning in non_critical_warnings)
                        # Check if this is an informational message
                        is_info = any(pattern in output for pattern in info_patterns)
                        
                        if is_non_critical:
                            logger.info(output)
                        # Check if this is likely an error message
                        elif "❌" in output or ("error" in output.lower() and not is_info) or "exception" in output.lower():
                            if not any(warning in output.lower() for warning in non_critical_warnings):
                                logger.error(output)
                                errors_found = True
                        # Otherwise it's regular output
                        else:
                            if "⚠️" in output or "warning" in output.lower():
                                logger.warning(output)
                            else:
                                logger.info(output)
            except queue.Empty:
                pass
            
            # Processing stderr
            try:
                while not stderr_queue.empty():
                    output = stderr_queue.get_nowait().strip()
                    if output:
                        # Determine if this is a non-critical warning
                        is_non_critical = any(warning in output for warning in non_critical_warnings)
                        # Check if this is an informational message despite being on stderr
                        is_info = any(pattern in output for pattern in info_patterns)
                        
                        if is_non_critical or is_info:
                            logger.info(output)
                        else:
                            logger.error(output)
                            errors_found = True
            except queue.Empty:
                pass
            
            # Provide a spinning animation to show that it's still running
            elapsed = time.time() - start_time
            spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[int(elapsed * 2) % 10]
            sys.stdout.write(f"\r{spinner} {description} still running... (elapsed: {format_elapsed_time(elapsed)})")
            sys.stdout.flush()
            time.sleep(0.1)
        
        # Process any remaining output
        stdout_thread.join(1)  # Wait for stdout thread to finish
        stderr_thread.join(1)  # Wait for stderr thread to finish
        
        # Get the exit code from the process
        exit_code = process.returncode
        
        # Clear the spinner line
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        
        elapsed_time = time.time() - start_time
        if exit_code == 0:
            if errors_found:
                logger.warning(f"⚠️ {description} completed with exit code 0 but had some error messages (took {format_elapsed_time(elapsed_time)})")
            else:
                logger.info(f"✅ {description} completed successfully (took {format_elapsed_time(elapsed_time)})")
            success = True
        else:
            logger.error(f"❌ {description} failed with exit code {exit_code}")
            success = False
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error in {description}:\n{traceback.format_exc()}")
        return False

def check_requirements():
    """Check if all requirements are met before running the pipeline."""
    logger = logging.getLogger(__name__)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create directory structure
    logger.info("Creating directory structure...")
    subprocess.run([sys.executable, os.path.join(script_dir, "create_dirs.py")])
    
    # Check for required files
    required_files = {
        'oneearth_bioregion_ecoregions.json': "Bioregion data file",
        'OneEarth_System_Prompts.json': "System prompts file",
        'OneEarth_Perplexity_keys.key': "API key file",
        '1_OneEarth_Bioregions.py': "Bioregion research script",
        '2_OneEarth_Regeneration_Plan.py': "Ecological regeneration plan generation script",
        '3_OneEarth_Vizualization.py': "Visualization and analysis script",
        'Visualization_Methods.py': "Visualization methods"
    }
    
    missing = []
    for filename, description in required_files.items():
        filepath = os.path.join(script_dir, filename)
        if not os.path.exists(filepath):
            missing.append(f"{filename} ({description})")
    
    if missing:
        logger.error("Missing required files:")
        for item in missing:
            logger.error(f"  - {item}")
        return False
    
    # Check for recommended packages but don't fail if they're not available
    logger.info("Checking recommended Python packages...")
    try:
        # Check if spaCy is installed
        logger.info("Checking for spaCy installation...")
        try:
            import spacy
            logger.info("✅ spaCy is installed")
            
            # Check if the required spaCy model is installed
            logger.info("Checking for spaCy language model...")
            try:
                nlp = spacy.load("en_core_web_sm")
                logger.info("✅ spaCy language model (en_core_web_sm) is installed")
            except OSError:
                logger.warning("⚠️ spaCy language model (en_core_web_sm) is not installed")
                logger.warning("Some NLP features in visualization may be limited")
        except ImportError:
            logger.warning("⚠️ spaCy is not installed")
            logger.warning("Using minimal NLP processing instead of spaCy (this is OK)")
    except Exception as e:
        logger.warning(f"⚠️ Could not verify package installation status: {str(e)}")
        logger.warning("Continuing with pipeline execution with minimal NLP processing")
    
    return True

def run_pipeline(skip_research=False, skip_business=False, skip_visualization=False, max_regions=None, model="testing", debug=False, max_tokens=4096):
    """Run the complete OneEarth processing pipeline."""
    logger = logging.getLogger(__name__)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check requirements
    if not check_requirements():
        logger.error("Requirements check failed. Cannot proceed with pipeline.")
        return False
    
    start_time = time.time()
    success = True
    
    # Log pipeline configuration
    logger.info(f"Pipeline Configuration:")
    logger.info(f"  - Model: {model}")
    logger.info(f"  - Max Regions: {max_regions if max_regions else 'No limit'}")
    logger.info(f"  - Skip Research: {skip_research}")
    logger.info(f"  - Skip Business: {skip_business}")
    logger.info(f"  - Skip Visualization: {skip_visualization}")
    logger.info(f"  - Debug Mode: {debug}")
    logger.info(f"  - Max Tokens: {max_tokens}")
    
    try:
        # Step 1: Run bioregion research
        if not skip_research:
            logger.info("=" * 80)
            logger.info("STEP 1: Starting bioregion research...")
            logger.info("=" * 80)
            
            cmd = f"{sys.executable} {os.path.join(script_dir, '1_OneEarth_Bioregions.py')}"
            if max_regions:
                cmd += f" --max-regions {max_regions}"
            if model:
                cmd += f" --model {model}"
            if debug:
                cmd += " --debug"
            cmd += f" --max-tokens {max_tokens}"
            
            research_success = run_command(cmd, "Bioregion Research")
            if not research_success:
                logger.error("Bioregion research failed!")
                success = False
                # If research fails, we can't proceed with business case generation
                skip_business = True
        else:
            logger.info("Skipping bioregion research (--skip-research flag used)")
            research_success = True
        
        # Step 2: Generate ecological regeneration plans
        if not skip_business:
            logger.info("=" * 80)
            logger.info("STEP 2: Generating ecological regeneration plans")
            logger.info("=" * 80)
            
            business_cmd = f"{sys.executable} {os.path.join(script_dir, '2_OneEarth_Regeneration_Plan.py')} --model {model}"
            business_success = run_command(business_cmd, "Ecological Regeneration Plan Generation")
            if not business_success:
                logger.error("Ecological regeneration plan generation failed!")
                success = False
        else:
            logger.info("Skipping ecological regeneration plan generation (--skip-business flag used)")
            business_success = True
        
        # Step 3: Run visualization (always run unless explicitly skipped)
        if not skip_visualization:
            logger.info("=" * 80)
            logger.info("STEP 3: Running visualization and analysis")
            logger.info("=" * 80)
            
            # Don't pass max-tokens to visualization as it doesn't use it
            viz_command = f"{sys.executable} {os.path.join(script_dir, '3_OneEarth_Vizualization.py')}"
            
            viz_success = run_command(viz_command, "Visualization and Analysis")
            if not viz_success:
                logger.error("Visualization and analysis failed!")
                success = False
        else:
            logger.info("Skipping visualization (--skip-visualization flag used)")
            viz_success = True
        
        # Calculate total runtime
        end_time = time.time()
        total_time = end_time - start_time
        hours, remainder = divmod(total_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logger.info("=" * 80)
        if success:
            logger.info("OneEarth pipeline completed successfully!")
        else:
            logger.info("OneEarth pipeline completed with errors. Check the log for details.")
        
        logger.info(f"Total runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        logger.info("=" * 80)
        
        return success
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        logger.error(traceback.format_exc())
        return False

def test_file_logging():
    """Run a test for file logging with timing."""
    logger = logging.getLogger(__name__)
    logger.info("Running file logging test...")
    
    # Create a test directory
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_logging")
    os.makedirs(test_dir, exist_ok=True)
    
    # Apply the decorator to a test function
    @log_file_operation
    def test_write_file(output_dir, filename, content):
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
            # Simulate some processing time
            time.sleep(1.5)
        return file_path
    
    # Test with a few files of different sizes
    logger.info("Testing with small file...")
    test_write_file(test_dir, "small_file.txt", "This is a small test file.")
    
    logger.info("Testing with medium file...")
    test_write_file(test_dir, "medium_file.txt", "Medium sized file.\n" * 50)
    
    logger.info("Testing with large file...")
    test_write_file(test_dir, "large_file.txt", "Larger test file content.\n" * 200)
    
    # Test with a nested directory
    nested_dir = os.path.join(test_dir, "nested")
    os.makedirs(nested_dir, exist_ok=True)
    logger.info("Testing with nested directory...")
    test_write_file(nested_dir, "nested_file.txt", "File in nested directory")
    
    logger.info("File logging test completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the OneEarth processing pipeline")
    parser.add_argument("--skip-research", action="store_true", help="Skip the bioregion research step")
    parser.add_argument("--skip-business", action="store_true", help="Skip the business case generation step")
    parser.add_argument("--skip-visualization", action="store_true", help="Skip the visualization step")
    parser.add_argument("--max-regions", type=int, help="Maximum number of bioregions to process")
    parser.add_argument("--model", choices=["testing", "production"], default="testing",
                       help="Model to use: 'testing' (cheaper) or 'production' (better results)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--max-tokens", type=int, default=4096,
                       help="Maximum token length for LLM responses (default: 4096)")
    parser.add_argument("--test-logging", action="store_true", help="Run a test for file logging with timing")
    args = parser.parse_args()
    
    logger = setup_logging(args.debug)
    
    if args.test_logging:
        logger.info("Starting file logging test")
        test_file_logging()
        sys.exit(0)
    
    logger.info("Starting OneEarth pipeline")
    
    success = run_pipeline(
        skip_research=args.skip_research,
        skip_business=args.skip_business,
        skip_visualization=args.skip_visualization,
        max_regions=args.max_regions,
        model=args.model,
        debug=args.debug,
        max_tokens=args.max_tokens
    )
    
    sys.exit(0 if success else 1) 