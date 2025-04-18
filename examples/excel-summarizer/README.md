# Karo Example: Excel Summarizer

This example demonstrates using the Karo framework to create an agent that can summarize data from an uploaded Excel file.

It utilizes:
- A custom tool (`ExcelReaderTool`) to read and extract data using pandas.
- An agent (`SummarizationAgent`) to process the extracted data and generate a summary using an LLM.

## Setup

1.  Ensure Karo framework is installed (`poetry install`).
2.  Install pandas and openpyxl:
    ```bash
    poetry add pandas openpyxl
    ```
3.  Set your `OPENAI_API_KEY` in the root `.env` file.
4.  Place an example Excel file (e.g., `sample_data.xlsx`) in this directory.

## Running

```bash
poetry run python examples/excel-summarizer/main.py --file sample_data.xlsx
```

**(More details to be added)**