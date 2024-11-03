"""
This script constructs and instantiates a global Biofirm agent whose observation inputs are the full set of binary indicators representing whether or not
the environmental variables are within their respective constraints.
The agent prefers with full probability to see the environmental variables within their restraints, i.e. 1 values are the preferred values.
For each timestep t, the current set of binary indiciators from the environment via `env.constraint_verification` are passed as observations to the biofirm agent.
The agent then infers a single null policy and the expected free energy of that policy is tracked.
"""
import numpy as np
import pandas as pd
import pymdp
from pymdp import utils
from pymdp.maths import softmax
from pymdp.agent import Agent
import math
import random
np.random.seed(0)
random.seed(0)
import copy

variables = 10
# Construct hierarchical agent taking into account all binary indicators as observations
A = utils.obj_array(variables)
for i in range(len(A)):
  A[i] = np.zeros( ( 2,2 ))    # initialize likelihood between 2 possible observations, 2 hidden state levels ('bad','good')
  A[i][0,0] = 1.0              # P(o='not in constraint'|s='bad') = 1.0
  A[i][1,1] = 1.0              # P(o='within constraint'|s='good') = 1.0
  #print(f"A[{i}] (normalized = {utils.is_normalized(A[i])}) = {A[i]}")
print(f"A ({utils.is_normalized(A)})")
B = utils.obj_array(1)
B[0] = np.zeros( (2, 2, 1 ))
for i in range(len(B[0])):
  for j in range(len(B[0])):
    B[0][i,j] = 0.5           # uncertainty over impact of 'do nothing' to impact hidden state (i.e. irrelevant)
print(f"B[0] ({utils.is_normalized(B[0])} = {B[0]}")
C = utils.obj_array(variables)
for i in range(len(C)):
  C[i] = np.array([0, 1])    # always prefer 1
print(f"C ({utils.is_normalized(C)}) ")
D = utils.obj_array(1)
D[0] = np.array([0.5, 0.5])
print(f"D ({utils.is_normalized(D)}) ")

biofirm = Agent(A=A, B=B, C=C, D=D, inference_algo='MMP',policy_len=1,inference_horizon=2,sampling_mode='full',action_selection='stochastic')
obs = [0,0,0,0,0,0,0,0,0,0]

g_pos_list = []
obs_list = []


# Run various psuedo-simulations to collect observations and compute expected free energy values
for i in range(5):
  for j in range(2):
      obs = copy.deepcopy(obs)
      obs[i] = 0
      qs = biofirm.infer_states(obs)
      q_pi, neg_efe = biofirm.infer_policies()
      action_sampled_id = biofirm.sample_action()
      print(f"env.constraint_verification = {obs} -> F = {biofirm.F}, G = {neg_efe * -1}")
      g_pos_list.append(biofirm.G[0]*-1)
      obs_list.append(obs)
for i in range(3):
  obs = copy.deepcopy(obs)
  #obs[i] = 0
  qs = biofirm.infer_states(obs)
  q_pi, neg_efe = biofirm.infer_policies()
  action_sampled_id = biofirm.sample_action()
  print(f"env.constraint_verification = {obs} -> F = {biofirm.F}, G = {neg_efe * -1}")
  g_pos_list.append(biofirm.G[0]*-1)
  obs_list.append(obs)
for i in range(1):
  for j in range(10):
    obs = copy.deepcopy(obs)
    obs[j] = 1
    qs = biofirm.infer_states(obs)
    q_pi, neg_efe = biofirm.infer_policies()
    action_sampled_id = biofirm.sample_action()
    print(f"env.constraint_verification = {obs} -> F = {biofirm.F}, G = {neg_efe * -1}")
    g_pos_list.append(biofirm.G[0]*-1)
    obs_list.append(obs)
for i in range(3):
  obs = copy.deepcopy(obs)
  obs[i] = 1
  qs = biofirm.infer_states(obs)
  q_pi, neg_efe = biofirm.infer_policies()
  action_sampled_id = biofirm.sample_action()
  print(f"env.constraint_verification = {obs} -> F = {biofirm.F}, G = {neg_efe * -1}")
  g_pos_list.append(biofirm.G[0]*-1)
  obs_list.append(obs)
print(qs)


print(g_pos_list)
print(len(obs_list))
print(len(g_pos_list))
print(obs_list)

import matplotlib.pyplot as plt
import numpy as np

variable_names = ['forest_health', 'carbon_sequestration', 'wildlife_habitat_quality',
       'water_quality', 'soil_health', 'invasive_species_count',
       'riparian_buffer_width', 'biodiversity_index', 'hazard_trees_count',
       'recreational_access_score']
#variable_names = env.data.copy().drop(columns=['timestep']).columns

# Create figure and subplots with shared x-axis
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 4))

# Top subplot: g_pos_list line plot
timesteps = list(range(len(g_pos_list)))
ax1.plot(timesteps, g_pos_list, 'o-', color='blue')
ax1.set_ylabel('Expected Free Energy')
ax1.set_title('Expected Free Energy based on Environmental Constraint Indicators')
ax1.grid(True)

# Bottom subplot: Binary indicators scatter plot
for t in range(len(obs_list)):  # Outer loop over timesteps
    for i in range(len(variable_names)):  # Inner loop over variables
        color = 'blue' if obs_list[t][i] == 1 else 'red'
        ax2.scatter(t, variable_names[i], color=color)

ax2.set_xlabel('Timestep')
ax2.set_ylabel('Indicator Variables')

# Adjust layout to prevent overlap
plt.tight_layout()
plt.show()