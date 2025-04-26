import pandas as pd
from typing import Optional, List, Any, Union
from pydantic import Field, FilePath
from typing import Optional, List, Any
import logging
import os

# Import Karo base tool components using absolute path (assuming karo is installed)
from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema

logger = logging.getLogger(__name__)

# --- Tool Schemas ---

class ExcelReaderInput(BaseToolInputSchema):
    """Input schema for the ExcelReaderTool."""
    file_path: FilePath = Field(..., description="The path to the Excel file (.xlsx or .xls).")
    sheet_name: Optional[Union[str, int]] = Field(None, description="Specific sheet name or index (0-based) to read. Reads the first sheet if None.")
    max_rows: Optional[int] = Field(100, description="Maximum number of rows to read from the sheet to avoid overly long context.")
    max_cols: Optional[int] = Field(20, description="Maximum number of columns to read.")

class ExcelReaderOutput(BaseToolOutputSchema):
    """Output schema for the ExcelReaderTool."""
    file_path: str = Field(..., description="The path of the file that was read.")
    sheet_name_read: str = Field(..., description="The name of the sheet that was actually read.")
    data_preview: Optional[str] = Field(None, description="A string representation (e.g., markdown table or CSV) of the first few rows/columns of the data.")
    row_count: Optional[int] = Field(None, description="Total number of rows read (up to max_rows).")
    column_names: Optional[List[str]] = Field(None, description="List of column names read (up to max_cols).")
    # Inherits success and error_message

# --- Tool Implementation ---

class ExcelReaderTool(BaseTool):
    """
    Reads data from a specified Excel file and sheet, providing a preview.
    """
    input_schema = ExcelReaderInput
    output_schema = ExcelReaderOutput
    name = "excel_reader"
    description = "Reads data from an Excel file (.xlsx, .xls) and returns a preview including headers and the first few rows."

    def __init__(self, config: Optional[Any] = None):
        """Initialize the ExcelReaderTool."""
        logger.info("ExcelReaderTool initialized.")
        pass  # No specific config needed

    def run(self, input_data: ExcelReaderInput) -> ExcelReaderOutput:
        """
        Reads the specified Excel file and returns a data preview.

        Args:
            input_data: An instance of ExcelReaderInput.

        Returns:
            An instance of ExcelReaderOutput.
        """
        # Explicitly check for openpyxl before proceeding
        try:
            import openpyxl
        except ImportError:
            logger.error("Missing dependency: 'openpyxl' is required to read .xlsx files. Install with `poetry add openpyxl` or `pip install openpyxl`.")
            return self.output_schema(success=False, error_message="Missing dependency: 'openpyxl' required for reading Excel files.", file_path=str(input_data.file_path), sheet_name_read="N/A")

        if not isinstance(input_data, self.input_schema):
            return self.output_schema(success=False, error_message="Invalid input data format.", file_path=str(input_data.file_path), sheet_name_read="N/A")

        file_path_str = str(input_data.file_path)  # Pydantic v2 returns Path object

        # Basic check for file existence before trying pandas
        if not os.path.exists(file_path_str):
            return self.output_schema(success=False, error_message=f"File not found at path: {file_path_str}", file_path=file_path_str, sheet_name_read="N/A")

        try:
            # Determine sheet to read
            excel_file = pd.ExcelFile(file_path_str, engine='openpyxl')  # Specify engine
            sheet_names = excel_file.sheet_names
            sheet_to_read: Union[str, int] = 0  # Default to first sheet index
            sheet_name_read: str = sheet_names[0]  # Default name

            if input_data.sheet_name is not None:
                if isinstance(input_data.sheet_name, int):
                    if 0 <= input_data.sheet_name < len(sheet_names):
                        sheet_to_read = input_data.sheet_name
                        sheet_name_read = sheet_names[sheet_to_read]
                    else:
                        return self.output_schema(success=False, error_message=f"Sheet index {input_data.sheet_name} out of range.", file_path=file_path_str, sheet_name_read="N/A")
                elif isinstance(input_data.sheet_name, str):
                    if input_data.sheet_name in sheet_names:
                        sheet_to_read = input_data.sheet_name
                        sheet_name_read = input_data.sheet_name
                    else:
                        return self.output_schema(success=False, error_message=f"Sheet name '{input_data.sheet_name}' not found. Available sheets: {sheet_names}", file_path=file_path_str, sheet_name_read="N/A")

            # Read the sheet with row/col limits
            # Read only necessary rows initially to check columns
            header_df = pd.read_excel(excel_file, sheet_name=sheet_to_read, nrows=0)  # Read only header
            all_columns = header_df.columns.tolist()
            cols_to_use = all_columns[:input_data.max_cols] if input_data.max_cols else all_columns

            df = pd.read_excel(
                excel_file,
                sheet_name=sheet_to_read,
                nrows=input_data.max_rows,
                usecols=cols_to_use
            )

            # Generate preview (e.g., markdown table)
            # Limit preview rows further if needed
            preview_rows = min(len(df), 10)  # Show max 10 rows in preview
            data_preview_str = df.head(preview_rows).to_markdown(index=False)

            logger.info(f"Successfully read {len(df)} rows and {len(df.columns)} columns from sheet '{sheet_name_read}' in '{file_path_str}'.")

            return self.output_schema(
                success=True,
                file_path=file_path_str,
                sheet_name_read=sheet_name_read,
                data_preview=data_preview_str,
                row_count=len(df),
                column_names=df.columns.tolist()
            )

        except FileNotFoundError:
            # This case should be caught by os.path.exists, but included for robustness
            return self.output_schema(success=False, error_message=f"File not found at path: {file_path_str}", file_path=file_path_str, sheet_name_read="N/A")
        # Remove the redundant ImportError handler here as it's checked above
        # except ImportError:
        #      logger.error("Missing dependency: 'openpyxl' is required to read .xlsx files. Install with `poetry add openpyxl` or `pip install openpyxl`.")
        #      return self.output_schema(success=False, error_message="Missing dependency: 'openpyxl' required for reading Excel files.", file_path=file_path_str, sheet_name_read="N/A")
        except Exception as e:
            logger.error(f"Failed to read Excel file '{file_path_str}': {e}", exc_info=True)
            return self.output_schema(success=False, error_message=f"Error reading Excel file: {e}", file_path=file_path_str, sheet_name_read="N/A")

# Example Usage (for testing)
if __name__ == "__main__":
    # Create a dummy excel file for testing
    dummy_file = "sample_data_tool_test.xlsx"
    try:
        test_data = {'col A': [1, 2, 3, 4, 5], 'col B': ['apple', 'banana', 'cherry', 'date', 'elderberry'], 'col C': [True, False, True, False, True]}
        test_df = pd.DataFrame(test_data)
        test_df.to_excel(dummy_file, index=False, sheet_name="TestDataSheet")
        print(f"Created dummy file: {dummy_file}")

        reader_tool = ExcelReaderTool()

        print("\n--- Testing Excel Reader Tool ---")

        # Test case 1: Read default sheet
        input1 = ExcelReaderInput(file_path=dummy_file)
        output1 = reader_tool.run(input1)
        print("\nOutput 1 (Default Sheet):")
        print(output1.model_dump_json(indent=2))
        assert output1.success
        assert output1.sheet_name_read == "TestDataSheet"
        assert output1.row_count == 5
        assert "apple" in output1.data_preview

        # Test case 2: Read non-existent file
        input2 = ExcelReaderInput(file_path="non_existent_file.xlsx")
        output2 = reader_tool.run(input2)
        print("\nOutput 2 (Non-existent File):")
        print(output2.model_dump_json(indent=2))
        assert not output2.success
        assert "File not found" in output2.error_message

        # Test case 3: Read non-existent sheet name
        input3 = ExcelReaderInput(file_path=dummy_file, sheet_name="WrongSheet")
        output3 = reader_tool.run(input3)
        print("\nOutput 3 (Non-existent Sheet Name):")
        print(output3.model_dump_json(indent=2))
        assert not output3.success
        assert "Sheet name 'WrongSheet' not found" in output3.error_message

        # Test case 4: Read with row/col limits
        input4 = ExcelReaderInput(file_path=dummy_file, max_rows=3, max_cols=2)
        output4 = reader_tool.run(input4)
        print("\nOutput 4 (Row/Col Limits):")
        print(output4.model_dump_json(indent=2))
        assert output4.success
        assert output4.row_count == 3
        assert output4.column_names == ['col A', 'col B']
        assert "cherry" not in output4.data_preview  # Row 3 (index 2) should be last

    except Exception as e:
        print(f"Error during example execution: {e}")
    finally:
        # Clean up dummy file
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
            print(f"\nRemoved dummy file: {dummy_file}")