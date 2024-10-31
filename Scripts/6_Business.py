npath = './ActInf_BioFirm_v_01.ipynb'
opath = './'

!pip install nbconvert

import nbconvert
import os
from traitlets.config import Config
from nbconvert.preprocessors import Preprocessor

class CodeBlockPreprocessor(Preprocessor):
    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'code':
            cell['source'] = f"```python\n{cell['source']}\n```"
        return cell, resources

# Define custom CSS for code blocks
custom_css = """
<style>
    pre {
        background-color: #f5f5f5;
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 10px;
        font-family: monospace;
        font-size: 14px;
        line-height: 1.4;
        overflow-x: auto;
    }
</style>
"""

# Configure nbconvert
c = Config()
c.HTMLExporter.preprocessors = [CodeBlockPreprocessor]
c.HTMLExporter.exclude_input_prompt = True
c.HTMLExporter.exclude_output_prompt = True

# Create HTML exporter with custom config
html_exporter = nbconvert.HTMLExporter(config=c)

# Add custom CSS to the template
html_exporter.template_name = 'classic'
html_exporter.template.extra_css = custom_css

# Convert notebook to HTML
notebook_path = npath # Update this path
output_path = opath

(body, resources) = html_exporter.from_filename(notebook_path)

# Save HTML file
html_filename = os.path.join(output_path, 'notebook.html')
with open(html_filename, 'w', encoding='utf-8') as f:
    f.write(body)

print(f"Conversion complete. HTML saved at: {html_filename}")

# Optional: Convert HTML to PDF using Google Chrome's print function
from google.colab import files
files.download(html_filename)

from openai import OpenAI
import numpy as np
import pandas as pd


pro_forma = """Business Model: Innovative Solutions Inc.
Mission Statement
To revolutionize [industry] through cutting-edge technology and ethical practices, while maximizing stakeholder value and societal impact.
Organizational Structure
Our company operates with a committee-based structure to ensure efficient decision-making and specialized focus across key areas:
Executive Committee
Research & Development (R&D) Committee
Ethics & Safety Committee
Financial Committee
Marketing Committee
Staff Allocation
Each employee contributes to the operations of their respective committee, fostering expertise and streamlined processes.
Committee Responsibilities
Executive Committee
Strategic planning and goal-setting
Overall company management and leadership
Inter-committee coordination and resource allocation
R&D Committee
Product innovation and development
Technology research and implementation
Quality assurance and continuous improvement
Ethics & Safety Committee
Ethical guidelines development and enforcement
Safety protocols and risk management
Compliance with industry regulations and standards
Financial Committee
Budgeting and financial planning
Investment strategies and capital allocation
Financial reporting and analysis
Marketing Committee
Brand development and management
Market research and customer insights
Sales strategies and customer acquisition
Operational Model
Ideation and Research: R&D Committee generates innovative concepts.
Ethical Review: Ethics & Safety Committee assesses potential impacts.
Financial Feasibility: Financial Committee evaluates economic viability.
Development: R&D Committee creates prototypes or services.
Marketing Strategy: Marketing Committee develops go-to-market plans.
Executive Approval: Executive Committee provides final authorization.
Launch and Monitoring: All committees collaborate on implementation and performance tracking.
Key Performance Indicators (KPIs)
Revenue growth
Customer satisfaction scores
Innovation index (new products/services per year)
Ethical compliance rate
Return on investment (ROI)
Market share
Funding and Revenue Model
Initial funding through [venture capital/angel investors/bootstrapping]
Revenue streams: [product sales/service subscriptions/licensing]
Profit sharing model among stakeholders
Growth Strategy
Expand product/service offerings
Enter new markets and geographic regions
Form strategic partnerships and collaborations
Continuous talent acquisition and development
Risk Management
Regular risk assessments by Ethics & Safety Committee
Diversification of product/service portfolio
Robust cybersecurity measures
Ongoing market trend analysis"""


roles = ['executive','r&d','ethics','financial','marketing']

import openai

YOUR_API_KEY = "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"
client = openai.OpenAI(api_key=YOUR_API_KEY)

# List of prompts to send to the LLM
prompts = [
    "Based on the provided pro forma business model for Innovative Solutions Inc., please elaborate on the specific responsibilities, processes, and interactions for each of the five committees (Executive, R&D, Ethics & Safety, Financial, and Marketing). Include details on how these committees would collaborate and make decisions in a real-world scenario.",
    "For each of the five committees (Executive, R&D, Ethics & Safety, Financial, and Marketing) in our business model, generate 5 distinct actions that an AI agent representing that committee could take. These actions should be in the form of prompts that the agent can send to an LLM to accomplish its tasks. Ensure that these actions are specific, relevant to the committee's responsibilities, and diverse in their approach to problem-solving.",
    "Given that each agent receives 5 observations per timestep (4 from other agents and 1 from itself), where the observations from other agents are integers 1 (poor), 2 (moderate), or 3 (good), and the self-observation is the index of the last action taken (0-4), provide a framework for interpreting these observations. How should an agent weigh these inputs to infer the quality of its own work?",
    "Describe a method for an agent to infer its hidden state factor 'quality' (as a categorical probability distribution of 'low' and 'high') based on the observations it receives. How should the agent update its belief about its work quality given the feedback from other agents and its own last action?",
    "Given an agent's current belief about its work quality (hidden state) and the set of 5 possible actions, propose a decision-making process for the agent to select its next action. How should the agent balance exploration (trying new actions) with exploitation (choosing actions that have worked well in the past)?",
    """For a single timestep in the simulation, describe how all five agents should:
a) Receive and interpret observations
b) Update their beliefs about their work quality
c) Select and execute their next action
d) Generate observations for other agents based on their action
Provide a step-by-step process that can be repeated for each timestep of the simulation.""",
    "Performance Evaluation Prompt"
]

# Function to send a prompt to the LLM and get a response
def send_prompt_to_llm(prompt, industry):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
        {"role": "system", "content": f"You are a skilled business professional in the industry of {industry}"},
        {"role": "user", "content": f"""{prompt}
         """}
          ],
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def send_prompt_to_llm(prompt,industry):
  # Send the request to the GPT-4o mini model based on which agent
  response = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[
        {"role": "system", "content": f"You are a skilled business professional in the industry of {industry}"},
        {"role": "user", "content": f"""{prompt}"""}
      ],
      temperature=0.7,  # controls randomness vs. coherence
      seed = 1
  )
  return str(response.choices[0].message.content)

# Iteratively send prompts and store responses

industry = "agriculture"

responses = {}
for prompt in prompts:
    print(f"Sending prompt: {prompt}")
    response = send_prompt_to_llm(prompt=prompt, industry=industry)
    responses[prompt] = response
    print(f"Response received: {response[:50]}...")  # Print first 50 characters
    print()

# Print all responses
print("All responses:")
for prompt, response in responses.items():
    print(f"\n{prompt}:")
    print(response)
    
    
    