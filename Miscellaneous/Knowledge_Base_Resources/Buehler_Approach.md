- **SciAgents (Buehler et. al, 2024) notes + Knowledge Graph construction**
    - **SciAgents (Buehler et. al, 2024):**
        - How are the agents constructed? https://www.perplexity.ai/search/how-are-the-agents-constructed-X6bnVj94SH.s9WeJ3Y.h1A How are the knowledge graphs constructed? https://www.perplexity.ai/search/explain-the-knowledge-graphs-a-qOGUg7kOSrWhwIqkqjsWhA
        - From github .py digging:
            - Seems to all trace back to a class of agent they define which is just a holder for conversational history and roles for LLM prompting?
            - No mention explicitly of ‘reinforcement learning’, ‘reward’, ‘Markov’,
        - Section 1 Introduction/overview
            - “creation of systems capable of autonomously advancing scientific understanding by exploring novel domains, identifying complex patterns, and uncovering previously unseen connections in vast scientific data”
                1. use large-scale ontological knowledge graphs to organize/interconnect diverse scientific concepts
                2. suite of LLMs and data retrieval tools
                3. multi-agent systems with in-situ learning capabilities
                - Autonomously reveal interdisciplinary relationships; generate/refine research hypotheses, underlying mechanisms, design principles, unexpected material properties
            - “traditional”/conventional human-driven methods inadequate for vast amount of existing scientific data for multi-disciplinary areas (ex. bio-inspired materials + extract principles → engineering applications)
            - new LLMs have been used to generate new ideas/hypotheses/solutions. But **limitations** include producing **inaccurate responses when dealing with questions outside of their initial training scope + concerns about accountability, explainability, transparency, leading to misleading/harmful content**
            - **‘In-context learning’ as solution strategy**: LLMs can adapt its responses based on context embedded within the prompt, derived from various sources — external knowledge integration leading to more precise responses [27, 28, 29] — goal being to **develop robust mechanisms for accurate retrieval and integration of relevant knowledge that enables LLMs to interpret and synthesize information pertinent to specific tasks, particularly in the realm of scientific discovery**
                - [27] Wei, J. et al. Chain-of-thought prompting elicits reasoning in large language models. Advances in neural
                information processing systems 35, 24824–24837 (2022).
                [28] White, J. et al. A prompt pattern catalog to enhance prompt engineering with chatgpt. arXiv preprint
                arXiv:2302.11382 (2023).
                [29] Zhou, Y. et al. Large language models are human-level prompt engineers. arXiv preprint arXiv:2211.01910
                (2022).
                [30] Sun, J. et al. Think-on-graph: Deep and responsible reasoning of large language model with knowledge graph.
                arXiv preprint arXiv:2307.07697 (2023).
            - **Knowledge base construction and strategic info retrieval:** Efficient mining of vast scientific datasets → transform unstructured natural language into structured data, e.g., comprehensive ontological knowledge graphs, which mechanistically breakdown info + offer ontological framework to elucidate interconnectedness of different concepts, **delineated as nodes and edges within the graph**
            - **Team of specialized agents**: single agents fall short of the *series of steps, deep thinking and integration of diverse (sometimes conflicting) information*. Instead, multi-agent systems **pool their capabilities (’division of labor’). Each agent is assigned a distinct role, optimized thru complex prompting strategies to ensure every subtask is tackled with targeted expertise and precision; foster collaboration for hypothesis generation/refinement/evaluation against criteria like novelty and feasibility.**
            - **Ontological knowledge graph used:** focused on biological materials and developed from around 1,000 scientific papers in this domain
            - **Novel Sampling strategy to extract relevant sub-graphs for identifying/understanding key concepts +interrelationships**: guides hypothesis generation, improving accuracy and rooting them in knowledge framework
        - 2 Results and discussion (multi-agent system’s main components and constitutive agents; first approach as pre-programmed AI-AI interactions, second approach fully automated framework of set of self-organizing agents; examples of path generation, hypothesis generation/critique, iterative prompting strategy)
            - Failure of conventional inferences strategies to produce sophisticated reasoning/detail in generated data; instead authors use set of interacting models and assign distinct roles to LLM-based agents with *carefully crafted prompts and in-context learning from graph representation of data*
            - 2.1 Multi-agent system for graph reasoning and scientific discovery
            - **Figure 1: multi-agent model outline:** two strategies
                - A: overview of graph construction (papers → graph construction → zoom-in on graph)
                - B: multi-agent system of pre-programmed interaction sequences between agents
                - C: fully automated, flexible multi-agent framework adapting dynamically to evolving research context
                - *Both systems leverage a sampled path within a global knowledge graph as context to guide the research idea generation process*
                - Agent roles:
                    - Ontologist: defines key concepts and relationships
                    - Scientist 1: crafts detailed research proposal
                    - Scientist 2: expands/refines the proposal
                    - Critic: conducts through review and suggests improvements
                    - Planner: (in second approach) develops detailed plan
                    - Assistant (in second approach): instructed to check novelty of generated research hypotheses
                        
                        ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/f162cbcb-122d-4c00-8425-880628935553/image.png)
                        
            - **1-Path generation**: knowledge graph integrates concepts and knowledge domains → seemingly disconnected hypothesis exploration.
                - Agents provided with a **sub-graph dervied from knowledge graph**. Takes a **random path approach**, infusing path with a richer array of concepts and relationships (instead of previous ‘shortest path’ work where only few concepts were included).
                - Specifically agents are provided two concepts (ex. “silk” and “energy-intensive”). These two concepts can be input by user or randomly selected by model from the knowledge graph.
                - **Figure 2: entire process overview (initial keyword selection or random exploration to path sampling to create subgraph → hierarchical expansion strategy with answer refinement/improvement, enriched with retrieved data, critiqued and amended by identification or critical modeling, simulation, experimental tasks → scientific paper)**
                    - Subgraph forms basis for generating *structured output in **JSON (including hypothesis, outcome, mechanisms, design principles, unexpected properties, comparison, novelty)***
                    - *each component subsequently expanded on with individual prompting yielding additional detail and comprehensive draft*
                    - draft then critically reviewed, including amendments for modeling and simulation priorities (ex. molecular dynamics) and experimental priorities (ex. synthetic biology)
                
                ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/0b4bdc02-4548-4fc3-8f4b-0eeb2f3b5645/image.png)
                
                - Path generation example from initial keywords, i.e. **from keyword 1 (silk) to keyword 2 (energy-intensive)**: generated path provides analytical representation of various concepts’ interconnections (including of seemingly disconnected concepts) → extrapolate, generate ideas
                
                ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/07671aa2-507f-4b93-93fc-09548fa8010b/image.png)
                
            - **2-Deep Insights with LLM-Based Analysis**
                - After initial sub-graph generation phase, agent transitions from static knowledge retrieval to dynamic knowledge generation, *allowing identification of gaps in existing research and proposing new angles of inquiry*
                - Ontologist applies advanced reasoning and inference techniques to synthesize and interpret complex web of data, extracting insights
                - **Figure 3:** results from multi-agent model, produced detailed organized research dev documentation (8,100 words). **Full conversations generated by SciAgents also included in Supplementary Information.**
                - **Figure 4:** knowledge graphs connecting keywords “silk” and “energy-intensive”, extracted from global graph using a) random path and b) shortest path between concepts. **Enhanced sampling invokes additional concepts to be incorporated into agents’ research development.** “Agentic reasoning” assesses ideas and negotiate, *via **adversarial interactions between the agents,** a sound prediction and delineated research ideas.*
                    
                    ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/8628efc5-1580-4923-84ae-6d233508755a/image.png)
                    
                - Example of insights into **ontologist’s identified relationships** — mapping and meaningfully interpreting complex datasets to generate hypotheses. Via refined understnading of relationships between concepts, model can support reasoning in scientific research / propose hypotheses to be explored in next stage
                    
                    ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/b68dec6c-ea12-47b5-a495-77fa2263c821/image.png)
                    
            - **3-Research Hypothesis Generation and Expansion**
                - Here multi-agent system’s effects emerge: agents use knowledge (parsed from graph and refined by ontologist) to propose novel ideas. Each agent is assigned specific role and tasked with synthesizing novel research proposal integrating all key concepts from the knowledge graph.
                - **Scientist_1 role:** delivers detailed (innovative and logically grounded) hypothesis to advance concepts’ understanding/application, then creates proposal addressing **seven key aspects:**
                    - hypothesis, outcome, mechanisms, design principles, unexpected properties, comparison, novelty (criteria which allow for assessment of feasibility / potential impact / innovation areas)
                        - Example: integrating silk with dandelion-based pigments to create biomaterials with enhanced optical and mechanical proprties, stemming from hierarchical organization of silk combined with pigments’ reinforcing effects; this proposal could exhibit mechanical strength reaching up to 1.5 GPa compared to tradition (0.5 to 1.0 GPa). Use of low-temp processing and dandelion pigments is projected to reduce energy consumption by approx 30%.
                        - Scientist_1’s research idea proposal provides foundational abstract for more detailed proposal developed thru subsequent agent interactions.
                        - Scientist_1 prompt:
                        
                        ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/7455ad3e-c390-46e5-b3fa-7d5a3d4bf3e5/image.png)
                        
                - Scientist_2 role: tasked to expand upon and critically assess idea’s components; integrate where possible quantitative scientific info (ex. chemical formulas, numerical values, protein sequences, processing conditions) to enrich proposal’s depth and accuracy. Scientist_2 also *comments on specific modeling and simulation techniques tailored to the project’s needs (ex. simulations for material behavior analysis, experimental methods).* Rationale and step-by-step reasoning ensure robust research proposal ready for further development.
                    - Ex. suggests using Molecular Dynamics (MD) Simulations to explore interactions at molecular level, using software like GROMACS or AMBER to model how silk fibroin interacts with danelion pigments to understand self-assembly processes and predict resulting microstructures.
                    - Potential applications: self-healing properties from materials’ dynamic interactions → ideal for adhesives that self-repair after damage
                    - Points out pigments’ reinforcing effect, improving properties of composite material, with plans to conduct mechanical testing to quantify these properties
                    - Detailed comparison to existing materials: compare 0.5 to 1.0 GPa of traditional materials versus up to 1.5 GPa for proposed composite material, with attribution of this gain to hierarchical organization of silk proteins and pigments’ reinforcing effect; details molecular structue, behavior of components, contribution ot mechanical properties; adds potential including of other specific bioactive compounds as well to potentially further enhance properties via intermolecular interactions and cross-linking for a multi-scale synergistic effect. Thus these principles contribute to creation of advanced bio-inspired material with enhanced mechanical/optical functionalities.
                    - Model predicts unexpected properties, e.g., self-healing properties, stimuli-responsive colors, UV protection and antimicrobial properties due to dandelions’ bioactive compounds, etc.
                - **Critic agent**: in final stage, Critic throughly reviews research proposal, summarizes its key points, recommends improvements. Then delivers comprehensive scientific critique, highlighting research idea’s strengths/weaknesses and suggesting areas for refinement. Also tasked to identify most impactful scientific question that can be addressed thru molecular modeling and experimentation, and to outline steps for setting up and conducting these priorities.
                - Example: comprehensive evaluation of methodology and potential impact. It commends the silk-dandelion integration for creating energy-efficient, structurally colored biomaterials, noting indisciplinarity and innovation aspects, as well as robustness added by use of modeling and experimental methods. Identifies as well areas needing improvement, ex. challenges with nanoscale integration, scalability, environmental impacts of solvent use, lack of quantitative data, as well as concerns over long-term sustainability of material under real-world conditions. In response, suggests conducting pilot studies for process validation, exploring green chemistry for pigment extraction, developing detailed scalability plans, and performing rigorous analyses of energy consumption / material durability—thus rendering hypotheses innovative but also practical. Proposes also the most impactful scientific questions related to molecular modeling, simulation, and synthetic biology experiments in Figure S7. Also outlines key steps for setting up/conducting simulations/experiments, using MD simulations, with appropriate force fields (CHARMM, AMBER), with parameters defined using tools like CGenFF; then place molecules in solvated environ, adding ions for neutralization, using VMD or GROMACS software for setup. Then after energy minimization and equilibration under constant temp/pressure, MD simulations run for 100-500 ns with periodic boundary conditions. Post-simulation, calculate interaction energies, identify binding sites, cluster analysis of self-assemble structures, tools to be used…
                - Critic ultimately is crucial by posing questions which challenge assumptions and focus of the research, ensuring simulations and experiments target key mechanisms and outcomes.
                    - **Figure 6:** most impact questions raised by critic agent for the generated research hypothesis on integrating silk with dandelion-based pigments to create biomaterials with enhanced optical/mechanical properties
                    
                    ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/393cb45e-47f6-47ac-8c56-595b417e1e0d/image.png)
                    
                - ***Proceeds as iterative feedback loop***
            - **2.2 Autonomous agentic modeling (SECOND APPROACH with ‘fully autonomous’ multi-agent system)**
                - Use general purpose GPT-4 family via OpenAI API. Each agent has specific role and focus, described by a unique profile. (same roles as FIRST APPROACH, with additional roles Human, Planner, Assistant, Group chat manager)
                    
                    ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/5681646e-b1ac-4242-964b-c7d3109ac5ba/image.png)
                    
                - Overall pipeline for SECOND APPROACH is similar to AI-AI interactions (FIRST APPROACH), with some modifications:
                    - **User** provides task overview → Start with step-by-step plan from **Planner**, which includes creating research hypothesis from keywords either given or randomly selected by model → **Assistant** agent calls pathway function to produce foundational knowledge (sub-)graph → **Ontologist** makes/discusses definitions and their relationships → **Scientist_1** generates research idea → **Scientist_2** expands on research idea → **Critic** provides summary, review, improvement suggestions → **Assistant** executes another tool to analyze and score novelty and feasibility of proposed research idea (→ ***iterate* )**
                    
                    ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/96d99f63-92cb-4781-ba38-acb7d65333dc/image.png)
                    
                - 
                
                ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/c994fb2a-0d81-4755-8ede-17c55cecd919/image.png)
                
                - Key similarities/differences in outputs from FIRST APPROACH vs SECOND APPROACH
                    - both propose silk and dandelion pigment integration; but differ in specifics such as scope of application, technical aspects’ depth regarding fabrication and potential uses
                    - First approach: agents receive only filtered subset of info from previous interactions
                    - Second approach: allows agents to share memory, giving access to all the content generated in previous interactions — i.e. they **operate with full visibility of their collaboration history.** *Also benefit from **tool used to assess novelty of ideas against current lierature, using Semantic Scholar API, plus proactively eliminate any ideas too similar to existing work. (Novelty and feasibility are each score as integers; ex. Novelty=7, Feasibility=8)***
                - Example: conducted 5 experiments, tasking multi-agent model to construct research ideas in each experiment. Random path selection generates varying levels of novelty and feasibility, as assessed against current literature. This **emphasizes importance of comparing with existing knowledge; furthermore, were this scaled over thousands of iterations, one could yield a very large ideation database.**
                    
                    ![image.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/5f27d613-4dae-4d35-9baf-1e9828cb0b7d/5b319807-1e4a-4012-aff1-1cf670b1160b/image.png)
                    
            - -
    - SciAgents paper, references 6 +31-34 for knowledge graphs
        - [6] Buehler, M. J. Accelerating scientific discovery with generative knowledge extraction, graph-based representation,
        and multimodal intelligent graph reasoning. Machine Learning: Science and Technology (2024). URL http:
        [//iopscience.iop.org/article/10.1088/2632-2153/ad7228](https://iopscience.iop.org/article/10.1088/2632-2153/ad7228).
        [31] Shetty, P. et al. A general-purpose material property data extraction pipeline from large polymer corpora using
        natural language processing. npj Computational Materials 9, 52 (2023).
        [32] Pan, S. et al. Unifying large language models and knowledge graphs: A roadmap. IEEE Transactions on
        Knowledge and Data Engineering (2024).
        [33] Dagdelen, J. et al. Structured information extraction from scientific text with large language models. Nature
        Communications 15, 1418 (2024).
        [34] Schilling-Wilhelmi, M. et al. From text to insight: Large language models for materials science data extraction.
        arXiv preprint arXiv:2407.16867 (2024).
    - **[Constructing knowledge graphs reference in SciAgents] [6]: “Accelerating scientific discovery with generative knowledge extraction, graph-based representation,
    and multimodal intelligent graph reasoning” (Buehler, 2024)** https://iopscience.iop.org/article/10.1088/2632-2153/ad7228
        
        
    - **((BioinspiredLLM: Conversational Large Language Model for the Mechanics of Biological and Bio-Inspired Materials” ((“Accelerating scientific discover[…]” reference [11]: how papers to be used were identified ))** https://onlinelibrary.wiley.com/doi/10.1002/advs.202306724-
        - Section 4:
            
            Dataset Generation: For the scope of this work, the dataset was focused on biological material mechanics. **The corpus selected was determined by using a search on Web of Science Core Collection (https:[//www.webofscience.com/wos/woscc/](https://www.webofscience.com/wos/woscc/)).** The search phrase used was “biological materials mechanical hierarchical structure” that returned 1056 English results retrieved on 31 July 2023. Generally, the terms “biological
            materials” alone can be too broad and introduce several biomedical or
            human-based materials articles, therefore the addition of the term “hierarchical” was essential in capturing complex multiscale architectures that typically exist in Nature. **Full-text PDFs or plain text data was obtained using publisher provided application programming interfaces, manually scraped with permission, or obtained through interlibrary loans. Full-texts PDFs were then converted and cleaned using Python packages, pdftotext and re for regular expression operations to remove website link patterns, DOI patterns, extraneous symbols, or words like “Copyright”, “Ltd”.** For ≈4% of the articles obtained, the PDFs were not native. In those cases, Python packages pdf2image and pytesseract were used for optical character recognition to extract text from scanned images of the article. Since many PDF articles consist of difficult to predict headers, upon converting from PDF to text, the text was cropped to the first instance of the word “Introduction” and cropped at the end at the first of the last instance of “References”, “Acknowledgements”, “Conflicts of Interest” and potential variations. Since cropping to the start of the introductions tends to remove the title and abstract, those were then manually added back in at the start of each .txt file. Of the 1056 search results, 1034 articles were able to be obtained and used in training, rendering a 98% yield. The remaining articles that were unavailable to be obtained were mostly due to missing or
            incorrect metadata.
            
        - -