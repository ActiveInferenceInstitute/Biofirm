import json
import os
from datetime import datetime
import traceback
import logging
from openai import OpenAI
import time

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger = logging.getLogger('')
    logger.handlers = [console_handler]
    return logger

def load_api_key(key_file_path):
    """Load API key from file."""
    try:
        with open(key_file_path, 'r') as key_file:
            keys = key_file.read().strip().split('\n')
            api_keys = dict(key.split('=') for key in keys)
            perplexity_api_key = api_keys.get('PERPLEXITY_API_KEY')
        
        if not perplexity_api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in the key file")
        
        logging.info("Perplexity API Key loaded successfully")
        return perplexity_api_key
    except Exception as e:
        logging.error(f"Error reading API key: {str(e)}")
        raise

def load_json_file(file_path):
    """Load and return JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading {file_path}: {e}")
        return None

def save_research_report(output_dir, filename, content):
    """Save research report to specified directory."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)
        logging.info(f"Saved report: {file_path}")
    except Exception as e:
        logging.error(f"Error saving report {filename}: {e}")
        traceback.print_exc()

def generate_research_prompt(bioregion, persona):
    """Generate research prompt combining bioregion data and research persona."""
    return f"""{persona['description']}

Your task is to conduct comprehensive research and analysis on the following bioregion:
Country: {bioregion['country']}
State: {bioregion['state']}
County: {bioregion['county']}
ID: {bioregion['id']}

Focus your analysis on:
1. Regional ecological systems and biodiversity
2. Environmental challenges and opportunities
3. Economic and industrial landscape
4. Regulatory environment and compliance requirements
5. Potential for sustainable biotech development
6. Local resources and infrastructure

Provide your analysis following the structure outlined in your role description."""

def get_perplexity_response(client, prompt, persona_description):
    """Get response from Perplexity API."""
    messages = [
        {
            "role": "system",
            "content": persona_description
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error getting Perplexity response: {e}")
        raise

def save_markdown_report(output_dir, filename, content):
    """Save research report as Markdown."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            # Add metadata header
            f.write(f"# {content['bioregion_id']} Research Report\n\n")
            f.write(f"**Research Persona:** {content['persona']}\n")
            f.write(f"**Date:** {content['timestamp'][:10]}\n")
            f.write(f"**Processing Time:** {content['processing_time']}\n\n")
            f.write("---\n\n")
            # Write the actual research content
            f.write(content['research_data'])
        logging.info(f"Saved Markdown report: {file_path}")
    except Exception as e:
        logging.error(f"Error saving Markdown report {filename}: {e}")
        traceback.print_exc()

def research_bioregion(client, bioregion, research_personas):
    """Conduct research on a bioregion using multiple research personas."""
    bioregion_id = bioregion['id']
    county_name = bioregion['county']
    
    # Create bioregion-specific output directory
    output_dir = os.path.join('Outputs', f"{bioregion['state']}_{county_name}")
    os.makedirs(output_dir, exist_ok=True)
    
    research_results = {}
    
    # Select relevant research personas using the correct keys
    relevant_personas = {
        'ecological_researcher': research_personas['0'],
        'market_analyst': research_personas['1'],
        'supply_chain_strategist': research_personas['2'],
        'regulatory_compliance_expert': research_personas['3']
    }
    
    # Generate research from each persona
    for persona_name, persona in relevant_personas.items():
        try:
            # Check if research already exists
            existing_file = f"{bioregion_id}_{persona_name}_report_{datetime.now().strftime('%Y%m%d')}"
            if os.path.exists(os.path.join(output_dir, f"{existing_file}.json")):
                logging.info(f"Skipping existing research for {bioregion_id} with {persona_name}")
                continue

            prompt = generate_research_prompt(bioregion, persona)
            
            logging.info(f"Starting research for {bioregion_id} with {persona_name}")
            start_time = time.time()
            
            # Get research from Perplexity
            research_content = get_perplexity_response(client, prompt, persona['description'])
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            research_result = {
                "timestamp": datetime.now().isoformat(),
                "bioregion_id": bioregion_id,
                "persona": persona_name,
                "prompt": prompt,
                "research_data": research_content,
                "processing_time": f"{elapsed_time:.2f} seconds"
            }
            
            # Save both JSON and Markdown versions
            json_filename = f"{existing_file}.json"
            markdown_filename = f"{existing_file}.md"
            
            save_research_report(output_dir, json_filename, research_result)
            save_markdown_report(output_dir, markdown_filename, research_result)
            
            research_results[persona_name] = research_result
            
            logging.info(f"Completed research for {bioregion_id} with {persona_name}")
            logging.info(f"Time taken: {elapsed_time:.2f} seconds")
            
            # Add delay between API calls
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error researching {bioregion_id} with {persona_name}: {e}")
            traceback.print_exc()
    
    return research_results

def save_consolidated_markdown(output_dir, filename, research_results, bioregion):
    """Save consolidated research results as a single Markdown file."""
    try:
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# Consolidated Research Report: {bioregion['id']}\n\n")
            f.write(f"## {bioregion['county']} County, {bioregion['state']}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("---\n\n")
            
            # Write each persona's research
            for persona_name, result in research_results.items():
                f.write(f"# {persona_name.replace('_', ' ').title()} Analysis\n\n")
                f.write(f"*Processing Time: {result['processing_time']}*\n\n")
                f.write(result['research_data'])
                f.write("\n\n---\n\n")
                
        logging.info(f"Saved consolidated Markdown report: {file_path}")
    except Exception as e:
        logging.error(f"Error saving consolidated Markdown report: {e}")
        traceback.print_exc()

def main():
    """Main function to orchestrate bioregion research."""
    logger = setup_logging()
    
    # Load required data and setup
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(script_dir, "RR_LLM_keys.key")
    
    try:
        # Initialize API client
        perplexity_api_key = load_api_key(key_file_path)
        client = OpenAI(
            api_key=perplexity_api_key,
            base_url="https://api.perplexity.ai"
        )
        
        # Load data files
        bioregions = load_json_file(os.path.join(script_dir, 'Biofirm_Regions.json'))
        research_personas = load_json_file(os.path.join(script_dir, 'Biofirm_System_Prompts.json'))
        
        if not bioregions or not research_personas:
            logging.error("Failed to load required data files")
            return
        
        # Create main output directory
        os.makedirs('Outputs', exist_ok=True)
        
        # Process each bioregion
        for bioregion_id, bioregion in bioregions.items():
            logging.info(f"\nResearching bioregion: {bioregion['id']} - {bioregion['county']}, {bioregion['state']}")
            try:
                research_results = research_bioregion(client, bioregion, research_personas)
                
                # Save consolidated results in both formats
                if research_results:
                    output_dir = os.path.join('Outputs', f"{bioregion['state']}_{bioregion['county']}")
                    date_str = datetime.now().strftime('%Y%m%d')
                    
                    # Save JSON
                    consolidated_json = f"{bioregion['id']}_consolidated_research_{date_str}.json"
                    save_research_report(output_dir, consolidated_json, research_results)
                    
                    # Save Markdown
                    consolidated_md = f"{bioregion['id']}_consolidated_research_{date_str}.md"
                    save_consolidated_markdown(output_dir, consolidated_md, research_results, bioregion)
                
            except Exception as e:
                logging.error(f"Error processing bioregion {bioregion['id']}: {e}")
                traceback.print_exc()
                continue
            
    except Exception as e:
        logging.error(f"Fatal error in main: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
