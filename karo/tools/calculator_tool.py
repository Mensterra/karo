import logging
from pydantic import Field
import math
import operator
from typing import Optional, Any

from karo.tools.base_tool import BaseTool, BaseToolInputSchema, BaseToolOutputSchema

logger = logging.getLogger(__name__)

# --- Tool Schemas ---

class CalculatorInput(BaseToolInputSchema):
    """Input schema for the CalculatorTool."""
    operand1: float = Field(..., description="The first number for the operation.")
    operand2: float = Field(..., description="The second number for the operation.")
    operator: str = Field(..., description="The operation to perform. Supported: +, -, *, /, ^ (power).")

class CalculatorOutput(BaseToolOutputSchema):
    """Output schema for the CalculatorTool."""
    result: Optional[float] = Field(None, description="The result of the calculation.")
    # Inherits success and error_message from BaseToolOutputSchema

# --- Tool Implementation ---

class CalculatorTool(BaseTool):
    """
    A simple tool to perform basic arithmetic operations.
    Supports addition (+), subtraction (-), multiplication (*), division (/), and exponentiation (^).
    """
    # --- Class attributes ---
    input_schema = CalculatorInput
    output_schema = CalculatorOutput
    name = "calculator"
    description = "Performs basic arithmetic operations (+, -, *, /, ^) on two numbers."

    # --- Operator mapping ---
    OPERATORS = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '^': operator.pow,
    }

    def __init__(self, config: Optional[Any] = None):
        """Initialize the CalculatorTool. No specific config needed for this simple tool."""
        logger.info("CalculatorTool initialized.")
        # No config needed for this tool, but constructor must exist
        pass

    def run(self, input_data: CalculatorInput) -> CalculatorOutput:
        """
        Executes the calculation based on the provided operands and operator.

        Args:
            input_data: An instance of CalculatorInput.

        Returns:
            An instance of CalculatorOutput containing the result or an error message.
        """
        if not isinstance(input_data, self.input_schema):
            return self.output_schema(success=False, error_message="Invalid input data format.")

        op_func = self.OPERATORS.get(input_data.operator)

        if op_func is None:
            return self.output_schema(
                success=False,
                error_message=f"Unsupported operator: '{input_data.operator}'. Supported operators are: {list(self.OPERATORS.keys())}"
            )

        try:
            # Perform calculation
            if input_data.operator == '/' and input_data.operand2 == 0:
                return self.output_schema(success=False, error_message="Division by zero is not allowed.")

            result = op_func(input_data.operand1, input_data.operand2)

            # Handle potential math errors (though division by zero is caught above)
            if not isinstance(result, (int, float)) or math.isnan(result) or math.isinf(result):
                 return self.output_schema(success=False, error_message=f"Calculation resulted in an invalid number: {result}")

            logger.info(f"CalculatorTool executed: {input_data.operand1} {input_data.operator} {input_data.operand2} = {result}")
            return self.output_schema(success=True, result=result)

        except Exception as e:
            logger.error(f"CalculatorTool failed during execution: {e}", exc_info=True)
            return self.output_schema(success=False, error_message=f"Calculation error: {e}")

# Example Usage (for testing)
if __name__ == "__main__":
    calc_tool = CalculatorTool()

    print("\n--- Testing Calculator Tool ---")

    # Test cases
    cases = [
        {"op1": 5, "op2": 3, "op": "+", "expected_success": True, "expected_result": 8.0},
        {"op1": 10, "op2": 4, "op": "-", "expected_success": True, "expected_result": 6.0},
        {"op1": 6, "op2": 7, "op": "*", "expected_success": True, "expected_result": 42.0},
        {"op1": 12, "op2": 3, "op": "/", "expected_success": True, "expected_result": 4.0},
        {"op1": 2, "op2": 5, "op": "^", "expected_success": True, "expected_result": 32.0},
        {"op1": 10, "op2": 0, "op": "/", "expected_success": False, "expected_error": "Division by zero"},
        {"op1": 5, "op2": 3, "op": "%", "expected_success": False, "expected_error": "Unsupported operator"},
    ]

    for i, case in enumerate(cases):
        print(f"\nTest Case {i+1}: {case['op1']} {case['op']} {case['op2']}")
        input_data = CalculatorInput(operand1=case['op1'], operand2=case['op2'], operator=case['op'])
        output = calc_tool.run(input_data)
        print(f"  Output: {output}")

        assert output.success == case['expected_success']
        if output.success:
            assert output.result == case['expected_result']
            assert output.error_message is None
        else:
            assert output.result is None
            assert case['expected_error'] in output.error_message

    print("\nCalculator Tool tests completed.")