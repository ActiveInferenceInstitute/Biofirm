# Biofirm Generative Model - Active Inference Framework

## System Architecture

### Ecosystem Initialization
- @Ecosystem_Simulation.py instantiates N active inference agents
- Each agent corresponds to a controllable ecological modality
- Number of agents (N) matches the number of controllable parameters in the ecosystem

### Ecosystem Configuration
Each variable in @ecosystem_config.json is specified with:
- **Variable Naming**: `{name}_N{noise}_C{control}`
  - N: Noise standard deviation parameter
  - C: Control strength parameter
- **Parameters**:
  - `initial_value`: Starting value [0-100]
  - `constraints`: Upper/lower bounds for homeostasis
  - `controllable`: Boolean flag for agent control
  - `control_strength`: Multiplier for control signals
  - `trend_coefficient`: Natural drift tendency
  - `noise_std`: Environmental noise magnitude
  - `unit`: Measurement unit specification

### POMDP Agent Configuration
Each agent implements a Partially Observable Markov Decision Process:
- **Observation Space**: Discrete states {0, 1, 2}
  - 0: Below constraint (LOW)
  - 1: Within constraints (HOMEOSTATIC) 
  - 2: Above constraint (HIGH)

- **Generative Model Components**:
  - A matrix (3x3): Maps observations to hidden states
    - P(o|s): Probability of observation given state
    - Encodes agent's model of sensory mapping
    - Updated through experience to improve state inference
  
  - B matrix (3x3x3): Encodes state transitions
    - P(s'|s,a): Probability of next state given current state and action
    - Represents agent's model of environmental dynamics
    - Dimensions: [current_state, next_state, action]
  
  - C vector (3,): Prior preferences over states
    - Encodes desired homeostatic state
    - Maximum preference for state 1 (HOMEOSTATIC)
    - Shapes policy selection through expected free energy

## Operational Flow

### Per Timestep Processing
1. **State Inference (Perception)**:
   - Receive observation ot from environment
   - Compute posterior belief Q(st|ot) through variational inference
   - Minimize variational free energy F to update beliefs:
     ```
     F = DKL[Q(s)||P(s)] - EQ(s)[log P(o|s)]
     ```

2. **Policy Selection**:
   - For each policy π, compute expected free energy G(π):
     ```
     G(π) = ∑τ [DKL[Q(sτ|π)||P(sτ)] + EQ(sτ)[H(P(oτ|sτ))]]
     ```
   - First term: Risk (divergence from preferred states)
   - Second term: Ambiguity (expected uncertainty)
   - Select policy minimizing G(π)

3. **Control Output**:
   - Sample action from selected policy
   - Generate control signal ∈ {-1, 0, 1}
   - Scale by control_strength parameter
   - Apply to environmental dynamics

### Feedback Loop
- Control signals modify underlying natural dynamics
- System maintains homeostasis through continuous perception-action cycles
- Agents collectively regulate ecosystem parameters through free energy minimization

### Variable Dynamics
- Each variable evolves according to:
  ```python
  new_value = current_value + 
              control_strength * control_signal +
              trend_coefficient +
              noise_std * random_normal()
  ```

## Key Properties
- Agents learn environmental dynamics through experience
- Policy selection balances goal-seeking with uncertainty reduction
- Collective behavior emerges from individual free energy minimization
- System exhibits adaptive homeostatic regulation