# Methods

Each configured variable has physical bounds, an initial value, a target, and parameters for its evolution. At each timestep the simulator adds trend, directed relationship effects, effective controller action, and noise, then clips the result to the allowed interval [@model]. Relationship effects use normalized source deviations and the configuration validator rejects cycles. A stable ordering of variables and relationships binds random draws and accumulation to canonicalized configuration.

The active-inference controller discretizes states and observations around each target. It constructs likelihood, transition, preference, and initial-state prior arrays specified by the GNN model, performs state and policy inference, and records the effective decrease, hold, or increase decision [@gnn; @model]. The package also supplies proportional and random controllers and a typed committee-policy path.
