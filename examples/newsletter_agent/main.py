from karo.core.base_agent import BaseAgent, BaseAgentConfig
from karo.providers.openai_provider import OpenAIProvider, OpenAIProviderConfig
from karo.prompts.system_prompt_builder import SystemPromptBuilder
from typing import Dict, Any
import os

from dotenv import load_dotenv

load_dotenv()
# Import the search tool from the Karo-compatible implementation
from examples.newsletter_agent.search_tool import SearchAndContentsTool, SearchInputSchema

# First, let's try to understand why the tool isn't being called
# Let's directly use the search tool and then pass its results to the agents
class NewsletterAgents:
    def __init__(self, model_name: str = "gpt-4-turbo", api_key: str = None, exa_api_key: str = None):
        """
        Initialize the newsletter agents using the Karo Agent framework.
        
        Args:
            model_name: The OpenAI model to use
            api_key: Optional OpenAI API key
            exa_api_key: Optional Exa API key (will use env var if not provided)
        """
        self.model_name = model_name
        self.api_key = api_key
        self.exa_api_key = exa_api_key or os.getenv("EXA_API_KEY")
        
        # Create the search tool instance with the API key
        self.search_tool = SearchAndContentsTool(api_key=self.exa_api_key)
        
        # Create all agents
        self.researcher = self._create_researcher_agent()
        self.insights_expert = self._create_insights_expert_agent()
        self.writer = self._create_writer_agent()
        self.editor = self._create_editor_agent()
    
    def _create_researcher_agent(self) -> BaseAgent:
        """Create the AI Researcher agent"""
        # 1. Initialize Provider with extra parameters for tool use
        provider_config = OpenAIProviderConfig(
            model=self.model_name, 
            api_key=self.api_key,
            # Add more parameters for tools
            tool_choice="auto",
            temperature=0.1,  # Lower temperature for more deterministic responses
        )
        provider = OpenAIProvider(config=provider_config)
        
        # 2. Initialize Tools
        available_tools = [self.search_tool]
        
        # 3. Initialize Prompt Builder with more explicit instructions
        prompt_builder = SystemPromptBuilder(
            role_description="You are an AI Researcher tracking the latest advancements and trends in AI, machine learning, and deep learning.",
            core_instructions=(
                "Your PRIMARY task is to use the search_and_contents tool to find the latest information. "
                "THIS IS CRITICAL: You MUST make at least one call to the search_and_contents tool - it is your main job. "
                "Without using this tool, your response will be incomplete and outdated. "
                "After using the search tool, provide comprehensive research with reliable sources. "
                "Include exact search queries you used and summarize the most relevant findings."
            ),
            output_instructions=(
                "1. FIRST: Call the search_and_contents tool with an appropriate query.\n"
                "2. THEN: Organize your findings into clear sections with source links.\n"
                "3. ALWAYS: Highlight the potential impact of each development."
            )
        )
        
        # 4. Create Agent Config with explicit tool settings
        agent_config = BaseAgentConfig(
            provider_config=provider_config,
            prompt_builder=prompt_builder,
            tools=available_tools,
            max_tool_call_attempts=5,  # Increase max attempts
            tool_sys_msg="You have access to the search_and_contents tool. You MUST use this tool to find information."
        )
        
        # 5. Create Agent
        return BaseAgent(config=agent_config)
    
    def _create_insights_expert_agent(self) -> BaseAgent:
        """Create the AI Insights Expert agent"""
        # 1. Initialize Provider with extra parameters for tool use
        provider_config = OpenAIProviderConfig(
            model=self.model_name, 
            api_key=self.api_key,
            tool_choice="auto",
            temperature=0.1,  # Lower temperature for more deterministic responses
        )
        provider = OpenAIProvider(config=provider_config)
        
        # 2. Initialize Tools
        available_tools = [self.search_tool]
        
        # 3. Initialize Prompt Builder with more explicit instructions
        prompt_builder = SystemPromptBuilder(
            role_description="You are an AI Insights Expert with deep knowledge of the field of AI.",
            core_instructions=(
                "Your PRIMARY task is to use the search_and_contents tool to verify and expand upon the research provided. "
                "THIS IS CRITICAL: You MUST make at least one call to the search_and_contents tool - it is your main job. "
                "Without using this tool, your insights will be incomplete. "
                "After searching, provide detailed analysis on the significance, applications, and future potential of each development."
            ),
            output_instructions=(
                "1. FIRST: Call the search_and_contents tool to verify and expand upon the research.\n"
                "2. THEN: Organize your analysis into clear sections.\n"
                "3. ALWAYS: Include potential industry implications and future directions."
            )
        )
        
        # 4. Create Agent Config with explicit tool settings
        agent_config = BaseAgentConfig(
           provider_config=provider_config,
            prompt_builder=prompt_builder,
            tools=available_tools,
            max_tool_call_attempts=5,  # Increase max attempts
            tool_sys_msg="You have access to the search_and_contents tool. You MUST use this tool to find information."
        )
        
        # 5. Create Agent
        return BaseAgent(config=agent_config)
    
    def _create_writer_agent(self) -> BaseAgent:
        """Create the Newsletter Content Creator agent"""
        # 1. Initializeprovider_config
        provider_config = OpenAIProviderConfig(model=self.model_name, api_key=self.api_key)
        provider = OpenAIProvider(config=provider_config)
        
        # 2. Initialize Prompt Builder
        prompt_builder = SystemPromptBuilder(
            role_description="You are a Newsletter Content Creator with expertise in writing about AI technologies.",
            core_instructions=(
                "Transform insights from the AI Insights Expert into engaging and reader-friendly newsletter content about recent developments in AI, machine learning, and deep learning. "
                "Make complex topics accessible and engaging for a diverse audience. "
                "Transform the insights into reader-friendly content, highlighting the innovation, relevance, and potential impact of each development."
            ),
            output_instructions="Write in a professional yet engaging tone. Structure the content with clear headings and concise paragraphs. Keep the content aligned with the newsletter's goals."
        )
        
        # 3. Create Agent Config
        agent_config = BaseAgentConfig(
            provider_config=provider_config,
            prompt_builder=prompt_builder
        )
        
        # 4. Create Agent
        return BaseAgent(config=agent_config)
    
    def _create_editor_agent(self) -> BaseAgent:
        """Create the Newsletter Editor agent"""
        # 1. Initialize Provider
        provider_config = OpenAIProviderConfig(model=self.model_name, api_key=self.api_key)
        provider = OpenAIProvider(config=provider_config)
        
        # 2. Initialize Prompt Builder
        prompt_builder = SystemPromptBuilder(
            role_description="You are a meticulous Newsletter Editor for AI content.",
            core_instructions=(
                "Proofread, refine, and structure the newsletter to ensure it is ready for publication. "
                "Maintain professional tone while ensuring content is accessible to the target audience. "
                "Ensure clarity, eliminate errors, enhance readability, and align the tone with the newsletter's vision. "
                "Focus on improving flow, highlighting key insights effectively, and ensuring the newsletter engages the audience."
            ),
            output_instructions="Include valid website URLs to reliable sources for the advancements discussed. Format the newsletter with proper headings, bullet points, and paragraph spacing. Ensure all technical terms are adequately explained for the target audience."
        )
        
        # 3. Create Agent Config
        agent_config = BaseAgentConfig(
            provider_config=provider_config,
            prompt_builder=prompt_builder
        )
        
        # 4. Create Agent
        return BaseAgent(config=agent_config)
    
    def manual_search(self, query: str, days_ago: int = 30) -> dict:
        """
        Directly execute a search using the search tool.
        
        Args:
            query: The search query
            days_ago: How many days back to search
            
        Returns:
            The search results
        """
        print(f"📊 Performing manual search for: '{query}'...")
        search_input = SearchInputSchema(
            search_query=query,
            days_ago=days_ago,
            max_results=5
        )
        
        try:
            results = self.search_tool.run(search_input)
            if results.get("success"):
                print(f"✅ Search successful: {results.get('total_results_found', 0)} results found")
                return results
            else:
                print(f"❌ Search failed: {results.get('error_message', 'Unknown error')}")
                return {"success": False, "error_message": results.get("error_message", "Unknown error")}
        except Exception as e:
            print(f"❌ Search error: {str(e)}")
            return {"success": False, "error_message": str(e)}
    
    # Modify the run_pipeline method to fix the response handling

    def run_pipeline(self, user_input: str) -> Dict[str, Any]:
        """
        Run the complete newsletter generation pipeline with manual search.
        
        Args:
            user_input: User's topic or focus for the newsletter
            
        Returns:
            Dictionary containing the outputs from each stage of the pipeline
        """
        from karo.schemas.base_schemas import BaseInputSchema
        
        # First, manually run searches to ensure we have data
        primary_search_results = self.manual_search(f"latest developments in {user_input}", days_ago=30)
        secondary_search_results = self.manual_search(f"impact of {user_input}", days_ago=60)
        
        # Convert search results to a readable format
        search_summary = "SEARCH RESULTS:\n\n"
        if primary_search_results.get("success"):
            search_summary += f"Search for '{primary_search_results.get('search_query')}' found {len(primary_search_results.get('results', []))} results:\n\n"
            for i, result in enumerate(primary_search_results.get("results", [])):
                search_summary += f"[Result {i+1}]\n"
                search_summary += f"Title: {result.get('title')}\n"
                search_summary += f"URL: {result.get('url')}\n"
                search_summary += f"Published: {result.get('published_date')}\n"
                if result.get('content_preview'):
                    search_summary += f"Preview: {result.get('content_preview')[:300]}...\n\n"
        
        if secondary_search_results.get("success"):
            search_summary += f"\nSearch for '{secondary_search_results.get('search_query')}' found {len(secondary_search_results.get('results', []))} results:\n\n"
            for i, result in enumerate(secondary_search_results.get("results", [])):
                search_summary += f"[Result {i+1}]\n"
                search_summary += f"Title: {result.get('title')}\n"
                search_summary += f"URL: {result.get('url')}\n"
                search_summary += f"Published: {result.get('published_date')}\n"
                if result.get('content_preview'):
                    search_summary += f"Preview: {result.get('content_preview')[:300]}...\n\n"
        
        # Stage 1: Research with explicit tool usage instructions and prepared search results
        print("\n🔍 Stage 1: Conducting research...")
        research_input = BaseInputSchema(
            chat_message=(
                f"Research task: Analyze these search results about {user_input}.\n\n"
                f"{search_summary}\n\n"
                f"Organize these findings into clear research with reliable sources. "
                f"Include the significance of each development and its broader industry impact. "
                f"If you need more specific information, use the search_and_contents tool with a specific query."
            )
        )
        
        # Create external history to ensure proper message passing
        research_history = [
            {"role": "user", "content": research_input.chat_message}
        ]
        
        # Use empty input but pass history explicitly
        empty_input = BaseInputSchema(chat_message="")
        research_result = self.researcher.run(empty_input, history=research_history)
        
        # Access the response correctly - first check if it has a response_message attribute
        if hasattr(research_result, 'response_message'):
            research_content = research_result.response_message
        # Next check if it's a BaseOutputSchema with content or response_content
        elif hasattr(research_result, 'content'):
            research_content = research_result.content
        elif hasattr(research_result, 'response_content'):
            research_content = research_result.response_content
        # If all else fails, try to convert it to a string
        else:
            research_content = str(research_result)
            
        print("✅ Research completed")
        
        # Show the tool calls that were made during research
        if hasattr(research_result, 'tool_calls') and research_result.tool_calls:
            print(f"  - Made {len(research_result.tool_calls)} tool calls during research")
        else:
            print("  - Note: No additional tool calls were made during research (using pre-fetched data)")
        
        # Stage 2: Insights using the research content and search results
        print("\n🧠 Stage 2: Generating insights...")
        insights_message = (
            f"Add insights to the following research about {user_input}.\n\n"
            f"Research to analyze:\n{research_content}\n\n"
            f"Also consider these additional search results:\n{search_summary[:1000]}...\n\n"
            f"If you need any specific information, use the search_and_contents tool with a specific query."
        )
        
        # Create insights history
        insights_history = [
            {"role": "user", "content": insights_message}
        ]
        
        insights_result = self.insights_expert.run(empty_input, history=insights_history)
        
        # Access the insights result the same way
        if hasattr(insights_result, 'response_message'):
            insights_content = insights_result.response_message
        elif hasattr(insights_result, 'content'):
            insights_content = insights_result.content
        elif hasattr(insights_result, 'response_content'):
            insights_content = insights_result.response_content
        else:
            insights_content = str(insights_result)
            
        print("✅ Insights generated")
        
        # Show the tool calls that were made during insights
        if hasattr(insights_result, 'tool_calls') and insights_result.tool_calls:
            print(f"  - Made {len(insights_result.tool_calls)} tool calls during insights generation")
        else:
            print("  - Note: No additional tool calls were made during insights (using pre-fetched data)")
        
        # Stage 3: Writing
        print("\n✍️ Stage 3: Creating newsletter draft...")
        writing_message = f"Transform these insights about {user_input} into engaging newsletter content:\n\n{insights_content}"
        
        # Create writing history
        writing_history = [
            {"role": "user", "content": writing_message}
        ]
        
        writing_result = self.writer.run(empty_input, history=writing_history)
        
        # Access writing result
        if hasattr(writing_result, 'response_message'):
            newsletter_draft = writing_result.response_message
        elif hasattr(writing_result, 'content'):
            newsletter_draft = writing_result.content
        elif hasattr(writing_result, 'response_content'):
            newsletter_draft = writing_result.response_content
        else:
            newsletter_draft = str(writing_result)
            
        print("✅ Draft created")
        
        # Stage 4: Editing
        print("\n📝 Stage 4: Editing and finalizing...")
        editing_message = (
            f"Proofread and refine this newsletter draft about {user_input}. "
            f"Ensure all sources are properly cited and the content is engaging and informative:\n\n{newsletter_draft}"
        )
        
        # Create editing history
        editing_history = [
            {"role": "user", "content": editing_message}
        ]
        
        editing_result = self.editor.run(empty_input, history=editing_history)
        
        # Access editing result
        if hasattr(editing_result, 'response_message'):
            final_newsletter = editing_result.response_message
        elif hasattr(editing_result, 'content'):
            final_newsletter = editing_result.content
        elif hasattr(editing_result, 'response_content'):
            final_newsletter = editing_result.response_content
        else:
            final_newsletter = str(editing_result)
            
        print("✅ Newsletter finalized")
        
        # Add debug logging to diagnose issues
        print(f"DEBUG - Final newsletter type: {type(editing_result)}")
        print(f"DEBUG - Final newsletter attributes: {dir(editing_result)}")
        
        # Return all stages and final result
        return {
            "research": research_content,
            "insights": insights_content,
            "draft": newsletter_draft,
            "final": final_newsletter
        }

# Example usage
if __name__ == "__main__":
    import sys
    
    # Get Exa API key from environment
    exa_api_key = os.getenv("EXA_API_KEY")
    if not exa_api_key:
        print("⚠️ Warning: EXA_API_KEY environment variable not set.")
        print("Web search functionality will not work without an Exa API key.")
        print("Get an API key from https://exa.ai and set it as an environment variable.")
        
        proceed = input("Do you want to proceed without web search? (y/n): ").lower()
        if proceed != 'y':
            print("Exiting. Please set the EXA_API_KEY environment variable and try again.")
            sys.exit(1)
    
    # Create the agents
    print("Initializing newsletter generation agents...")
    agents = NewsletterAgents(model_name="gpt-4-turbo", exa_api_key=exa_api_key)
    
    # Get user input or use default
    if len(sys.argv) > 1:
        # Join all arguments as a single input string
        user_query = " ".join(sys.argv[1:])
    else:
        # Prompt for input if no command line arguments
        user_query = input("Enter a topic for your AI newsletter: ")
    
    print(f"\n===== GENERATING NEWSLETTER ON: {user_query} =====\n")
    print("This may take a few minutes...\n")
    
    # Run the pipeline with user input
    try:
        result = agents.run_pipeline(user_query)
        
        # Print the final newsletter
        print("\n===== FINAL NEWSLETTER =====\n")
        print(result["final"])
        
        # Option to see intermediate results
        show_details = input("\nWould you like to see the intermediate steps? (y/n): ").lower()
        if show_details == 'y':
            print("\n===== RESEARCH CONTENT =====\n")
            print(result["research"])
            
            print("\n===== INSIGHTS CONTENT =====\n")
            print(result["insights"])
            
            print("\n===== DRAFT NEWSLETTER =====\n")
            print(result["draft"])
    except Exception as e:
        print(f"\n❌ Error during newsletter generation: {str(e)}")
        import traceback
        traceback.print_exc()
        print("Please check your API keys and internet connection and try again.")




# An application that helps non developers and small businesses train their data to create an AI model for their buisnesses and use case.