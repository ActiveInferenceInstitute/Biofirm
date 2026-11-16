# Biofirm model contract

Biofirm models an ecosystem as a bounded, partially observed control system.
The public implementation lives under `src/biofirm`; the JSON files under
`One_Earth/` and `Bio_Perplexity/` are source datasets and research prompts.

## State and transition

Each variable declares an initial value, target, physical minimum and maximum,
unit, trend, noise scale, and control strength. A transition is computed once
per timestep:

```text
x[t + 1] = clip(x[t] + trend + relationship(x[t]) + control[t] + noise[t],
                minimum, maximum)
```

Relationship effects are directed linear contributions from normalized source
deviations. Configuration validation rejects missing fields, unknown variables,
non-finite numbers, invalid ranges, and cycles. Each variable may configure a
symmetric `observation_bins` count (an odd number >= 3); the default of 3
preserves the below/at/above observation model, while larger odd counts (e.g. 5)
discretize the state around the target more finely.

Variable and relationship mappings are canonicalized by name at construction,
including dependency accumulation and random-draw assignment. Hash-equivalent
configurations replay in that order; preserve original artifacts and runtime
provenance for earlier insertion-order-dependent runs.

## Active inference

The active-inference controller discretizes each variable into observation
states around the target using the variable's configured `observation_bins`. It
constructs the PyMDP `A`, `B`, `C`, and `D` matrices with JAX-compatible arrays,
uses an empirical prior, performs state inference followed by policy inference,
and records the effective control action. The action space remains the three-step
decrease/hold/increase contract. Action IDs are `0` for control below `-1e-12`,
`1` within `[-1e-12, 1e-12]`, and `2` above `1e-12`. Custom and generated decisions
must satisfy the same finite, bounded control/action rule before a transition.
Deterministic action selection is the default. Stochastic selection requires a
configured seed and uses a JAX PRNG key.

The generative-model structure is specified in Generalized Notation Notation at
[`models/biofirm_ecosystem_variable.gnn.md`](models/biofirm_ecosystem_variable.gnn.md);
[`models/README.md`](models/README.md) records the pinned upstream revision and
the drift guard that keeps the specification, `src/biofirm/gnn.py`, and
`src/biofirm/pymdp.py` in agreement.

The simulation history contains the observed state, controls, action IDs,
beliefs, variational free energy, expected free energy, policy distributions,
metrics (including a `posterior_entropy` uncertainty term derived from
controller beliefs), and the individual transition terms. A failure in matrix
operations or controller inference is surfaced with variable context.

## Other controllers

The proportional slide-rule controller computes bounded error feedback with
configurable response and damping. The random baseline uses a seeded generator
and records each selected action. The business controller evaluates a typed
committee policy and applies the chosen action's configured controls.

## Reproducibility

```bash
biofirm validate
biofirm simulate --steps 20 --seed 7 --controller active-inference --output run.json
```

The same configuration, seed, and controller produce the same JSON history.
Runtime files are written only when an output path is explicitly supplied.

Serialized simulation results use schema version `1` and include the canonical
configuration snapshot and SHA-256 hash, controller name, package version, seed,
summary, and immutable transition records. Consumers must validate the complete
document before analysis or visualization; missing, extra, non-finite, or
tampered fields are errors.
Validation also checks initial values and zero initial controls, bounds noise by
three configured standard deviations, reconstructs clipped next-state values and
recomputes posterior entropy from stored beliefs. Rejected historical documents
remain evidence and must not be rewritten to pass these checks; keys and schema
version remain unchanged.
