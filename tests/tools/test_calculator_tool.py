import pytest
import math

# Module to test
from karo.tools.calculator_tool import CalculatorTool, CalculatorInput, CalculatorOutput

# --- Fixtures ---

@pytest.fixture
def calculator_tool():
    """Provides an instance of the CalculatorTool."""
    return CalculatorTool()

# --- Test Cases ---

def test_calculator_tool_init(calculator_tool):
    """Tests successful initialization."""
    assert calculator_tool is not None
    assert calculator_tool.name == "calculator"
    assert calculator_tool.description is not None

def test_calculator_addition(calculator_tool):
    """Tests the addition operation."""
    input_data = CalculatorInput(operand1=5.5, operand2=2.3, operator='+')
    output = calculator_tool.run(input_data)
    assert output.success is True
    assert output.result == pytest.approx(7.8)
    assert output.error_message is None

def test_calculator_subtraction(calculator_tool):
    """Tests the subtraction operation."""
    input_data = CalculatorInput(operand1=10, operand2=4.5, operator='-')
    output = calculator_tool.run(input_data)
    assert output.success is True
    assert output.result == pytest.approx(5.5)
    assert output.error_message is None

def test_calculator_multiplication(calculator_tool):
    """Tests the multiplication operation."""
    input_data = CalculatorInput(operand1=6, operand2=-3, operator='*')
    output = calculator_tool.run(input_data)
    assert output.success is True
    assert output.result == pytest.approx(-18.0)
    assert output.error_message is None

def test_calculator_division(calculator_tool):
    """Tests the division operation."""
    input_data = CalculatorInput(operand1=15, operand2=4, operator='/')
    output = calculator_tool.run(input_data)
    assert output.success is True
    assert output.result == pytest.approx(3.75)
    assert output.error_message is None

def test_calculator_power(calculator_tool):
    """Tests the exponentiation operation."""
    input_data = CalculatorInput(operand1=3, operand2=4, operator='^')
    output = calculator_tool.run(input_data)
    assert output.success is True
    assert output.result == pytest.approx(81.0)
    assert output.error_message is None

def test_calculator_division_by_zero(calculator_tool):
    """Tests division by zero error."""
    input_data = CalculatorInput(operand1=10, operand2=0, operator='/')
    output = calculator_tool.run(input_data)
    assert output.success is False
    assert output.result is None
    assert "Division by zero" in output.error_message

def test_calculator_unsupported_operator(calculator_tool):
    """Tests using an unsupported operator."""
    input_data = CalculatorInput(operand1=5, operand2=2, operator='%')
    output = calculator_tool.run(input_data)
    assert output.success is False
    assert output.result is None
    assert "Unsupported operator" in output.error_message
    assert "'%'" in output.error_message

def test_calculator_invalid_input_type(calculator_tool):
    """Tests passing invalid input type to run method."""
    invalid_input = {"operand1": 1, "operand2": 2, "operator": "+"}
    output = calculator_tool.run(invalid_input) # type: ignore
    assert output.success is False
    assert output.result is None
    assert output.error_message == "Invalid input data format."

# Example of a potential math error (though less likely with basic ops)
# def test_calculator_math_error(calculator_tool):
#     # This might happen with very large numbers in power, etc.
#     # Requires mocking math.pow or similar if needed to force error
#     pass