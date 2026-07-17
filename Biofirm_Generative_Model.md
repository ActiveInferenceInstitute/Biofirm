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
non-finite numbers, invalid ranges, and cycles.

## Active inference

The active-inference controller discretizes each variable into below-target,
target, and above-target observations. It constructs the PyMDP `A`, `B`, `C`,
and `D` matrices with JAX-compatible arrays, uses an empirical prior, performs
state inference followed by policy inference, and records the selected action.
Deterministic action selection is the default. Stochastic selection requires a
configured seed and uses a JAX PRNG key.

The simulation history contains the observed state, controls, action IDs,
beliefs, variational free energy, expected free energy, policy distributions,
metrics, and the individual transition terms. A failure in matrix operations
or controller inference is surfaced with variable context.

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
