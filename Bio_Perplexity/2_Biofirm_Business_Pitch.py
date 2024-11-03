import os
import json
import time
from openai import OpenAI
from datetime import datetime
import logging
import glob

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger = logging.getLogger('')
    logger.handlers = [console_handler]
    return logger

logger = setup_logging()

# Specify target System prompt by short name
TARGET_SYSTEM_PROMPT = "biofirm_business_case_manager"

def load_api_key(key_file_path):
    try:
        with open(key_file_path, 'r') as key_file:
            keys = key_file.read().strip().split('\n')
            api_keys = dict(key.split('=') for key in keys)
            perplexity_api_key = api_keys.get('PERPLEXITY_API_KEY')
        
        if not perplexity_api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in the key file")
        
        logger.info("Perplexity API Key loaded successfully")
        return perplexity_api_key
    except Exception as e:
        logger.error(f"Error reading API key: {str(e)}")
        raise

def load_json_file(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        raise

def get_system_message(system_prompts, short_name):
    system_prompt = next((prompt for prompt in system_prompts.values() 
                         if prompt["short_name"] == short_name), None)
    if not system_prompt:
        raise ValueError(f"System prompt with short_name '{short_name}' not found.")
    return {
        "role": "system",
        "content": system_prompt["description"]
    }

def load_research_reports(region_dir):
    """Load all research reports from a region directory."""
    research_data = {}
    
    # Load all markdown files (they contain the well-formatted research)
    for md_file in glob.glob(os.path.join(region_dir, "*_report_*.md")):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                persona_type = md_file.split('_report_')[0].split('_')[-1]
                research_data[persona_type] = content
        except Exception as e:
            logger.error(f"Error loading research file {md_file}: {e}")
    
    return research_data

def generate_business_case_prompt(bioregion, research_data):
    """Generate prompt for business case analysis."""
    prompt = f"""Please analyze the following comprehensive research data for {bioregion['county']} County, {bioregion['state']} 
and develop a detailed business case for establishing a Biofirm natural capital company in this region.

The research includes multiple expert perspectives:

{research_data}

Based on this research, please provide a comprehensive business case analysis following your outlined structure. 
Focus particularly on:
1. Unique opportunities in this region for natural capital development
2. Competitive advantages and market positioning
3. Specific revenue streams and business models
4. Critical risks and mitigation strategies
5. Clear recommendations for implementation

Please maintain a practical, implementation-focused approach while ensuring alignment with 
sustainability principles and natural capital preservation."""

    return prompt

def save_business_case(output_dir, bioregion_id, content):
    """Save business case as both JSON and MD files."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save as Markdown
    md_filename = f"{bioregion_id}_business_case_{timestamp}.md"
    md_path = os.path.join(output_dir, md_filename)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Save as JSON
    json_filename = f"{bioregion_id}_business_case_{timestamp}.json"
    json_path = os.path.join(output_dir, json_filename)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "bioregion_id": bioregion_id,
            "content": content
        }, f, indent=2)
    
    logger.info(f"Saved business case: {md_path}")
    return md_path

def process_region_business_case(client, system_prompts, bioregion, base_dir):
    """Process business case for a specific region."""
    bioregion_id = bioregion['id']
    region_dir = os.path.join(base_dir, f"{bioregion['state']}_{bioregion['county']}")
    
    if not os.path.exists(region_dir):
        logger.warning(f"No research data found for {bioregion_id}")
        return
    
    # Load all research reports
    research_data = load_research_reports(region_dir)
    if not research_data:
        logger.warning(f"No research reports found for {bioregion_id}")
        return
    
    # Generate business case prompt
    prompt = generate_business_case_prompt(bioregion, research_data)
    
    messages = [
        get_system_message(system_prompts, TARGET_SYSTEM_PROMPT),
        {"role": "user", "content": prompt}
    ]
    
    logger.info(f"Generating business case for {bioregion_id}")
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=messages,
        )
        
        content = response.choices[0].message.content
        
        # Save the business case
        output_path = save_business_case(region_dir, bioregion_id, content)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Business case generated successfully in {elapsed_time:.2f} seconds")
        logger.info(f"Saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"Error generating business case for {bioregion_id}: {e}")
        raise
    
    time.sleep(1)  # Rate limiting

def main():
    logger = setup_logging()
    
    # Setup paths and load required data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(script_dir, "RR_LLM_keys.key")
    
    try:
        # Initialize API client
        perplexity_api_key = load_api_key(key_file_path)
        client = OpenAI(
            api_key=perplexity_api_key,
            base_url="https://api.perplexity.ai"
        )
        
        # Load configuration files
        bioregions = load_json_file(os.path.join(script_dir, 'Biofirm_Regions.json'))
        system_prompts = load_json_file(os.path.join(script_dir, 'Biofirm_System_Prompts.json'))
        
        # Process each bioregion
        for bioregion_id, bioregion in bioregions.items():
            try:
                process_region_business_case(
                    client,
                    system_prompts,
                    bioregion,
                    os.path.join(script_dir, 'Outputs')
                )
            except Exception as e:
                logger.error(f"Failed to process {bioregion_id}: {e}")
                continue
        
        logger.info("All business cases completed")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    main()
