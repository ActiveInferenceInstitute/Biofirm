# OneEarth Architecture

This document provides a detailed explanation of the OneEarth system architecture, data flow, and component interactions.

## System Overview

The OneEarth system is designed to analyze bioregions from the OneEarth framework, generate business cases for sustainable ventures, and visualize insights to inform decision-making. The system follows a sequential pipeline architecture with three main stages:

1. **Bioregion Research**: Analyzes bioregions through multiple expert perspectives
2. **Business Case Generation**: Creates comprehensive business proposals based on research
3. **Visualization & Analysis**: Generates visual insights and comparisons across regions

## System Architecture Diagram

```mermaid
graph TD
    subgraph "Data Sources"
        A1[oneearth_bioregion_ecoregions.json] --> P1
        A2[OneEarth_System_Prompts.json] --> P1
        A2 --> P2
    end

    subgraph "Processing Pipeline"
        P1[1. OneEarth_Bioregions.py] --> P2[2. OneEarth_Business_Pitch.py]
        P2 --> P3[3. OneEarth_Vizualization.py]
    end

    subgraph "Outputs"
        P1 --> B1[Bioregion Research Reports]
        P2 --> B2[Business Case Documents]
        P3 --> B3[Visualizations]
    end

    subgraph "API Services"
        C1[Perplexity API] --- P1
        C1 --- P2
    end

    subgraph "Supporting Modules"
        D1[Visualization_Methods.py] --- P3
    end
```

## Component Details

### 1. Data Sources

#### oneearth_bioregion_ecoregions.json
- **Purpose**: Provides hierarchical bioregion data from the OneEarth framework
- **Structure**: 
  - Hierarchical tree representing realm, region, and ecoregion relationships
  - Contains metadata for each region including unique IDs, names, and image references
  - Used to identify target regions for analysis

#### OneEarth_System_Prompts.json
- **Purpose**: Defines specialized research personas for AI-assisted analysis
- **Structure**:
  - Collection of role definitions with specialized expertise:
    - Ecological Researcher
    - Market Analyst
    - Supply Chain Strategist
    - Regulatory Compliance Expert
    - Business Case Manager
  - Each role includes detailed system prompts to guide AI analysis

### 2. Processing Components

#### 1_OneEarth_Bioregions.py
- **Purpose**: Conducts specialized research on each bioregion
- **Key Functions**:
  - `load_json_file()`: Loads bioregion and system prompt data
  - `generate_research_prompt()`: Creates context-specific research prompts
  - `get_perplexity_response()`: Calls Perplexity API with research personas
  - `research_bioregion()`: Orchestrates multi-perspective research
  - `save_consolidated_markdown()`: Consolidates insights into reports

#### 2_OneEarth_Business_Pitch.py
- **Purpose**: Generates business cases from research data
- **Key Functions**:
  - `load_research_reports()`: Loads research data from previous stage
  - `generate_business_case_prompt()`: Creates business case generation prompt
  - `process_region_business_case()`: Orchestrates business case creation
  - `save_business_case()`: Saves business proposals in markdown and JSON

#### 3_OneEarth_Vizualization.py
- **Purpose**: Analyzes and visualizes research and business data
- **Key Functions**:
  - `collect_regional_files()`: Aggregates all research and business documents
  - `analyze_regional_research()`: Applies NLP and visual analytics
  - Uses various visualization methods from Visualization_Methods.py

#### Visualization_Methods.py
- **Purpose**: Provides specialized visualization and analysis functions
- **Key Functions**:
  - Text preprocessing and NLP functions
  - Dimension reduction methods (PCA, t-SNE)
  - Statistical visualization (confidence intervals, term frequency)
  - Network analysis and visualization

### 3. Data Flow

```mermaid
sequenceDiagram
    participant User
    participant BioRegions as 1_OneEarth_Bioregions.py
    participant BusinessPitch as 2_OneEarth_Business_Pitch.py
    participant Visualization as 3_OneEarth_Vizualization.py
    participant PerplexityAPI as Perplexity API
    
    User->>BioRegions: Run research process
    BioRegions->>PerplexityAPI: Request ecological research
    PerplexityAPI-->>BioRegions: Return research data
    BioRegions->>PerplexityAPI: Request market analysis
    PerplexityAPI-->>BioRegions: Return market data
    BioRegions->>PerplexityAPI: Request supply chain analysis
    PerplexityAPI-->>BioRegions: Return supply chain data
    BioRegions->>PerplexityAPI: Request regulatory analysis
    PerplexityAPI-->>BioRegions: Return regulatory data
    BioRegions->>User: Save research reports
    
    User->>BusinessPitch: Run business case generation
    BusinessPitch->>BioRegions: Load research reports
    BusinessPitch->>PerplexityAPI: Generate business case
    PerplexityAPI-->>BusinessPitch: Return business case
    BusinessPitch->>User: Save business case report
    
    User->>Visualization: Run visualization
    Visualization->>BioRegions: Load research reports
    Visualization->>BusinessPitch: Load business cases
    Visualization->>User: Generate visualizations
```

## Directory Structure

```
OneEarth/
├── 1_OneEarth_Bioregions.py             # Research generation script
├── 2_OneEarth_Business_Pitch.py         # Business case generation script
├── 3_OneEarth_Vizualization.py          # Visualization script
├── OneEarth_README.md                   # Project README
├── OneEarth_Architecture.md             # This architecture documentation
├── OneEarth_System_Prompts.json         # System prompts for research personas
├── oneearth_bioregion_ecoregions.json   # Bioregion data
├── Visualization_Methods.py             # Visualization utility functions
├── requirements.txt                     # Project dependencies
├── RR_LLM_keys.key                      # API keys (not included in repo)
├── Outputs/                             # Generated research and business cases
│   └── Region_State_County/             # Organized by region
│       ├── region_ecological_researcher_report_*.md
│       ├── region_market_analyst_report_*.md
│       ├── region_supply_chain_strategist_report_*.md
│       ├── region_regulatory_compliance_expert_report_*.md
│       ├── region_consolidated_research_*.md
│       └── region_business_case_*.md
└── Visualizations/                      # Generated visualizations
    ├── regional/                        # Region-specific visualizations
    ├── comparative/                     # Cross-region comparisons
    ├── topic_analysis/                  # Topic modeling results
    └── network_analysis/                # Term network visualizations
```

## Customization and Extension

The OneEarth system is designed to be extensible in several ways:

1. **Additional Bioregions**: New bioregions can be added to the input JSON
2. **Enhanced System Prompts**: The expert personas can be refined or expanded
3. **New Visualizations**: Additional visualization methods can be added to the module
4. **Model Upgrades**: The system can be updated to use new AI models as they become available

## Limitations and Considerations

- **API Rate Limits**: The system incorporates delay mechanisms between API calls to respect rate limits
- **Processing Time**: Large-scale analyses may require significant processing time
- **Cost Considerations**: API usage incurs costs based on token usage
- **Data Storage**: Large research outputs require adequate storage capacity

## Potential Future Enhancements

1. **Interactive Dashboard**: Web-based visualization dashboard
2. **Real-time Updates**: Continuous monitoring of bioregion changes
3. **Comparative Analysis**: Enhanced cross-regional comparative analysis
4. **Integration with GIS**: Geographic information system integration
5. **Stakeholder Feedback Loop**: Mechanisms to incorporate human feedback 