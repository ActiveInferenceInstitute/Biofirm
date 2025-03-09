# OneEarth Workflow

This document provides a detailed visualization of the complete OneEarth processing pipeline, showing data flow and processing steps.

## System Components

```mermaid
graph TD
    subgraph "Input Data"
        A1[oneearth_bioregion_ecoregions.json]
        A2[OneEarth_System_Prompts.json]
        A3[RR_LLM_keys.key]
    end

    subgraph "Processing Scripts"
        B1[1_OneEarth_Bioregions.py]
        B2[2_OneEarth_Business_Pitch.py]
        B3[3_OneEarth_Vizualization.py]
        B4[Visualization_Methods.py]
        B5[run_pipeline.py]
        B6[create_dirs.py]
    end

    subgraph "External Services"
        C1[Perplexity API]
    end

    subgraph "Output Data"
        D1[Research Reports]
        D2[Business Cases]
        D3[Visualizations]
    end

    % Data connections
    A1 --> B1
    A2 --> B1
    A2 --> B2
    A3 --> B1
    A3 --> B2

    % Processing flow
    B1 --> D1
    D1 --> B2
    B2 --> D2
    D1 --> B3
    D2 --> B3
    B3 --> D3
    B4 -.-> B3
    B5 -.-> B1
    B5 -.-> B2
    B5 -.-> B3
    B6 -.-> B5

    % API connection
    C1 --- B1
    C1 --- B2
```

## Detailed Processing Flow

```mermaid
sequenceDiagram
    actor User
    participant Setup as create_dirs.py
    participant Runner as run_pipeline.py
    participant Bio as 1_OneEarth_Bioregions.py
    participant Business as 2_OneEarth_Business_Pitch.py
    participant Vis as 3_OneEarth_Vizualization.py
    participant API as Perplexity API
    participant Outputs as Output Folders

    User->>Runner: Run pipeline
    Runner->>Setup: Create directory structure
    Setup-->>Runner: Directory structure ready
    
    Runner->>Bio: Run bioregion research
    
    loop For each bioregion
        Bio->>API: Request ecological research
        API-->>Bio: Return research data
        Bio->>API: Request market research
        API-->>Bio: Return research data
        Bio->>API: Request supply chain research
        API-->>Bio: Return research data
        Bio->>API: Request regulatory research
        API-->>Bio: Return research data
        Bio->>Outputs: Save research reports
    end
    
    Bio-->>Runner: Research complete
    Runner->>Business: Generate business cases
    
    loop For each bioregion
        Business->>Outputs: Load research reports
        Business->>API: Generate business case
        API-->>Business: Return business case
        Business->>Outputs: Save business case
    end
    
    Business-->>Runner: Business cases complete
    Runner->>Vis: Generate visualizations
    
    Vis->>Outputs: Load research reports
    Vis->>Outputs: Load business cases
    Vis->>Outputs: Save visualizations
    
    Vis-->>Runner: Visualizations complete
    Runner-->>User: Pipeline complete
```

## Data Structure

```mermaid
erDiagram
    BIOREGION {
        string id
        string name
        string type
        string parent_id
    }
    
    RESEARCH-PERSONA {
        string id
        string short_name
        string description
    }
    
    RESEARCH-REPORT {
        string bioregion_id
        string persona
        string timestamp
        string research_data
    }
    
    BUSINESS-CASE {
        string bioregion_id
        string timestamp
        string content
    }
    
    VISUALIZATION {
        string type
        string region
        string filename
    }
    
    BIOREGION ||--o{ RESEARCH-REPORT : "researched by"
    RESEARCH-PERSONA ||--o{ RESEARCH-REPORT : "produces"
    BIOREGION ||--o{ BUSINESS-CASE : "has"
    RESEARCH-REPORT }|--o{ BUSINESS-CASE : "informs"
    RESEARCH-REPORT }|--o{ VISUALIZATION : "visualized in"
    BUSINESS-CASE }|--o{ VISUALIZATION : "visualized in"
```

## File Dependencies

```mermaid
flowchart TD
    subgraph "Helper Scripts"
        A[run_pipeline.py]
        B[create_dirs.py]
    end

    subgraph "Core Processing"
        C[1_OneEarth_Bioregions.py]
        D[2_OneEarth_Business_Pitch.py]
        E[3_OneEarth_Vizualization.py]
    end

    subgraph "Support Modules"
        F[Visualization_Methods.py]
    end

    subgraph "Input Files"
        G[oneearth_bioregion_ecoregions.json]
        H[OneEarth_System_Prompts.json]
        I[RR_LLM_keys.key]
    end

    subgraph "Output Directories"
        J[Outputs/]
        K[Visualizations/]
    end

    % Dependencies
    A --> B
    A --> C
    A --> D
    A --> E
    
    C --> G
    C --> H
    C --> I
    C --> J
    
    D --> H
    D --> I
    D --> J
    
    E --> F
    E --> J
    E --> K
    
    B --> J
    B --> K
```

## Run Sequence

```mermaid
stateDiagram-v2
    [*] --> Setup
    Setup --> ValidateFiles
    ValidateFiles --> RunResearch
    ValidateFiles --> Error : Missing Files
    
    RunResearch --> RunBusiness : Success
    RunResearch --> Error : Failure
    
    RunBusiness --> RunVisualization : Success
    RunBusiness --> Error : Failure
    
    RunVisualization --> Complete : Success
    RunVisualization --> Error : Failure
    
    Complete --> [*]
    Error --> [*]
``` 