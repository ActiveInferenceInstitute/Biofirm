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
  - **A Matrix (Observation Likelihood)**:
    - **Description**: Maps observations to hidden states.
    - **Structure**: 3x3 matrix where each column represents P(o|s) for a given state.
    - **Initialization**:
      ```python:Scripts/POMDP_ABCD.py:POMDPMatrices.initialize_likelihood_matrix
      def initialize_likelihood_matrix(self) -> np.ndarray:
          """Initialize observation model P(o|s)
          
          Creates a simple 3x3 likelihood matrix mapping observations to states:
          - Each column is P(o|s) for a given state
          - High confidence in correct observations (diagonal)
          - Small probability of adjacent observations
          
          Returns:
              A[o,s] = P(o|s) likelihood matrix
              Shape: (3,3) for LOW/HOMEO/HIGH observations and states
          """
          # Initialize with zeros
          A = np.zeros((3, 3), dtype=np.float64)
          
          # High confidence in correct observations (diagonal)
          conf = self.matrix_config.observation_confidence  # e.g. 0.90
          np.fill_diagonal(A, conf)
          
          # Small probability of adjacent observations
          noise = (1.0 - conf) / 2.0  # Split remaining probability
          
          # Add noise to adjacent states
          A[0, 1] = noise  # P(o=LOW | s=HOMEO)
          A[1, 0] = noise  # P(o=HOMEO | s=LOW)
          A[1, 2] = noise  # P(o=HOMEO | s=HIGH)
          A[2, 1] = noise  # P(o=HIGH | s=HOMEO)
          
          # Add tiny probability to remaining transitions
          A[0, 2] = noise  # P(o=LOW | s=HIGH)
          A[2, 0] = noise  # P(o=HIGH | s=LOW)
          
          # Verify columns sum to 1.0
          if not np.allclose(A.sum(axis=0), 1.0):
              self.logger.error(f"A matrix:\n{A}")
              self.logger.error(f"Column sums: {A.sum(axis=0)}")
              raise ValueError(f"A matrix columns must sum to 1: {A.sum(axis=0)}")
          
          return A.astype(np.float64)  # Ensure float64 type
      ```

  - **B Matrix (Transition Model)**:
    - **Description**: Encodes state transitions based on current state and action.
    - **Structure**: 3x3x3 tensor where B[s', s, a] = P(s'|s, a).
    - **Initialization**:
      ```python:Scripts/POMDP_ABCD.py:POMDPMatrices.initialize_transition_matrix
      def initialize_transition_matrix(self) -> np.ndarray:
          """Initialize transition model P(s'|s,a)
          
          Returns:
              B[s',s,a] = P(s'|s,a) encoding action effects
          """
          B = np.zeros((3, 3, 3), dtype=np.float64)
          
          # DECREASE action [a=0]
          B[:,:,0] = np.array([
              [0.90, 0.80, 0.60],  # P(s'=LOW | s, DEC)
              [0.10, 0.15, 0.30],  # P(s'=HOMEO | s, DEC)
              [0.00, 0.05, 0.10]   # P(s'=HIGH | s, DEC)
          ])
          
          # MAINTAIN action [a=1]
          B[:,:,1] = np.array([
              [0.85, 0.10, 0.00],  # P(s'=LOW | s, MAINTAIN)
              [0.10, 0.80, 0.10],  # P(s'=HOMEO | s, MAINTAIN)
              [0.05, 0.10, 0.90]   # P(s'=HIGH | s, MAINTAIN)
          ])
          
          # INCREASE action [a=2]
          B[:,:,2] = np.array([
              [0.10, 0.05, 0.00],  # P(s'=LOW | s, INC)
              [0.30, 0.15, 0.10],  # P(s'=HOMEO | s, INC)
              [0.60, 0.80, 0.90]   # P(s'=HIGH | s, INC)
          ])
          
          return B
      ```

  - **C Vector (Preference Model)**:
    - **Description**: Encodes agent's preferences over states.
    - **Structure**: 1D array with size equal to the number of states.
    - **Initialization**:
      ```python:Scripts/POMDP_ABCD.py:POMDPMatrices.initialize_preference_matrix
      def initialize_preference_matrix(self) -> np.ndarray:
          """Initialize preferences over observations
          
          Returns:
              C[o] = P(o) with strong preference for HOMEO
          """
          log_prefs = np.array([
              0.1,                                # LOW state
              self.matrix_config.homeostatic_preference,  # HOMEO state (preferred)
              0.1                                 # HIGH state
          ], dtype=np.float64)
          
          # Normalize to probabilities
          prefs = softmax(log_prefs)
          return prefs.reshape(-1)  # Ensure 1D array
      ```

  - **D Vector (Prior Beliefs)**:
    - **Description**: Represents the initial belief state of the agent over hidden states.
    - **Structure**: 1D array with size equal to the number of states.
    - **Initialization**:
      ```python:Scripts/POMDP_ABCD.py:POMDPMatrices.initialize_prior_beliefs
      def initialize_prior_beliefs(self) -> np.ndarray:
          """Initialize prior beliefs over states
          
          Returns:
              D[s] = P(s) with slight HOMEO bias
          """
          priors = np.array([0.33, 0.34, 0.33], dtype=np.float64)
          return priors.reshape(-1)  # Ensure 1D array
      ```

## Operational Flow

### Per Timestep Processing
1. **State Inference (Perception)**:
   - Receive observation \( o_t \) from environment
   - Compute posterior belief \( Q(s_t|o_t) \) through variational inference
   - Minimize variational free energy \( F \) to update beliefs:
     \[
     F = \text{DKL}[Q(s)||P(s)] - \mathbb{E}_{Q(s)}[\log P(o|s)]
     \]

2. **Policy Selection**:
   - For each policy \( \pi \), compute expected free energy \( G(\pi) \):
     \[
     G(\pi) = \sum_{\tau} \left[ \text{DKL}[Q(s_\tau|\pi)||P(s_\tau)] + \mathbb{E}_{Q(s_\tau)}[H(P(o_\tau|s_\tau))] \right]
     \]
   - First term: Risk (divergence from preferred states)
   - Second term: Ambiguity (expected uncertainty)
   - Select policy minimizing \( G(\pi) \)

3. **Control Output**:
   - Sample action from selected policy
   - Generate control signal \( \in \{-1, 0, 1\} \)
   - Scale by `control_strength` parameter
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

### Prior Beliefs (D Matrix)
The **D Matrix** represents the agent's initial beliefs about the state of the ecosystem before any observations are made. It is crucial for setting the starting point of the inference process.

- **Description**: Prior beliefs \( D[s] = P(s) \) over the hidden states.
- **Structure**: 1D array with dimensions matching the number of hidden states (3 in this case for LOW, HOMEO, HIGH).
- **Initialization**:
  - Initialized with a slight bias towards the homeostatic state to reflect a natural tendency of the ecosystem to maintain balance.
  - Example Initialization:
    ```python:Scripts/POMDP_ABCD.py:POMDPMatrices.initialize_prior_beliefs
    def initialize_prior_beliefs(self) -> np.ndarray:
        """Initialize prior beliefs over states
        
        Returns:
            D[s] = P(s) with slight HOMEO bias
        """
        priors = np.array([0.33, 0.34, 0.33], dtype=np.float64)
        return priors.reshape(-1)  # Ensure 1D array
    ```
  - **Values**:
    - LOW: 0.33
    - HOMEO: 0.34
    - HIGH: 0.33

- **Normalization**: Ensures that the sum of all prior probabilities equals 1.
  ```python:Scripts/POMDP_ABCD.py:POMDPMatrices._validate_matrices
  def _validate_matrices(self, matrices: Dict[str, np.ndarray]) -> None:
      """Validate POMDP matrices meet PyMDP requirements"""
      try:
          # Get arrays directly - they're already numpy arrays, not object arrays
          A = matrices['A']
          B = matrices['B']
          C = matrices['C']
          D = matrices['D']
          
          # Validate A matrix columns sum to 1 with strict tolerance
          if not np.allclose(A.sum(axis=0), 1.0, rtol=1e-10, atol=1e-10):
              raise ValueError(f"A matrix columns must sum to 1: {A.sum(axis=0)}")
          
          # Validate B matrix for each action with strict tolerance
          for a in range(B.shape[2]):
              if not np.allclose(B[:,:,a].sum(axis=0), 1.0, rtol=1e-10, atol=1e-10):
                  raise ValueError(f"B matrix not normalized for action {a}: {B[:,:,a].sum(axis=0)}")
          
          # Validate C and D are probability distributions with strict tolerance
          for name, M in [('C', C), ('D', D)]:
              if not np.allclose(M.sum(), 1.0, rtol=1e-10, atol=1e-10):
                  raise ValueError(f"{name} matrix must sum to 1: {M.sum()}")
              if not np.all(M >= 0):
                  raise ValueError(f"{name} matrix contains negative values")
              if not np.all(np.isfinite(M)):
                  raise ValueError(f"{name} matrix contains non-finite values")
              
          # Validate shapes
          if A.shape != (3, 3):
              raise ValueError(f"A matrix should be (3,3), got {A.shape}")
          if B.shape != (3, 3, 3):
              raise ValueError(f"B matrix should be (3,3,3), got {B.shape}")
          if C.shape != (3,):
              raise ValueError(f"C matrix should be (3,), got {C.shape}")
          if D.shape != (3,):
              raise ValueError(f"D matrix should be (3,), got {D.shape}")
          
      except Exception as e:
          self.logger.error(f"Matrix validation error: {str(e)}")
          raise
  ```

## Matrix Validation
To ensure the integrity of the POMDP model, all matrices must satisfy specific validation criteria. This includes ensuring that probability distributions are properly normalized and that no invalid values (such as negatives or non-finite numbers) exist within the matrices.

- **A Matrix**:
  - Columns must sum to 1.0.
  - No negative or non-finite values.
  
- **B Matrix**:
  - For each action, the corresponding transition matrix must have columns summing to 1.0.
  - No negative or non-finite values.

- **C and D Vectors**:
  - Must sum to 1.0.
  - No negative or non-finite values.

Example validation function: