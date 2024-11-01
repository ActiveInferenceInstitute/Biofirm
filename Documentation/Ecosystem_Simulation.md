Ecosystem_Simulation.py Overview

The Ecosystem_Simulation.py file is a Python script designed to simulate a natural resource environment, focusing on the interactions between various ecological variables over time. Here’s a step-by-step breakdown of what the code does:

1. **Imports and Setup**
   - The script begins by importing necessary libraries such as `pandas`, `numpy`, and others for data manipulation, logging, and visualization.
   - It adds the project root to the Python path to facilitate importing modules from the project structure.

2. **Simulation Parameters**
   - A dictionary named `SIMULATION_PARAMS` is defined, which contains parameters for the simulation, including the number of timesteps, control modes, and visualization settings.

3. **EnvironmentState Dataclass**
   - A `dataclass` named `EnvironmentState` is defined to encapsulate the state of the environment at any given timestep. It includes attributes like timestamp, timestep number, variables, constraints, and metadata.
   - The `to_dict` method converts the state into a dictionary format for serialization.

4. **Environment Class**
   - The core of the simulation is encapsulated in the `Environment` class, which simulates the ecosystem.
   - **Initialization**: The constructor (`__init__`) initializes the environment, sets up logging, creates output directories, and loads configuration settings from a specified file.
   - **Logging**: The `_log_simulation_settings` method logs the simulation settings for tracking purposes.

5. **Configuration Initialization**
   - The `_init_from_config` method initializes variables from the configuration file, setting their initial values and identifying controllable variables.
   - The `_init_tracking_system` method sets up a DataFrame to track the history of variable changes and initializes constraints based on the configuration.

6. **Simulation Steps**
   - The `step` method executes a single timestep of the simulation, updating controllable variables based on input adjustments, updating dependent variables, and recording the state.
   - The `_update_controllable_variables` method applies adjustments to the controllable variables while ensuring they remain within specified bounds.

7. **State Management**
   - The `_record_state` method captures the current state of the environment and saves it to a historical data file in JSON format.
   - The `_verify_constraints` method checks if the current values of the variables are within defined constraints, returning a list of state indicators.

8. **Simulation Execution**
   - The `run_simulation` method orchestrates the entire simulation process, executing a specified number of timesteps and applying control strategies (either random or active inference).
   - It initializes a `BiofirmAgent` if the active inference strategy is selected, which helps in making decisions based on the current state of the environment.

9. **Comparison of Strategies**
   - The `run_comparison` method runs simulations using both random control and active inference strategies, generating visualizations to compare the results.

10. **Visualization and Metrics**
   - The script includes methods for generating visualizations of the simulation results and saving metrics related to the simulation's performance.
   - The `_generate_visualizations` method creates plots to visualize the data collected during the simulation.

11. **Main Execution Block**
   - The script includes a main execution block that initializes the environment and runs the comparison of both strategies when the script is executed directly.

12. **Error Handling**
   - Throughout the code, there are try-except blocks to handle exceptions gracefully, logging errors and providing feedback if something goes wrong during the simulation.

Summary
Overall, the Ecosystem_Simulation.py script is a comprehensive framework for simulating and analyzing the dynamics of an ecosystem, allowing for the exploration of different control strategies and their impacts on various environmental variables. It emphasizes logging, state management, and visualization to facilitate understanding and analysis of the simulation results.