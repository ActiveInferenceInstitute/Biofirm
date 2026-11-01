# GNN spec: Biofirm ecosystem variable control model

## GNNSection
ActInfBiofirmEcosystemVariable

## GNNVersionAndFlags
GNN v1.1

## ModelName
Biofirm Ecosystem Variable Control Model

## ModelAnnotation
Generative-model specification for the active-inference controller in
`src/biofirm/controllers.py`, built by `src/biofirm/pymdp.py`.

One bounded scalar ecological variable is discretized into an odd number
(`observation_bins`, default 3) of symmetric levels around its target:
`below target`, `at target`, `above target` for the default three bins. The
variable is a single hidden-state factor; the discretized level is the single
observation modality and the likelihood is the identity mapping (the
observation *is* the discretized level). The three controls are the fixed
decrease/hold/increase contract: action `a` shifts the level by `a - 1` bins and
clips at the physical minimum and maximum. Preferences are log-preferences that
peak at the target level; the initial-state prior is uniform.

This file is the source of truth for the *default* three-bin instantiation and
for the structural contract that every other odd `observation_bins` value
preserves: one factor, one identity-likelihood modality, the same three
controls, a uniform prior, a target-peaked preference vector, and the clipped
shift transition. `observation_bins` is declared per variable in the ecosystem
configuration (`CONFIGURATION.md`); the runtime generalization is verified by
`tests/test_gnn.py` against `build_active_inference_matrices`.

Transition tensor orientation: Biofirm stores `B[next_state, previous_state,
action]`, the canonical GNN orientation (the same order PyMDP 1.x expects).
Transition equation per variable per timestep:
`x[t+1] = clip(x[t] + trend + relationship(x[t]) + control[t] + noise[t],
minimum, maximum)`.

Claim boundary: the discretization and controller are implemented and tested,
but the ecological variables, targets, and relationship coefficients are
illustrative configuration, not calibrated ecological evidence.

## StateSpaceBlock
# Hidden state factor (one factor): discretized level around the target.
s_bin[3,1,type=int]                  # hidden factor 0: below/at/above target

# Observation modality (one): the discretized level.
o_level[3,1,type=int]                # modality 0: discretized variable level

# Likelihood (identity): A[observation, state].
A_level[3,3,type=float]

# Transition tensor: B[next_state, previous_state, action].
B_bin[3,3,3,type=float]

# Log-preference vector over observation levels.
C_level[3,type=float]

# Initial-state prior over levels.
D_bin[3,type=float]

# Controls for the single controllable factor: decrease/hold/increase.
u_control[3,1,type=int]              # discrete control index (3 controls)
π_control[3,type=float]              # policy posterior over the 3 controls

# Free energy and time.
F[1,type=float]
G[1,type=float]
t[1,type=int]

## Connections
# Prior initializes the hidden factor.
D_bin>s_bin

# Identity likelihood: the modality depends on the level alone.
s_bin>A_level
A_level>o_level

# Transitions depend on the level and its control.
s_bin>B_bin
u_control>B_bin
B_bin>s_bin

# Preferences and policy selection.
C_level-o_level
G>π_control
π_control>u_control

## InitialParameterization
# A: identity likelihood, column-stochastic.
A_level={(1.0,0.0,0.0),(0.0,1.0,0.0),(0.0,0.0,1.0)}

# B: transition tensor in canonical (next_state, previous_state, action) order.
# Each next-state slice is a (previous_state, action) matrix; the tensor is
# column-stochastic over the next_state axis. Action 0 decreases the level by
# one bin, action 1 holds it, action 2 increases it by one bin, clipped at the
# first and last bin.
B_bin={
  ( (1.0,1.0,0.0),
    (1.0,0.0,0.0),
    (0.0,0.0,0.0) ),   # next_state 0
  ( (0.0,0.0,1.0),
    (0.0,1.0,0.0),
    (1.0,0.0,0.0) ),   # next_state 1
  ( (0.0,0.0,0.0),
    (0.0,0.0,1.0),
    (0.0,1.0,1.0) )    # next_state 2
}

# C: log-preferences peak at the target level (index 1 of 3).
C_level={-1.0,2.0,-1.0}

# D: uniform prior over levels.
D_bin={0.3333333333333333,0.3333333333333333,0.3333333333333333}

## Equations
# Belief update (state inference):
#   Q(s) = softmax(ln(D) + ln(A^T o))
# Identity likelihood and uniform prior, so Q(s) tracks the observed level.
# Policy posterior:
#   Q(π) = softmax(-G(π))
# Transition (clipped shift by one bin):
#   s' = clip(s + a - 1, 0, num_bins - 1)
# Column-stochastic normalization:
#   sum_o A[o, s] = 1 for every state s
#   sum_{s'} B[s', s, a] = 1 for every state s and control a

## Time
Dynamic
DiscreteTime=t
ModelTimeHorizon=Unbounded

## ActInfOntologyAnnotation
s_bin=HiddenStateFactor0
o_level=ObservationModality0
A_level=LikelihoodMatrixModality0
B_bin=TransitionMatrixFactor0
C_level=LogPreferenceVectorModality0
D_bin=PriorOverHiddenStatesFactor0
u_control=Action
π_control=PolicyVector
t=Time

## ModelParameters
model_id: biofirm_ecosystem_variable
num_factors: 1
num_hidden_states: 3
num_modalities: 1
num_obs: 3
num_actions: 3
num_timesteps: Unbounded
conditional_independence: true
observation_bins_default: 3
observation_bins_rule: odd integer >= 3
transition_axis_order: next_state,previous_state,action

## Footer
Biofirm Ecosystem Variable Control Model — GNN v1.1 structural spec.
Default three-bin instantiation; every odd `observation_bins` value preserves
the declared structure. Illustrative ecological configuration, not calibrated
ecological evidence.

## Signature
pending
