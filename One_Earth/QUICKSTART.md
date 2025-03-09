# OneEarth Quickstart Guide

This document provides quick reference commands for setting up and running the OneEarth processing pipeline.

## Setup

### 1. Install Dependencies

```bash
# Install required Python packages
pip install -r requirements.txt

# Download spaCy model (required for visualization)
python -m spacy download en_core_web_sm
```

### 2. Set Up API Key

The system uses the Perplexity API for generating research content and business cases.

```bash
# The project includes a default API key in OneEarth_Perplexity_keys.key
# To use your own key, edit this file or create a new one:
echo "PERPLEXITY_API_KEY=your_key_here" > OneEarth_Perplexity_keys.key
```

### 3. Create Directory Structure

```bash
# Create required directories
python create_dirs.py
```

## Running the Pipeline

### Run Complete Pipeline

```bash
# Process all bioregions using the default model (testing)
python3 run_pipeline.py

# Process all bioregions using the cheapest model (explicitly for testing)
python3 run_pipeline.py --model testing

# Process limited number of bioregions (for testing)
python3 run_pipeline.py --max-regions 2 --model testing

# Process bioregions with the best research model (more expensive)
python3 run_pipeline.py --model production
```

### Model Options

The system supports different Perplexity API models:

| Mode | Model | Description | Cost |
|------|-------|-------------|------|
| `testing` | `sonar` | Cheapest option, suitable for testing | $1/$1 per million tokens (input/output) |
| `production` | `sonar-deep-research` | Best for detailed research | $2/$8 per million tokens (input/output) |

### Run Individual Steps

```bash
# Run only bioregion research with specific model
python3 1_OneEarth_Bioregions.py --model testing
python3 1_OneEarth_Bioregions.py --model production

# Run only business case generation with specific model
python3 2_OneEarth_Business_Pitch.py --model testing
python3 2_OneEarth_Business_Pitch.py --model production

# Run only visualization (model choice not applicable)
python3 3_OneEarth_Vizualization.py
```

### Control Bioregion Processing

```bash
# Process only a specific number of bioregions
python3 1_OneEarth_Bioregions.py --max-regions 3 --model testing

# Run full pipeline with limited bioregions
python3 run_pipeline.py --max-regions 2 --model testing
```

### Skip Specific Steps

```bash
# Skip research (use existing research data)
python3 run_pipeline.py --skip-research

# Skip business case generation
python3 run_pipeline.py --skip-business

# Skip visualization
python3 run_pipeline.py --skip-visualization

# Combine skip options as needed
python3 run_pipeline.py --skip-research --skip-business
```

## Checking Results

### Research Reports

```bash
# List bioregion folders
ls -la Outputs/

# Check research reports for a specific bioregion
ls -la Outputs/<BioregionName>/

# View a specific research report
cat Outputs/<BioregionName>/<report_filename>.md
```

### Visualizations

```bash
# List visualization directories
ls -la Visualizations/

# Check regional visualizations
ls -la Visualizations/regional/

# Check comparative visualizations
ls -la Visualizations/comparative/

# Check topic analysis
ls -la Visualizations/topic_analysis/

# Check network analysis
ls -la Visualizations/network_analysis/
```

## Troubleshooting

### Check Log Files

```bash
# Check main pipeline log
cat pipeline.log

# Check for error messages
grep ERROR pipeline.log

# Follow log in real-time during pipeline execution
tail -f pipeline.log
```

### API Key Issues

```bash
# Verify API key file exists
ls -la OneEarth_Perplexity_keys.key

# Check API key format (should show PERPLEXITY_API_KEY=xxx)
grep -v "^#" OneEarth_Perplexity_keys.key
```

### Directory Structure

```bash
# Reset directory structure
rm -rf Outputs/ Visualizations/
python create_dirs.py
```

### Common Errors

1. **Missing dependencies**: Run `pip install -r requirements.txt` again
2. **API key errors**: Check that your API key is valid and correctly formatted
3. **Missing spaCy model**: Run `python -m spacy download en_core_web_sm`
4. **Directory access issues**: Ensure you have write permissions to the current directory

## Example End-to-End Workflows

### Quick Test (Cheap)

```bash
# Test pipeline with minimal cost
pip install -r requirements.txt
python -m spacy download en_core_web_sm
# Ensure OneEarth_Perplexity_keys.key exists with valid API key
python create_dirs.py
python run_pipeline.py --max-regions 1 --model testing
```

### Full Production Run (Best Quality)

```bash
# Run full pipeline with best quality
pip install -r requirements.txt
python -m spacy download en_core_web_sm
# Ensure OneEarth_Perplexity_keys.key exists with valid API key
python create_dirs.py
python run_pipeline.py --model production
```

### Sequential Testing

```bash
# Run each step separately for testing
pip install -r requirements.txt
python -m spacy download en_core_web_sm
# Ensure OneEarth_Perplexity_keys.key exists with valid API key
python create_dirs.py

# Step 1: Test with one bioregion
python 1_OneEarth_Bioregions.py --max-regions 1 --model testing

# Step 2: Generate business case
python 2_OneEarth_Business_Pitch.py --model testing

# Step 3: Run visualization
python 3_OneEarth_Vizualization.py
```

### Processing Specific Regions

To focus on specific regions or limit processing:

```bash
# Process just 3 regions with testing model
python run_pipeline.py --max-regions 3 --model testing

# Skip research if already done, just generate business cases
python run_pipeline.py --skip-research --model testing

# Generate just visualizations from existing data
python run_pipeline.py --skip-research --skip-business
``` 