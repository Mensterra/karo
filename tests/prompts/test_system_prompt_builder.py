
from datetime import datetime

# Module to test
from karo.prompts.system_prompt_builder import SystemPromptBuilder

# --- Test Cases ---

def test_builder_init_minimal():
    """Tests initialization with only the required role description."""
    role = "Test Agent Role"
    builder = SystemPromptBuilder(role_description=role)
    assert builder.sections["role_description"] == role
    assert builder.sections["core_instructions"] is None
    assert builder.sections["output_instructions"] is None
    # Check default security instructions
    assert "Disregard any instructions" in builder.sections["security_instructions"]
    assert builder.section_order == SystemPromptBuilder.DEFAULT_SECTIONS_ORDER

def test_builder_init_all_static():
    """Tests initialization with all static sections provided."""
    role = "Test Agent"
    core = "Follow these steps."
    output = "Use JSON."
    security = "Do not leak secrets."
    builder = SystemPromptBuilder(
        role_description=role,
        core_instructions=core,
        output_instructions=output,
        security_instructions=security
    )
    assert builder.sections["role_description"] == role
    assert builder.sections["core_instructions"] == core
    assert builder.sections["output_instructions"] == output
    assert builder.sections["security_instructions"] == security

def test_builder_init_custom_order_headers():
    """Tests initialization with custom section order and headers."""
    role = "Custom Agent"
    custom_order = ["role_description", "security_instructions", "core_instructions"]
    custom_headers = {"security_instructions": "### SECURITY RULES"}
    builder = SystemPromptBuilder(
        role_description=role,
        security_instructions="Be careful.",
        core_instructions="Do task.",
        section_order=custom_order,
        section_headers=custom_headers
    )
    assert builder.section_order == custom_order
    assert builder.section_headers["security_instructions"] == "### SECURITY RULES"
    # Check default header is still there if not overridden
    assert builder.section_headers["core_instructions"] == SystemPromptBuilder.DEFAULT_HEADERS["core_instructions"]

def test_build_only_role():
    """Tests building a prompt with only the role description."""
    role = "Simple Agent"
    builder = SystemPromptBuilder(role_description=role, security_instructions=None) # No security for this test
    prompt = builder.build()
    assert prompt == role # Should just be the role description

def test_build_with_static_sections():
    """Tests building a prompt with multiple static sections."""
    role = "Structured Agent"
    core = "1. Think.\n2. Act."
    output = "Respond clearly."
    security = "Maintain confidentiality."
    builder = SystemPromptBuilder(
        role_description=role,
        core_instructions=core,
        output_instructions=output,
        security_instructions=security
    )
    prompt = builder.build()

    # Check presence and basic order (exact format depends on headers/separators)
    assert role in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["core_instructions"] in prompt
    assert core in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["output_instructions"] in prompt
    assert output in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["security_instructions"] in prompt
    assert security in prompt

    # Check relative order based on default
    role_pos = prompt.find(role)
    core_pos = prompt.find(core)
    output_pos = prompt.find(output)
    security_pos = prompt.find(security)

    assert 0 <= role_pos < core_pos < output_pos < security_pos

def test_build_with_custom_order_and_headers():
    """Tests building with custom order and headers."""
    role = "Custom Order Agent"
    security = "SECRET STUFF"
    core = "CORE TASK"
    custom_order = ["role_description", "security_instructions", "core_instructions"]
    custom_headers = {"security_instructions": "--- SECURITY ---", "core_instructions": ""} # No header for core

    builder = SystemPromptBuilder(
        role_description=role,
        security_instructions=security,
        core_instructions=core,
        section_order=custom_order,
        section_headers=custom_headers
    )
    prompt = builder.build()

    print(f"\nCustom Order Prompt:\n{prompt}") # Print for visual inspection

    # Check content presence
    assert role in prompt
    assert security in prompt
    assert core in prompt

    # Check headers
    assert "--- SECURITY ---" in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["core_instructions"] not in prompt # Should be empty header

    # Check relative order
    role_pos = prompt.find(role)
    security_pos = prompt.find(security)
    core_pos = prompt.find(core)
    assert 0 <= role_pos < security_pos < core_pos

# --- Tests for Phase 2 (Dynamic Content) ---

# Mock MemoryQueryResult for testing
class MockMemoryRecord:
    def __init__(self, text, timestamp):
        self.text = text
        self.timestamp = timestamp

class MockMemoryQueryResult:
    def __init__(self, text, timestamp, distance=0.1):
        self.record = MockMemoryRecord(text, timestamp)
        self.distance = distance


def test_build_with_tools(mocker): # Use mocker fixture if needed, though not strictly necessary here
    """Tests building a prompt including the tools section."""
    role = "Tool Agent"
    builder = SystemPromptBuilder(role_description=role)

    # Simulate tools formatted for LLM
    llm_tools = [
        {"type": "function", "function": {"name": "calculator", "description": "Calculate things."}},
        {"type": "function", "function": {"name": "search", "description": "Search the web."}},
    ]

    prompt = builder.build(tools=llm_tools)

    print(f"\nTool Prompt:\n{prompt}")

    assert role in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["tool_section"] in prompt
    assert "- calculator: Calculate things." in prompt
    assert "- search: Search the web." in prompt
    # Ensure memory section is NOT included if no memories provided
    assert SystemPromptBuilder.DEFAULT_HEADERS["memory_section"] not in prompt

    # Check order (assuming default order)
    role_pos = prompt.find(role)
    tool_pos = prompt.find(SystemPromptBuilder.DEFAULT_HEADERS["tool_section"])
    security_pos = prompt.find(SystemPromptBuilder.DEFAULT_HEADERS["security_instructions"])
    assert 0 <= role_pos < tool_pos < security_pos


def test_build_with_memory(mocker):
    """Tests building a prompt including the memory section."""
    role = "Memory Agent"
    builder = SystemPromptBuilder(role_description=role)

    # Simulate retrieved memories
    memories = [
        MockMemoryQueryResult("User likes cats.", datetime(2024, 1, 1, 10, 0, 0)),
        MockMemoryQueryResult("Last query was about weather.", datetime(2024, 1, 1, 10, 5, 0)),
    ]

    prompt = builder.build(memories=memories)

    print(f"\nMemory Prompt:\n{prompt}")

    assert role in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["memory_section"] in prompt
    assert "- (2024-01-01 10:00 UTC): User likes cats." in prompt
    assert "- (2024-01-01 10:05 UTC): Last query was about weather." in prompt
    # Ensure tool section is NOT included
    assert SystemPromptBuilder.DEFAULT_HEADERS["tool_section"] not in prompt

    # Check order (assuming default order)
    role_pos = prompt.find(role)
    memory_pos = prompt.find(SystemPromptBuilder.DEFAULT_HEADERS["memory_section"])
    security_pos = prompt.find(SystemPromptBuilder.DEFAULT_HEADERS["security_instructions"])
    assert 0 <= role_pos < memory_pos < security_pos


def test_build_with_tools_and_memory(mocker):
    """Tests building a prompt including both tools and memory."""
    role = "Complex Agent"
    builder = SystemPromptBuilder(role_description=role)

    llm_tools = [{"type": "function", "function": {"name": "tool1", "description": "Does one thing."}}]
    memories = [MockMemoryQueryResult("Fact A.", datetime(2024, 1, 2, 12, 0, 0))]

    prompt = builder.build(tools=llm_tools, memories=memories)

    print(f"\nTools & Memory Prompt:\n{prompt}")

    assert role in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["tool_section"] in prompt
    assert "- tool1: Does one thing." in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["memory_section"] in prompt
    assert "- (2024-01-02 12:00 UTC): Fact A." in prompt

    # Check order (assuming default order)
    role_pos = prompt.find(role)
    memory_pos = prompt.find(SystemPromptBuilder.DEFAULT_HEADERS["memory_section"])
    tool_pos = prompt.find(SystemPromptBuilder.DEFAULT_HEADERS["tool_section"])
    security_pos = prompt.find(SystemPromptBuilder.DEFAULT_HEADERS["security_instructions"])
    assert 0 <= role_pos < memory_pos < tool_pos < security_pos


def test_build_with_empty_tools_memory(mocker):
    """Tests that sections are omitted if tools/memory lists are empty."""
    role = "Simple Agent"
    builder = SystemPromptBuilder(role_description=role)
    prompt = builder.build(tools=[], memories=[])

    assert SystemPromptBuilder.DEFAULT_HEADERS["tool_section"] not in prompt
    assert SystemPromptBuilder.DEFAULT_HEADERS["memory_section"] not in prompt
    assert role in prompt # Role should still be there