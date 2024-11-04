# Biofirm

A framework for ecological system control using Active Inference agents.

## Overview

Biofirm consists of two main components:

1. **Ecosystem Control System**
   - Active Inference-based multi-agent control framework
   - Homeostatic regulation of ecological parameters
   - Comparative analysis between random and controlled dynamics

2. **BioPerplexity Analysis** 
   - California county-level bioregion research using Perplexity.ai API
   - Business case generation and pitch development
   - Cross-document visualization and analysis

## System Architecture

### Active Inference Framework
- Multi-agent POMDP (Partially Observable Markov Decision Process) implementation
- Each agent controls one ecological modality through free energy minimization
- Collective homeostatic regulation through distributed control

Key Components:
- `Ecosystem_Simulation.py`: Main simulator comparing random vs. active inference control
- `Biofirm_Agent.py`: PyMDP-based active inference agent implementation
- `POMDP_ABCD.py`: Generative model matrix generation (A,B,C,D matrices)
- `utils/`: Ecological configuration files and parameters

### Analysis Tools
- `Free_Energy_Minimization.py`: Analysis of control performance
- `Noise_Control_ActiveInference_Sweep.py`: Parameter sweep across noise and control levels

### BioPerplexity Pipeline
1. `1_Research_Bioregions.py`: County-level data collection
2. `2_Biofirm_Business_Pitch.py`: Business case generation
3. `3_Write_Letter_Perplexity.py`: Documentation generation
4. `3_Biofirm_Visualization.py`: Data visualization

## Getting Started

1. Environment Setup:
```bash
python Startup.py  # Creates PyMDP virtual environment
source venv/bin/activate
```

2. Configuration:
- Adjust ecological parameters in `utils/ecosystem_config.json`
- Configure agent parameters in generative model files

3. Run Simulations:
```bash
python Scripts/Ecosystem_Simulation.py
```

## Technical Details

See `Biofirm_Generative_Model.md` for comprehensive documentation of:
- POMDP framework implementation
- Generative model architecture
- Free energy minimization approach
- Control system dynamics

## Project Structure
```
├── Bio_Perplexity/          # Business analysis tools
├── Scripts/                 # Core simulation code
│   ├── utils/              # Configuration files
│   └── Outputs/            # Simulation results
└── Stream/                 # Documentation
```