import os
import json
import time
from openai import OpenAI
from datetime import datetime
import logging
import glob
import pandas as pd
from typing import Dict, Any

# ​​Can you include the energy/funding costs for a proposed policy -business case- as a proforma business model and iterating and improving model


def setup_logging():
    """Setup logging with pro-forma specific formatting and cleaner output"""
    # Create a formatter that includes timestamp and level
    formatter = logging.Formatter(
        '%(asctime)s - Pro-Forma Analysis - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup console handler with the formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Setup logger
    logger = logging.getLogger('pro_forma_analysis')
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Add our console handler
    logger.addHandler(console_handler)
    
    # Prevent duplicate logging
    logger.propagate = False
    
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
    """Generate prompt for business case analysis with structured financial requirements."""
    # Convert research data to a formatted string
    research_summary = "\n\n".join([
        f"=== {persona.upper()} PERSPECTIVE ===\n{content}"
        for persona, content in research_data.items()
    ])
    
    prompt = f"""Analyze the following research data for {bioregion.get('county', '')} County, {bioregion.get('state', '')} 
and develop a detailed pro-forma business case for establishing a Biofirm natural capital company in this region.

RESEARCH DATA:
{research_summary}

Please provide a comprehensive pro-forma business analysis with two parts:

PART 1 - NARRATIVE ANALYSIS
Provide a detailed narrative analysis covering:
1. Executive Summary
2. Market Analysis & Opportunities
3. Business Model & Revenue Streams
4. Risk Assessment & Mitigation
5. Implementation Strategy
6. Recommendations

PART 2 - STRUCTURED FINANCIAL DATA
Provide detailed financial projections in the following JSON-compatible format:

{{
    "revenue_projections": {{
        "year_1": {{
            "product_sales": "X",
            "licensing_royalties": "X",
            "grants_funding": "X",
            "consulting_services": "X",
            "total_revenue": "X"
        }},
        // Repeat for years 2-5
    }},
    "cost_structure": {{
        "energy_costs": {{
            "electricity": "X",
            "renewable_investment": "X",
            "efficiency_measures": "X"
        }},
        "operational_costs": {{
            "research_development": "X",
            "manufacturing": "X",
            "labor": "X",
            "marketing": "X"
        }},
        "capital_expenditure": {{
            "initial_setup": "X",
            "equipment": "X",
            "facility_improvements": "X"
        }}
    }},
    "funding_requirements": {{
        "initial_capital": "X",
        "venture_capital": "X",
        "grants": "X",
        "loans": "X",
        "timeline": ["milestone1", "milestone2"]
    }},
    "financial_metrics": {{
        "roi": "X",
        "npv": "X",
        "irr": "X",
        "payback_period": "X",
        "profit_margins": "X"
    }},
    "sensitivity_analysis": {{
        "revenue_impact": {{"scenario": "X% change", "impact": "Y% change"}},
        "cost_impact": {{"scenario": "X% change", "impact": "Y% change"}},
        "energy_impact": {{"scenario": "X% change", "impact": "Y% change"}}
    }},
    "sustainability_metrics": {{
        "carbon_footprint": "X",
        "energy_efficiency": "X",
        "waste_reduction": "X",
        "water_usage": "X"
    }}
}}

Replace all X values with actual numbers, ensuring consistency across projections.
Format Part 2 exactly as shown above to enable direct JSON parsing.
Include clear assumptions for all calculations."""

    return prompt

def extract_financial_data(content: str) -> Dict[str, Any]:
    """Extract structured financial data from the business case content."""
    try:
        # Find the structured financial data section
        parts = content.split("PART 2 - STRUCTURED FINANCIAL DATA")
        if len(parts) < 2:
            logger.warning("Structured financial data section not found")
            return None
        
        financial_section = parts[1]
        
        # Initialize structured data
        financial_data = {
            "projections": {
                "revenue": {
                    "product_sales": {},
                    "licensing_royalties": {},
                    "grants_funding": {},
                    "consulting_services": {},
                    "total_revenue": {}
                },
                "costs": {
                    "energy": {
                        "electricity": {},
                        "renewable_investment": {},
                        "efficiency_measures": {}
                    },
                    "operational": {
                        "research_development": {},
                        "manufacturing": {},
                        "labor": {},
                        "marketing": {}
                    },
                    "capital": {
                        "initial_setup": None,
                        "equipment": {},
                        "facility_improvements": {}
                    }
                },
                "funding": {
                    "initial_capital": None,
                    "venture_capital": None,
                    "grants": None,
                    "loans": None,
                    "timeline": []
                },
                "metrics": {
                    "roi": None,
                    "npv": None,
                    "irr": None,
                    "payback_period": None,
                    "profit_margins": None
                }
            },
            "sensitivity_analysis": {
                "revenue": [],
                "costs": [],
                "energy": []
            },
            "sustainability_metrics": {
                "carbon_footprint": None,
                "energy_efficiency": None,
                "waste_reduction": None,
                "water_usage": None
            }
        }

        # Extract values using regex patterns
        # Note: In a full implementation, you would add detailed regex patterns 
        # to extract each specific value from the financial_section
        
        # Example extraction (simplified):
        import re
        
        # Extract revenue data
        for year in range(1, 6):
            year_pattern = f"Year {year}:"
            if year_data := re.search(f"{year_pattern}.*?(\$[\d,]+)", financial_section):
                financial_data["projections"]["revenue"]["total_revenue"][f"year_{year}"] = year_data.group(1)

        # Extract metrics
        if roi_match := re.search(r"ROI:\s*([\d.]+)%", financial_section):
            financial_data["projections"]["metrics"]["roi"] = float(roi_match.group(1))
        
        if npv_match := re.search(r"NPV.*?:\s*\$([\d,]+)", financial_section):
            financial_data["projections"]["metrics"]["npv"] = float(npv_match.group(1).replace(",", ""))

        # Add more regex patterns for other data points...

        return financial_data
    except Exception as e:
        logger.error(f"Error extracting financial data: {e}")
        return None

def save_business_case(output_dir, bioregion_id, content, financial_data=None):
    """Save pro-forma business case with enhanced financial data."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    files_saved = []
    
    # Save narrative as Markdown
    md_filename = f"{bioregion_id}_pro_forma_{timestamp}.md"
    md_path = os.path.join(output_dir, md_filename)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Pro-Forma Business Analysis\n\n")
        f.write(content)
    files_saved.append(md_filename)
    
    # Save financial data if available
    if financial_data:
        # Save as JSON
        fin_filename = f"{bioregion_id}_pro_forma_financials_{timestamp}.json"
        fin_path = os.path.join(output_dir, fin_filename)
        with open(fin_path, 'w', encoding='utf-8') as f:
            json.dump(financial_data, f, indent=2)
        files_saved.append(fin_filename)
        
        # Try to save as CSV
        try:
            df = pd.json_normalize(financial_data, sep='_')
            csv_filename = f"{bioregion_id}_pro_forma_financials_{timestamp}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            df.to_csv(csv_path, index=False)
            files_saved.append(csv_filename)
        except Exception as e:
            logger.warning(f"Could not save CSV version of financial data: {e}")
    
    # Save complete analysis
    json_filename = f"{bioregion_id}_pro_forma_complete_{timestamp}.json"
    json_path = os.path.join(output_dir, json_filename)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "timestamp": timestamp,
                "bioregion_id": bioregion_id,
                "analysis_type": "pro_forma",
                "version": "2.0"
            },
            "narrative": content,
            "financial_data": financial_data,
            "schema_version": "pro_forma_v2"
        }, f, indent=2)
    files_saved.append(json_filename)
    
    # Log saved files in a clean format
    logger.info(f"Pro-forma analysis for {bioregion_id} saved:")
    for filename in files_saved:
        logger.info(f"  - {filename}")
    
    return md_path

def process_region_business_case(client, system_prompts, bioregion, base_dir):
    """Process pro-forma business case analysis for a specific region."""
    try:
        bioregion_id = bioregion.get('id')
        state = bioregion.get('state', '')
        county = bioregion.get('county', '')
        
        if not all([bioregion_id, state, county]):
            logger.error(f"Missing required bioregion information for {bioregion_id}")
            return
            
        region_dir = os.path.join(base_dir, f"{state}_{county}")
        os.makedirs(region_dir, exist_ok=True)
        
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
        
        logger.info(f"Processing {bioregion_id}: Generating pro-forma analysis")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=messages,
        )
        
        content = response.choices[0].message.content
        
        # Extract structured financial data
        financial_data = extract_financial_data(content)
        
        # Save the pro-forma analysis
        output_path = save_business_case(
            region_dir, 
            bioregion_id, 
            content,
            financial_data
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Completed {bioregion_id}: Analysis generated in {elapsed_time:.2f} seconds")
        
        time.sleep(1)  # Rate limiting
        
    except Exception as e:
        logger.error(f"Failed {bioregion_id}: {str(e)}")
        return  # Continue with next region instead of raising

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
        
        logger.info("Starting pro-forma business analysis generation")
        
        # Load configuration files
        bioregions = load_json_file(os.path.join(script_dir, 'Biofirm_Regions.json'))
        system_prompts = load_json_file(os.path.join(script_dir, 'Biofirm_System_Prompts.json'))
        
        # Process each bioregion with proper ID handling
        for bioregion_id, bioregion in bioregions.items():
            # Ensure bioregion has required fields
            if not isinstance(bioregion, dict) or 'id' not in bioregion:
                logger.warning(f"Skipping invalid bioregion entry: {bioregion_id}")
                continue
                
            try:
                process_region_business_case(
                    client,
                    system_prompts,
                    bioregion,
                    os.path.join(script_dir, 'Outputs')
                )
            except Exception as e:
                logger.error(f"Failed to process pro-forma analysis for {bioregion['id']}: {str(e)}")
                continue
        
        logger.info("All pro-forma business analyses completed")
        
    except Exception as e:
        logger.error(f"Fatal error in pro-forma analysis: {e}")
        raise

if __name__ == "__main__":
    main()
