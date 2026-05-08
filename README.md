# IndoorGraph
========================================================
IndoorLLM
LLM + Graph-Based Indoor Navigation System
========================================================

IndoorLLM is a graph-based indoor navigation pipeline designed
for complex indoor environments such as:

- Airports
- Shopping malls
- Commercial centers
- Large indoor infrastructures

The system uses structured graphs implemented with NetworkX
and integrates a Small Language Model (SLM) through Ollama
to provide natural language interaction.

--------------------------------------------------------
PROJECT STRUCTURE
--------------------------------------------------------

The project is composed of two main modules:

1. IndoorLLM.py
2. LLM_agent.py

Additional tools and datasets are available inside the Data folder.

========================================================
1. IndoorLLM.py
========================================================

IndoorLLM.py is the core Graph Engine of the project.

It contains:
- Graph loading
- Graph manipulation
- In-memory graph management
- Routing algorithms
- Path computation
- User profile handling
- Indoor navigation logic

The script works directly on a structured NetworkX graph.

--------------------------------------------------------
HOW TO RUN
--------------------------------------------------------

Launch the engine using:

python IndoorLLM.py START DESTINATION PROFILE

Example:

python IndoorLLM.py W A5 all

--------------------------------------------------------
PARAMETERS
--------------------------------------------------------

START
    Starting node of the route.

DESTINATION
    Target node of the route.

PROFILE
    Navigation preferences.

Profiles can specify:
- corridors
- stairs
- other routing preferences

Using:

all

enables every available path type.

--------------------------------------------------------
IMPORTANT NOTE
--------------------------------------------------------

The graph currently used must be manually selected
inside the source code.

At the moment, the project is configured for:

Orio Center

Example test:

python IndoorLLM.py W A5 all

========================================================
2. LLM_agent.py
========================================================

LLM_agent.py is the Natural Language Interface of the project.

It uses:
- Ollama
- Small Language Models (SLM)

The agent interprets user requests in natural language
and uses IndoorLLM.py as the routing engine.

--------------------------------------------------------
HOW TO RUN
--------------------------------------------------------

Start the conversational agent with:

python LLM_agent.py

After launch, start chatting directly in terminal.

--------------------------------------------------------
EXAMPLE REQUEST
--------------------------------------------------------

Using the Orio Center example graph:

Give me directions from W to A5

or

How do I get from W to A5?

========================================================
INSTALLATION
========================================================

--------------------------------------------------------
1. CREATE PYTHON ENVIRONMENT
--------------------------------------------------------

Windows:

python -m venv venv
venv\Scripts\activate

Linux / macOS:

python3 -m venv venv
source venv/bin/activate

--------------------------------------------------------
2. INSTALL REQUIREMENTS
--------------------------------------------------------

pip install -r requirements.txt

--------------------------------------------------------
3. INSTALL OLLAMA
--------------------------------------------------------

Download and install Ollama from:

https://ollama.com/

Then pull the desired model:

ollama pull llama3

========================================================
SVG GRAPH EXTRACTOR
========================================================

The project includes a graph extraction pipeline from SVG files.

Script:

ExtractGraph_fromsvg.py

--------------------------------------------------------
WORKFLOW
--------------------------------------------------------

1. Create or export the indoor map as SVG
   (Affinity Designer was used during testing).

2. Link the correct SVG file path inside:

   ExtractGraph_fromsvg.py

3. Run the extractor script.

4. The graph output will be generated automatically.

========================================================
DATA FOLDER
========================================================

The Data folder contains project resources and outputs.

--------------------------------------------------------
Data/grafica
--------------------------------------------------------

Contains:
- Computed route plots
- Example SVG projects
- Affinity vector projects
- Visual assets

--------------------------------------------------------
Data/Result and validation
--------------------------------------------------------

Contains:
- System output files generated during tests
- Validation prompts
- Validation datasets
- Full validation results

========================================================
TECHNOLOGIES USED
========================================================

- Python
- NetworkX
- Ollama
- Small Language Models (SLM)
- SVG-based graph extraction

========================================================
PROJECT GOAL
========================================================

The goal of IndoorLLM is to combine:

- Structured graph navigation
- Indoor routing
- Natural language interaction
- Lightweight local LLM systems

to build intelligent indoor navigation systems
for real-world environments.

========================================================