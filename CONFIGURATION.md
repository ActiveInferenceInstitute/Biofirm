# Biofirm configuration reference

Biofirm runs are configured by a single JSON document. Every command loads and
strictly validates the same schema: `biofirm validate --config path.json` is
the fastest way to check a file before running it.

When no `--config` is supplied, the packaged default is used
(`src/biofirm/data/ecosystem.json`). Validation rejects unknown fields,
non-finite numbers, invalid ranges, duplicate or alias-colliding variable
names, dependency cycles, and incomplete action vectors.

## Top-level keys

| Key | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `name` | string | yes | — | Configuration name, recorded in artifacts. |
| `variables` | object | yes | — | Map of variable name to [variable definition](#variable-definition). At least one variable is required. |
| `relationships` | object | no | `{}` | Map of target variable to [relationship definition](#relationship-definition). |
| `controller` | object | no | defaults below | [Controller definition](#controller-definition). |
| `output` | object | no | defaults below | [Output definition](#output-definition). |
| `seed` | integer | no | `7` | Default seed for reproducible runs. |

## Variable definition

Each key under `variables` is the variable name; the value is an object:

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `initial` | number | yes | — | Starting value. Must lie within `[minimum, maximum]`. |
| `target` | number | yes | — | Homeostatic target. Must lie within `[minimum, maximum]`. |
| `minimum` | number | yes | — | Physical lower bound. Must be below `maximum`. |
| `maximum` | number | yes | — | Physical upper bound. Must be above `minimum`. |
| `trend` | number | no | `0.0` | Per-timestep drift term added to the state. |
| `noise` | number | no | `0.0` | Standard deviation of transition noise; must be >= 0. Noise draws are clipped to ±3 standard deviations. |
| `control_strength` | number | no | `1.0` | Maximum magnitude of a control signal for this variable; must be >= 0. |
| `observation_bins` | odd integer >= 3 | no | `3` | Number of symmetric observation bins. `3` reproduces the below/at/above model; larger odd counts (e.g. `5`) discretize the state around the target more finely. |
| `unit` | string | no | `"index"` | Human-readable unit, recorded in artifacts. |
| `aliases` | array of strings | no | `[]` | Alternative names accepted when parsing bioregion text. Must be unique (case-insensitive) and must not repeat the variable name. |

## Relationship definition

Each key under `relationships` is a target variable; the value is an object:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `dependencies` | object | yes | Map of source variable name to a linear coefficient. |

A relationship contributes

```text
coefficient * ((source_value - source_target) / source_span) * target_span
```

to the target's transition, where `span = maximum - minimum`. Coefficients
are illustrative model parameters, not calibrated ecological claims. Every
source must be an existing variable, and the directed dependency graph must be
acyclic.

## Controller definition

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `name` | string | no | `"active-inference"` | One of `active-inference`, `slide-rule`, `random`, `business`. |
| `stochastic` | boolean | no | `false` | When true, action selection is stochastic (requires a seed). |
| `response_rate` | number in `(0, 1]` | no | `0.5` | Slide-rule response gain. |
| `damping` | number in `[0, 1)` | no | `0.2` | Slide-rule damping. |
| `random_seed` | integer or null | no | `null` | Optional seed for stochastic selection. |

The active-inference controller builds the PyMDP `A`, `B`, `C`, and `D`
matrices with JAX-compatible arrays using each variable's `observation_bins`.
The action space is the fixed three-step decrease/hold/increase contract.

## Output definition

| Field | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `directory` | string | no | `"artifacts"` | Directory used when a command writes by default. |
| `write_by_default` | boolean | no | `false` | When true, `simulate`/`sweep` write an artifact even without `--output`. |

## Example

```json
{
  "name": "river-ecosystem",
  "seed": 11,
  "variables": {
    "biodiversity": {
      "initial": 50.0,
      "target": 50.0,
      "minimum": 0.0,
      "maximum": 100.0,
      "noise": 0.5,
      "control_strength": 2.0,
      "unit": "index"
    }
  },
  "relationships": {
    "biodiversity": {
      "dependencies": { "water_quality": 0.1 }
    }
  },
  "controller": {
    "name": "active-inference",
    "stochastic": false
  },
  "output": {
    "directory": "artifacts",
    "write_by_default": false
  }
}
```

`biofirm scenarios` takes multiple `--config` flags and runs the same seeds
across each variant. The canonical JSON serialization of a validated
configuration is hashed (SHA-256) and snapshotted into every simulation
artifact so runs can be audited against the exact configuration that produced
them.
