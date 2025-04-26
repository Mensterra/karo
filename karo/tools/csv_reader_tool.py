import pandas as pd
import os
import logging
from typing import Optional, Dict, Any, List
from pydantic import Field, FilePath

# Use relative imports to access base classes from within karo structure
from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema

logger = logging.getLogger(__name__)

# --- Tool Schemas ---

class CsvReaderInput(BaseToolInputSchema):
    """Input schema for the CsvReaderTool."""
    file_path: FilePath = Field(..., description="Path to the CSV file.")
    lookup_column: str = Field(..., description="The column to search for the lookup_value.")
    lookup_value: str = Field(..., description="The value to search for in the lookup_column.")
    return_columns: Optional[List[str]] = Field(None, description="List of columns to return in the output. If None, returns all columns.")

class CsvReaderOutput(BaseToolOutputSchema):
    """Output schema for the CsvReaderTool."""
    found: bool = Field(False, description="True if the lookup_value was found in the CSV, False otherwise.")
    row_data: Optional[Dict[str, Any]] = Field(None, description="A dictionary containing the data from the row where the lookup_value was found. None if not found.")

# --- Tool Implementation ---

class CsvReaderTool(BaseTool):
    """
    Reads a CSV file, finds a row based on a lookup value in a specified column,
    and returns the data from that row.
    """
    input_schema = CsvReaderInput
    output_schema = CsvReaderOutput
    name = "csv_reader"
    description = "Reads a CSV file and finds a row based on a lookup value in a specified column."

    def __init__(self, config: Optional[Any] = None):
        """Initialize the CsvReaderTool."""
        logger.info("CsvReaderTool initialized.")
        # No specific config needed for this tool besides file_path in input
        pass

    def run(self, input_data: CsvReaderInput) -> CsvReaderOutput:
        """
        Reads the CSV, finds the row, and returns the data.
        """
        logger.info(f"Attempting to read value '{input_data.lookup_value}' from column '{input_data.lookup_column}' from '{input_data.file_path}'")
        try:
            if not os.path.exists(input_data.file_path):
                return self.output_schema(success=False, error_message=f"CSV file not found at path: {input_data.file_path}")

            # Read CSV - consider adding error handling for file format issues
            df = pd.read_csv(input_data.file_path)
            logger.debug(f"CSV columns: {df.columns.tolist()}")

            if input_data.lookup_column not in df.columns:
                return self.output_schema(success=False, error_message=f"Column '{input_data.lookup_column}' not found in CSV. Available columns: {df.columns.tolist()}")

            # Find the row
            row = df[df[input_data.lookup_column] == input_data.lookup_value]

            if row.empty:
                logger.warning(f"Value '{input_data.lookup_value}' not found in column '{input_data.lookup_column}'.")
                return self.output_schema(success=True, found=False, row_data=None)

            # Should only be one row, take the first if multiple
            row_data = row.iloc[0].to_dict()

            logger.info(f"Value '{input_data.lookup_value}' found in column '{input_data.lookup_column}'.")
            return self.output_schema(
                success=True,
                found=True,
                row_data=row_data
            )

        except pd.errors.EmptyDataError:
            logger.error(f"CSV file is empty: {input_data.file_path}")
            return self.output_schema(success=False, error_message="CSV file is empty.")
        except Exception as e:
            logger.error(f"Error processing CSV file '{input_data.file_path}': {e}", exc_info=True)
            return self.output_schema(success=False, error_message=f"Failed to read or process CSV data: {e}")

# Example Usage (for testing the tool directly)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Assume data.csv is in the same directory for direct execution
    script_dir = os.path.dirname(__file__)
    test_csv_path = os.path.join(script_dir, 'data.csv')

    # Create a dummy CSV for testing
    test_data = {'name': ['Alice', 'Bob', 'Charlie'], 'age': [25, 30, 28], 'city': ['New York', 'London', 'Paris']}
    test_df = pd.DataFrame(test_data)
    test_df.to_csv(test_csv_path, index=False)

    if not os.path.exists(test_csv_path):
        print(f"Error: Test file 'data.csv' not found in {script_dir}")
    else:
        tool = CsvReaderTool()

        print("\n--- Testing CSV Reader Tool ---")

        test_cases = [
            {"lookup_column": "name", "lookup_value": "Alice", "return_columns": ["age", "city"], "expect_success": True, "expect_found": True, "expect_age": 25, "expect_city": "New York"},
            {"lookup_column": "name", "lookup_value": "Bob", "return_columns": ["age", "city"], "expect_success": True, "expect_found": True, "expect_age": 30, "expect_city": "London"},
            {"lookup_column": "name", "lookup_value": "Charlie", "return_columns": ["age", "city"], "expect_success": True, "expect_found": True, "expect_age": 28, "expect_city": "Paris"},
            {"lookup_column": "name", "lookup_value": "David", "return_columns": ["age", "city"], "expect_success": True, "expect_found": False},
            {"lookup_column": "age", "lookup_value": "30", "return_columns": ["name"], "expect_success": True, "expect_found": True, "expect_name": "Bob"},
            {"lookup_column": "nonexistent_column", "lookup_value": "Bob", "return_columns": ["age"], "expect_success": False, "expect_error": "column 'nonexistent_column' not found"},
        ]

        for i, case in enumerate(test_cases):
            print(f"\nTest Case {i+1}: Lookup Column={case['lookup_column']}, Lookup Value={case['lookup_value']}, Return Columns={case['return_columns']}")
            input_data = CsvReaderInput(file_path=test_csv_path, lookup_column=case['lookup_column'], lookup_value=case['lookup_value'], return_columns=case['return_columns'])
            output = tool.run(input_data)
            print(f"  Output: {output}")

            assert output.success == case['expect_success']
            assert output.found == case['expect_found']

            if output.success and output.found:
                if case['return_columns'] is None or "age" in case['return_columns']:
                    assert output.row_data['age'] == case['expect_age'] if 'expect_age' in case else True
                if case['return_columns'] is None or "city" in case['return_columns']:
                    assert output.row_data['city'] == case['expect_city'] if 'expect_city' in case else True
                if case['return_columns'] is None or "name" in case['return_columns']:
                    assert output.row_data['name'] == case['expect_name'] if 'expect_name' in case else True
            elif not output.success:
                assert case['expect_error'] in output.error_message.lower()

        print("\nCSV Reader Tool tests completed.")