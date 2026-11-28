# Implementation evidence

A versioned simulation record stores its canonical configuration and hash, controller and seed, transition records, and derived summaries [@artifacts]. Consumers validate the complete document before analyzing it. They can check control bounds, reconstruct the clipped state update, and recalculate entropy from recorded beliefs [@model]. These checks establish internal artifact consistency. They do not establish that the parameters measure ecological processes in a field setting.

The model specification is compared against code by the tests for supported observation-bin counts. The gate names separate arms for package checks, documentation validation, and pinned specification conformance [@gate].
