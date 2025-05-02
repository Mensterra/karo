import pandas as pd
import os
import logging
from typing import Optional, Dict, Any
from pydantic import Field, FilePath, EmailStr

# Use relative imports to access base classes from within karo_copy structure
try:
    # Adjust relative path based on location: ../../karo/tools/base_tool.py
    from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema
except ImportError as e:
    # Fallback or clearer error if structure is wrong
    raise ImportError(f"Could not import BaseTool relative to csv_order_reader_tool.py: {e}")

logger = logging.getLogger(__name__)

# --- Tool Schemas ---

class CsvOrderReaderInput(BaseToolInputSchema):
    """Input schema for the CsvOrderReaderTool."""
    order_number: str = Field(..., description="The order number to look up.")
    customer_email: EmailStr = Field(..., description="The customer's email address for verification.")
    file_path: FilePath = Field(..., description="Path to the orders CSV file.")

class CsvOrderReaderOutput(BaseToolOutputSchema):
    """Output schema for the CsvOrderReaderTool."""
    order_number: Optional[str] = Field(None, description="The order number found.")
    customer_email: Optional[EmailStr] = Field(None, description="The customer email verified.")
    status: Optional[str] = Field(None, description="The status of the order.")
    details: Optional[Dict[str, Any]] = Field(None, description="Other details from the order row.")

# --- Tool Implementation ---

class CsvOrderReaderTool(BaseTool):
    """
    Reads an orders CSV file to find the status of a specific order,
    verifying against the customer's email.
    """
    input_schema = CsvOrderReaderInput
    output_schema = CsvOrderReaderOutput
    name = "csv_order_reader"
    description = "Looks up the status of a specific order number in a CSV file, verifying with the customer's email."

    def __init__(self, config: Optional[Any] = None):
        """Initialize the CsvOrderReaderTool."""
        logger.info("CsvOrderReaderTool initialized.")
        # No specific config needed for this tool besides file_path in input
        pass

    def run(self, input_data: CsvOrderReaderInput) -> CsvOrderReaderOutput:
        """
        Reads the CSV, finds the order, verifies email, and returns status.
        """
        logger.info(f"Attempting to read order '{input_data.order_number}' for '{input_data.customer_email}' from '{input_data.file_path}'")
        try:
            if not os.path.exists(input_data.file_path):
                 return self.output_schema(success=False, error_message=f"CSV file not found at path: {input_data.file_path}")

            # Read CSV - consider adding error handling for file format issues
            df = pd.read_csv(input_data.file_path)
            logger.debug(f"CSV columns: {df.columns.tolist()}")

            # Ensure required columns exist (case-insensitive check)
            required_cols = ['ordernumber', 'customeremail', 'status']
            df.columns = df.columns.str.lower().str.replace(' ', '') # Normalize column names
            if not all(col in df.columns for col in required_cols):
                 missing = [col for col in required_cols if col not in df.columns]
                 return self.output_schema(success=False, error_message=f"CSV missing required columns: {missing}")

            # Find the order row (case-insensitive search for order number)
            order_row = df[df['ordernumber'].str.lower() == input_data.order_number.lower()]

            if order_row.empty:
                logger.warning(f"Order '{input_data.order_number}' not found.")
                return self.output_schema(success=False, error_message=f"Order '{input_data.order_number}' not found.")

            # Should only be one row, take the first if multiple (though unlikely with unique IDs)
            order_data = order_row.iloc[0]

            # Verify customer email (case-insensitive)
            if order_data['customeremail'].lower() != input_data.customer_email.lower():
                logger.warning(f"Email mismatch for order '{input_data.order_number}'. Expected '{input_data.customer_email}', found '{order_data['customeremail']}'.")
                return self.output_schema(success=False, error_message="Order found, but customer email does not match.")

            status = order_data['status']
            # Extract other details (convert row to dict)
            details = order_data.to_dict()

            logger.info(f"Order '{input_data.order_number}' found for '{input_data.customer_email}' with status: {status}")
            return self.output_schema(
                success=True,
                order_number=input_data.order_number, # Return original case
                customer_email=input_data.customer_email, # Return original case
                status=status,
                details=details
            )

        except pd.errors.EmptyDataError:
             logger.error(f"CSV file is empty: {input_data.file_path}")
             return self.output_schema(success=False, error_message="Orders file is empty.")
        except Exception as e:
            logger.error(f"Error processing CSV file '{input_data.file_path}': {e}", exc_info=True)
            return self.output_schema(success=False, error_message=f"Failed to read or process order data: {e}")

# Example Usage (for testing the tool directly)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Assume orders.csv is in the same directory for direct execution
    script_dir = os.path.dirname(__file__)
    test_csv_path = os.path.join(script_dir, 'orders.csv')

    if not os.path.exists(test_csv_path):
        print(f"Error: Test file 'orders.csv' not found in {script_dir}")
    else:
        tool = CsvOrderReaderTool()

        print("\n--- Testing CSV Order Reader Tool ---")

        test_cases = [
            {"order": "ORD1001", "email": "alice@example.com", "file": test_csv_path, "expect_success": True, "expect_status": "Shipped"},
            {"order": "ORD1002", "email": "bob@example.com", "file": test_csv_path, "expect_success": True, "expect_status": "Processing"},
            {"order": "ORD1003", "email": "alice@example.com", "file": test_csv_path, "expect_success": True, "expect_status": "Delivered"},
            {"order": "ORD1001", "email": "wrong@example.com", "file": test_csv_path, "expect_success": False, "expect_error": "email does not match"},
            {"order": "ORD9999", "email": "alice@example.com", "file": test_csv_path, "expect_success": False, "expect_error": "not found"},
            {"order": "ORD1001", "email": "alice@example.com", "file": "nonexistent.csv", "expect_success": False, "expect_error": "not found at path"},
        ]

        for i, case in enumerate(test_cases):
            print(f"\nTest Case {i+1}: Order={case['order']}, Email={case['email']}, File={case['file']}")
            input_data = CsvOrderReaderInput(order_number=case['order'], customer_email=case['email'], file_path=case['file'])
            output = tool.run(input_data)
            print(f"  Output: {output}")

            assert output.success == case['expect_success']
            if output.success:
                assert output.status == case['expect_status']
                assert output.error_message is None
            else:
                assert case['expect_error'] in output.error_message.lower()
                assert output.status is None

        print("\nCSV Order Reader Tool tests completed.")