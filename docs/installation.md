# Installation

This guide explains how to install the Karo framework for use in your projects.

## Prerequisites

*   Python 3.10 or higher
*   pip (Python package installer)

## Standard Installation

The recommended way to install Karo is using pip:

```bash
pip install karo
```
*(Note: Replace `karo` with the actual package name if it's different upon publishing).*

This command will download and install the latest stable version of Karo and its core dependencies.

## Installing Optional Dependencies

Some components, like specific database integrations or tools, might require extra dependencies. These can often be installed as extras.

*   **For Excel Reading:** If you plan to use tools that read `.xlsx` files (like the `ExcelReaderTool` example), you'll need `openpyxl`:
    ```bash
    pip install openpyxl
    ```
    *(Or potentially `pip install karo[excel]` if extras are configured in `pyproject.toml` later)*

*   **For Pandas:** If using tools requiring pandas:
    ```bash
    pip install pandas
    ```
    *(Or potentially `pip install karo[pandas]`)*

*   **For Rich Output:** If running examples that use `rich` for formatted terminal output:
    ```bash
    pip install rich
    ```

## Environment Variables

Karo requires API keys for certain services, primarily LLM providers and embedding models. The recommended way to manage these is through environment variables.

Create a `.env` file in the root directory of *your project* (where you are importing and using Karo) and add the necessary keys:

```dotenv
# Example for OpenAI
OPENAI_API_KEY='your-openai-api-key-here'

# Add other keys as needed for different providers or services
# SOME_OTHER_API_KEY='your-other-key'
```

Karo components (like `OpenAIProvider` or `ChromaDBService` using OpenAI embeddings) will automatically look for these environment variables if the keys are not provided directly during configuration. You can use libraries like `python-dotenv` in your own application code to load this file:

```python
# In your application script
from dotenv import load_dotenv
load_dotenv()

# Now Karo components can access the environment variables
# ... initialize Karo providers/services ...
```

## Development Installation

If you want to contribute to Karo or install it directly from the source code:

1.  Clone the repository:
    ```bash
    git clone <karo-repo-url>
    cd karo
    ```
2.  It's highly recommended to use [Poetry](https://python-poetry.org/) for managing dependencies during development. Install Poetry if you haven't already.
3.  Install dependencies, including development tools:
    ```bash
    poetry install
    ```
This sets up an editable installation, meaning changes you make to the Karo source code will be reflected immediately when you run your code or the examples.