https://www.perplexity.ai/search/i-am-writing-a-simulation-whic-oTghHbfcRcONlJtO.LpWdA

```
I am writing a simulation which operates in timesteps and involves 3 Active Inference agents who each try to maintain the values of the variables in their environment (collected at each timestep as time-series variables) between each variable's respective target constraint range. The time-series variables have unknown relationships between one another. At each timestep, a new row of the data is recorded and a list is created which contains one indicator for each variable denoting whether the value of the variable is higher, lower, or within the variable's respective target range. The agents receive these indicators as observations to infer hidden states denoting, for each variable, whether the state is higher, lower, or homeostatic. Each of agents which has 3 actions ("MAINTAIN", "DECREASE", "INCREASE") to modify its respective variable. The agent strongly prefers to see each variable within its target range. This makes the entire simulation like a homeostasis machine, where the agents try to keep all variables in homeostasis. Are there any similar systems, applications, or simulations similar to my simulation?
```


Your described simulation bears similarities to several systems and applications across different domains. Let me break down the comparable systems:

## Biological Homeostatic Systems

**Physiological Control Systems**
The multi-agent homeostatic control you're describing closely resembles biological regulatory networks, particularly how the human body maintains various physiological parameters. The endocrine system, for example, uses multiple glands acting as agents to maintain hormonal balance through similar increase/decrease/maintain actions.

**Artificial Homeostatic Systems**
Your system shares characteristics with artificial homeostatic hormone systems (AHHS), which are bio-inspired control architectures where virtual hormones regulate system parameters through decentralized control mechanisms.

## Industrial Applications

**Process Control Systems**
Industrial control systems, particularly in chemical processing plants, employ multiple PID controllers that work simultaneously to maintain different variables within specified ranges. These systems often deal with interconnected variables where changes in one parameter affect others, similar to your unknown variable relationships.

## Environmental Control Systems

**Building Management**
Modern building automation systems use multiple controllers to maintain various environmental parameters (temperature, humidity, CO2 levels) within comfort zones, dealing with interconnected variables and multiple control points.

## Key Similarities to Your System

Your simulation shares these fundamental characteristics with the above systems:

- Multiple autonomous controllers (agents)
- Homeostatic target ranges
- Interdependent variables
- Discrete action spaces
- Observation-based state inference
- Decentralized control architecture

## Unique Aspects

What makes your system particularly interesting is:

- The use of Active Inference for agent decision-making
- The explicit modeling of unknown variable relationships
- The discrete tri-state representation of variables (high/low/homeostatic)
- The combination of time-series data with categorical state inference

## Related Research Areas

**Multi-Agent Systems**
Your simulation aligns with research in distributed control systems where multiple agents must coordinate without explicit communication to maintain system stability.

**Homeostatic AI**
The field of artificial homeostatic systems, which aims to create self-regulating artificial systems inspired by biological homeostasis, is particularly relevant to your work.

**Complex Systems Control**
Your simulation relates to research in controlling complex systems with multiple interconnected variables and uncertain relationships between parameters.