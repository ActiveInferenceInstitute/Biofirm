import json
import os
from datetime import datetime
import traceback
import logging
import requests
import time
import argparse
from run_pipeline import log_file_operation

def setup_logging(debug=False):
    """Set up logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
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
        
        logging.debug(f"API Key loaded from {key_file_path}")
        return perplexity_api_key
    except Exception as e:
        logging.error(f"Error reading API key from {key_file_path}: {str(e)}")
        raise

def load_json_file(file_path):
    """Load and return JSON data from file."""
    try:
        logging.debug(f"Loading JSON file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logging.debug(f"Successfully loaded JSON file: {file_path}")
            return data
    except Exception as e:
        logging.error(f"Error loading {file_path}: {e}")
        return None

def save_research_report(output_dir, filename, content):
    """Save research report to specified directory."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        logging.info(f"🔄 Saving research report to: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        # Log success with file size
        file_size = os.path.getsize(file_path)
        file_size_kb = file_size / 1024
        logging.info(f"✅ Saved JSON report: {filename} ({file_size_kb:.2f} KB)")
        return file_path
    except Exception as e:
        logging.error(f"❌ Error saving research report to {file_path}: {str(e)}")
        raise

def generate_research_prompt(bioregion, persona):
    """Generate research prompt combining bioregion data and research persona."""
    return f"""{persona['description']}

Your task is to conduct comprehensive research and analysis on the following bioregion:
Bioregion ID: {bioregion['_id']}
Bioregion Name: {bioregion['name']}
Bioregion Type: {bioregion.get('type', 'N/A')}

Focus your analysis on:
1. Regional ecological systems and biodiversity
2. Environmental challenges and opportunities
3. Economic and industrial landscape
4. Regulatory environment and compliance requirements
5. Potential for sustainable biotech development
6. Local resources and infrastructure

Provide your analysis following the structure outlined in your role description."""

def get_perplexity_response(client, prompt, persona_description, model_name, max_tokens=4096):
    """
    Get a response from the Perplexity API using the requests library
    """
    try:
        logging.debug(f"Making API call with model: {model_name}")
        logging.debug(f"Prompt: {prompt}")
        logging.debug(f"Persona: {persona_description}")
        logging.debug(f"Max tokens: {max_tokens}")
        
        # Create the API request payload
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": persona_description},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        
        # Make the API request
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {client}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        response_data = response.json()
        
        # Extract the content from the response
        return response_data["choices"][0]["message"]["content"]
        
    except Exception as e:
        logging.error(f"API call failed: {str(e)}")
        return f"Error making API call: {str(e)}"

def save_markdown_report(output_dir, filename, content):
    """Save research report as Markdown."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, filename)
        
        # Calculate metrics for logging
        word_count = len(content['research_data'].split())
        
        logging.info(f"🔄 Saving Markdown report to: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            # Add metadata header
            f.write(f"# {content['bioregion_id']} Research Report\n\n")
            f.write(f"**Research Persona:** {content['persona']}\n")
            f.write(f"**Date:** {content['timestamp'][:10]}\n")
            f.write(f"**Processing Time:** {content['processing_time']}\n")
            f.write(f"**Word Count:** {word_count} words\n\n")
            f.write("---\n\n")
            # Write the actual research content
            f.write(content['research_data'])
        
        # Log success with file size
        file_size = os.path.getsize(file_path)
        file_size_kb = file_size / 1024
        logging.info(f"📑 Saved Markdown report: {filename}")
        logging.info(f"   📊 Words: {word_count} words | 💾 Size: {file_size_kb:.2f} KB")
        logging.info(f"   📂 Path: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"❌ Error saving Markdown report {filename}: {e}")
        traceback.print_exc()

def check_existing_outputs(output_dir, bioregion_name, research_personas):
    """Check if all persona outputs already exist for a bioregion."""
    all_exist = True
    existing_personas = []
    
    for persona_key, persona in research_personas.items():
        persona_name = persona.get('short_name', f'persona_{persona_key}')
        json_filename = f"{bioregion_name}_{persona_name}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        if os.path.exists(json_path):
            existing_personas.append(persona_name)
        else:
            all_exist = False
    
    return all_exist, existing_personas

def research_bioregion(client, bioregion, system_prompts, model_name, max_tokens=4096):
    """Research a single bioregion with all available personas."""
    bioregion_id = bioregion.get('_id', '')
    bioregion_name = bioregion.get('name', '')
    logging.info(f"🌍 Starting research for bioregion: {bioregion_name}")
    
    # Create output directory for this bioregion - use consistent naming convention (replace spaces with underscores)
    output_dir = os.path.join('Outputs', bioregion_name.replace(' ', '_').replace('/', '_'))
    os.makedirs(output_dir, exist_ok=True)
    logging.debug(f"Created output directory: {output_dir}")
    
    research_results = {}
    
    # Get research personas
    research_personas = {k: v for k, v in system_prompts.items() if k != "config"}
    total_personas = len(research_personas)
    logging.info(f"📊 Found {total_personas} research personas to process")
    
    # Check if all outputs already exist
    all_outputs_exist, existing_personas = check_existing_outputs(output_dir, bioregion_name, research_personas)
    if all_outputs_exist:
        logging.info(f"✅ All outputs already exist for bioregion: {bioregion_name}. Skipping...")
        
        # Load existing results to return
        for persona_key, persona in research_personas.items():
            persona_name = persona.get('short_name', f'persona_{persona_key}')
            json_filename = f"{bioregion_name}_{persona_name}.json"
            json_path = os.path.join(output_dir, json_filename)
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    research_results[persona_name] = json.load(f)
                    
                logging.info(f"✅ SUCCESS: Loaded existing research for {bioregion_name} with {persona_name}")
            except Exception as e:
                logging.error(f"❌ FAILED: Error loading existing result {json_path}: {e}")
        
        return research_results
    
    # If some outputs exist, log which ones
    if existing_personas:
        logging.info(f"📂 Found {len(existing_personas)}/{total_personas} existing outputs: {', '.join(existing_personas)}")
    
    # Process with each research persona
    for idx, (persona_key, persona) in enumerate(research_personas.items(), 1):
        persona_name = persona.get('short_name', f'persona_{persona_key}')
        progress_percent = (idx / total_personas) * 100
        
        # Check if this persona's output already exists
        json_filename = f"{bioregion_name}_{persona_name}.json"
        json_path = os.path.join(output_dir, json_filename)
        
        if os.path.exists(json_path):
            # Explicitly use INFO level for skipping messages - even if emoji is not in filter list
            logging.info(f"ℹ️ [{progress_percent:.1f}%] Skipping persona: {persona_name} ({idx}/{total_personas}) - output already exists")
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    research_results[persona_name] = json.load(f)
                    
                logging.info(f"✅ SUCCESS: Loaded existing research for {bioregion_name} with {persona_name}")
            except Exception as e:
                logging.warning(f"⚠️ ISSUE: Error loading existing result {json_path}: {e} - continuing without this data")
            
            continue
            
        logging.info(f"⏳ [{progress_percent:.1f}%] Processing with persona: {persona_name} ({idx}/{total_personas})")
        
        try:
            # Generate research prompt
            prompt = generate_research_prompt(bioregion, persona)
            prompt_word_count = len(prompt.split())
            logging.info(f"📝 Generated prompt for {persona_name} ({prompt_word_count} words)")
            
            # Log the start of the API call with timestamp
            start_time = time.time()
            start_time_str = datetime.now().strftime("%H:%M:%S")
            logging.info(f"🔄 Starting Perplexity API call at {start_time_str}...")
            
            # Get research from Perplexity
            research_content = get_perplexity_response(client, prompt, persona['description'], model_name, max_tokens)
            
            # Calculate timing and word counts
            end_time = time.time()
            elapsed_time = end_time - start_time
            word_count = len(research_content.split())
            chars_per_second = len(research_content) / elapsed_time if elapsed_time > 0 else 0
            
            research_result = {
                "timestamp": datetime.now().isoformat(),
                "bioregion_id": bioregion_id,
                "persona": persona_name,
                "prompt": prompt,
                "research_data": research_content,
                "processing_time": f"{elapsed_time:.2f} seconds",
                "word_count": word_count
            }
            
            # Save both JSON and Markdown versions
            json_filename = f"{bioregion_name}_{persona_name}.json"
            markdown_filename = f"{bioregion_name}_{persona_name}.md"
            
            # Full file paths for reporting
            json_path = os.path.join(output_dir, json_filename)
            markdown_path = os.path.join(output_dir, markdown_filename)
            
            # Create a divider for better visibility in logs
            logging.info("─" * 80)
            # Log completion with detailed metrics and emojis
            logging.info(f"✅ [{progress_percent:.1f}%] Completed: {persona_name} for {bioregion_name}")
            logging.info(f"⏱️  Time: {elapsed_time:.2f} seconds ({chars_per_second:.1f} chars/sec)")
            logging.info(f"📊 Words: {word_count} words in response")
            logging.info(f"💾 Output: {markdown_path}")
            logging.info(f"🔢 JSON: {json_path}")
            logging.info("─" * 80)
            
            save_research_report(output_dir, json_filename, research_result)
            save_markdown_report(output_dir, markdown_filename, research_result)
            
            research_results[persona_name] = research_result
            
            # Log success with clear SUCCESS indicators
            logging.info(f"✅ SUCCESS: Completed research for {bioregion_name} with {persona_name}")
            logging.info(f"⏱️ SUCCESS TIME: {elapsed_time:.2f} seconds")
            
            # Add delay between API calls to respect rate limits
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"❌ FAILED: Error researching {bioregion_name} with {persona_name}: {e}")
            traceback.print_exc()
    
    return research_results

def save_consolidated_markdown(output_dir, filename, research_results, bioregion):
    """Save consolidated research results as a single Markdown file."""
    try:
        file_path = os.path.join(output_dir, filename)
        logging.info(f"🔄 Creating consolidated Markdown report: {file_path}")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# Consolidated Research Report: {bioregion['_id']}\n\n")
            f.write(f"## {bioregion['name']}\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("---\n\n")
            
            # Write each persona's research
            for persona_name, result in research_results.items():
                f.write(f"# {persona_name.replace('_', ' ').title()} Analysis\n\n")
                f.write(f"*Processing Time: {result['processing_time']}*\n\n")
                f.write(result['research_data'])
                f.write("\n\n---\n\n")
        
        # Log success with file size
        file_size = os.path.getsize(file_path)
        file_size_kb = file_size / 1024
        logging.info(f"✅ Saved consolidated Markdown report: {file_path} ({file_size_kb:.2f} KB)")
        return file_path
    except Exception as e:
        logging.error(f"❌ Error saving consolidated report {filename}: {e}")
        traceback.print_exc()

def extract_target_bioregions(bioregions_data, max_regions=None):
    """Extract target bioregions from the hierarchical data."""
    target_bioregions = []
    
    # Get the OneEarth data from the first element of the list
    if isinstance(bioregions_data, list) and len(bioregions_data) > 0:
        oneearth_data = bioregions_data[0]
    else:
        logging.error("❌ Unexpected bioregions data format")
        return target_bioregions
    
    # Get realms
    realms = oneearth_data.get('children', [])
    logging.info(f"🌍 Found {len(realms)} biogeographic realms to process")
    
    for realm in realms:
        realm_id = realm.get('_id', '')
        realm_name = realm.get('name', '')
        logging.debug(f"Processing realm: {realm_name} (ID: {realm_id})")
        
        # Get regions within this realm
        regions = realm.get('children', [])
        if regions:
            logging.debug(f"Found {len(regions)} regions in {realm_name}")
        
        for region in regions:
            region_id = region.get('_id', '')
            region_name = region.get('name', '')
            logging.debug(f"Processing region: {region_name} (ID: {region_id})")
            
            # Get ecoregions within this region
            ecoregions = region.get('children', [])
            if ecoregions:
                logging.debug(f"Found {len(ecoregions)} ecoregions in {region_name}")
            
            for ecoregion in region.get('children', []):
                ecoregion_id = ecoregion.get('_id', '')
                ecoregion_name = ecoregion.get('name', '')
                
                if ecoregion_id:
                    # Add additional context
                    ecoregion['realm'] = realm_name
                    ecoregion['region'] = region_name
                    target_bioregions.append(ecoregion)
                    
                    # Show progress with emoji
                    if len(target_bioregions) % 5 == 0 or (max_regions and len(target_bioregions) == max_regions):
                        logging.info(f"🌿 Added ecoregion #{len(target_bioregions)}: {ecoregion_name} ({realm_name})")
                    else:
                        logging.debug(f"Added ecoregion to targets: {ecoregion_name}")
                    
                    # Break if we've reached the maximum number of bioregions
                    if max_regions is not None and len(target_bioregions) >= max_regions:
                        logging.info(f"📊 Reached max_regions limit ({max_regions})")
                        break
            
            # Break if we've reached the maximum number of bioregions
            if max_regions is not None and len(target_bioregions) >= max_regions:
                break
        
        # Break if we've reached the maximum number of bioregions
        if max_regions is not None and len(target_bioregions) >= max_regions:
            break
    
    logging.info(f"🎯 Extracted {len(target_bioregions)} bioregions for processing")
    return target_bioregions

def main():
    """Main function to orchestrate bioregion research."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run bioregion research using Perplexity API")
    parser.add_argument("--max-regions", type=int, help="Maximum number of bioregions to process")
    parser.add_argument("--model", choices=["testing", "production"], default="testing",
                       help="Model to use: 'testing' (cheaper) or 'production' (better results)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--max-tokens", type=int, default=4096, 
                       help="Maximum token length for LLM responses (default: 4096)")
    args = parser.parse_args()
    
    # Set logging level
    logger = setup_logging(args.debug)
    
    logging.info("=" * 80)
    logging.info("🚀 STARTING ONEEARTH BIOREGION RESEARCH")
    logging.info("=" * 80)
    start_time_total = time.time()
    
    # Load required data and setup
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(script_dir, "OneEarth_Perplexity_keys.key")
    bioregions_file = os.path.join(script_dir, "oneearth_bioregion_ecoregions.json")
    prompts_file = os.path.join(script_dir, "OneEarth_System_Prompts.json")
    
    try:
        # Load data files
        logging.info("📂 Loading data files...")
        bioregions_data = load_json_file(bioregions_file)
        system_prompts = load_json_file(prompts_file)
        
        if not bioregions_data or not system_prompts:
            logging.error("❌ Failed to load required data files")
            return
        
        # Get model configuration
        model_config = args.model  # "testing" or "production"
        model_name = system_prompts.get("config", {}).get("models", {}).get(model_config, "sonar")
        logging.info(f"🤖 Using Perplexity model: {model_name} ({model_config} mode)")
        
        # Initialize API key
        perplexity_api_key = load_api_key(key_file_path)
        if not perplexity_api_key:
            logging.error("❌ Failed to load API key")
            return
        logging.info("🔑 API key loaded successfully")
        
        # Create main output directory
        os.makedirs('Outputs', exist_ok=True)
        logging.info("📁 Created output directory structure")
        
        # Extract target bioregions from the hierarchical data
        target_bioregions = extract_target_bioregions(bioregions_data, args.max_regions)
        
        # Track statistics
        total_bioregions = len(target_bioregions)
        successful_bioregions = 0
        total_words_generated = 0
        total_files_created = 0
        bioregion_start_time = time.time()
        
        # Process each selected bioregion
        for i, bioregion in enumerate(target_bioregions):
            bioregion_id = bioregion['_id']
            bioregion_name = bioregion['name']
            
            # Display bioregion progress with a divider
            progress_pct = ((i) / total_bioregions) * 100
            logging.info("\n" + "=" * 80)
            logging.info(f"🔄 BIOREGION {i+1}/{total_bioregions} [{progress_pct:.1f}%]: {bioregion_name}")
            if 'realm' in bioregion and 'region' in bioregion:
                logging.info(f"📍 Realm: {bioregion['realm']} | Region: {bioregion['region']}")
            logging.info("=" * 80)
            
            bioregion_start_time = time.time()
            
            try:
                # Pass the API key directly as the client parameter
                research_results = research_bioregion(perplexity_api_key, bioregion, system_prompts, model_name, args.max_tokens)
                
                # Save consolidated results in both formats
                if research_results:
                    output_dir = os.path.join('Outputs', bioregion_name.replace(' ', '_').replace('/', '_'))
                    date_str = datetime.now().strftime('%Y%m%d')
                    
                    # Save JSON
                    consolidated_json = f"{bioregion_id}_consolidated_research_{date_str}.json"
                    save_research_report(output_dir, consolidated_json, research_results)
                    
                    # Save Markdown
                    consolidated_md = f"{bioregion_id}_consolidated_research_{date_str}.md"
                    save_consolidated_markdown(output_dir, consolidated_md, research_results, bioregion)
                    
                    # Update statistics
                    successful_bioregions += 1
                    bioregion_word_count = sum(len(result.get('research_data', '').split()) 
                                               for result in research_results.values())
                    total_words_generated += bioregion_word_count
                    # Count files (2 per persona + 2 consolidated)
                    bioregion_files = 2 * len(research_results) + 2
                    total_files_created += bioregion_files
                    
                    # Calculate time statistics
                    bioregion_elapsed = time.time() - bioregion_start_time
                    overall_elapsed = time.time() - start_time_total
                    avg_time_per_bioregion = overall_elapsed / (i + 1)
                    estimated_time_remaining = avg_time_per_bioregion * (total_bioregions - i - 1)
                    
                    # Display bioregion completion summary
                    logging.info("\n" + "-" * 80)
                    logging.info(f"✅ COMPLETED: {bioregion_name} ({i+1}/{total_bioregions})")
                    logging.info(f"⏱️  Time: {bioregion_elapsed:.1f} seconds")
                    logging.info(f"📊 Generated: {bioregion_word_count} words across {bioregion_files} files")
                    logging.info(f"🕒 Progress: {progress_pct:.1f}% complete | Est. remaining: {estimated_time_remaining/60:.1f} minutes")
                    logging.info("-" * 80)
                
            except Exception as e:
                logging.error(f"❌ Error processing bioregion {bioregion_id}: {e}")
                traceback.print_exc()
                continue
        
        # Final summary
        total_elapsed = time.time() - start_time_total
        hours, remainder = divmod(total_elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logging.info("\n" + "=" * 80)
        logging.info("🎉 BIOREGION RESEARCH COMPLETE")
        logging.info("=" * 80)
        logging.info(f"📊 Processed: {successful_bioregions}/{total_bioregions} bioregions successfully")
        logging.info(f"📝 Generated: {total_words_generated} total words")
        logging.info(f"📁 Created: {total_files_created} files")
        logging.info(f"⏱️  Total time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        if successful_bioregions > 0:
            logging.info(f"⚡ Performance: {total_words_generated/total_elapsed:.1f} words/second overall")
        logging.info("=" * 80)
            
    except Exception as e:
        logging.error(f"❌ Fatal error in main: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
