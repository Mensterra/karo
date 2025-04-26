from karo.tools.base_tool import BaseTool
from pydantic import BaseModel, Field
from exa_py import Exa
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os

from dotenv import load_dotenv

load_dotenv()

class SearchResult(BaseModel):
    """Schema for a single search result"""
    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    published_date: Optional[str] = Field(None, description="Date the content was published")
    content_preview: Optional[str] = Field(None, description="Preview of the content")


class SearchInputSchema(BaseModel):
    """Schema for search tool inputs"""
    search_query: str = Field(..., description="The search query to use")
    days_ago: int = Field(default=7, description="How many days back to search for content")
    max_results: int = Field(default=5, description="Maximum number of results to return")
    max_preview_chars: int = Field(default=500, description="Maximum characters for content previews")


class SearchOutputSchema(BaseModel):
    """Schema for search tool outputs"""
    success: bool = Field(default=True, description="Whether the search was successful")
    error_message: Optional[str] = Field(None, description="Error message if search failed")
    results: Optional[List[SearchResult]] = Field(None, description="List of search results")
    search_query: Optional[str] = Field(None, description="The query that was searched")
    total_results_found: Optional[int] = Field(None, description="Total number of results found")


class SearchAndContentsTool(BaseTool):
    """Tool for searching the web and retrieving content using Exa API"""
    name: str = "search_and_contents"
    description: str = (
        "Searches the web based on a search query for recent results. "
        "Returns both the search results and the contents of those pages. "
        "Particularly useful for finding recent developments and news."
    )
    input_schema = SearchInputSchema
    output_schema = SearchOutputSchema
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the search tool with an optional API key
        
        Args:
            api_key: Exa API key, falls back to EXA_API_KEY environment variable if not provided
        """
        super().__init__()
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        
    def run(self, input_data: SearchInputSchema) -> Dict[str, Any]:
        """
        Execute the search and return results with content
        
        Args:
            input_data: The search parameters
            
        Returns:
            Dictionary of results that will be converted to the output schema
        """
        try:
            # Verify API key exists
            if not self.api_key:
                return {
                    "success": False,
                    "error_message": "No Exa API key available. Please provide an API key or set the EXA_API_KEY environment variable.",
                    "results": None
                }
            
            # Initialize Exa client
            exa = Exa(api_key=self.api_key)

            # Calculate date cutoff
            days_ago = input_data.days_ago
            date_cutoff = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

            # Log the search being performed
            print(f"🔍 Searching for: '{input_data.search_query}' (last {days_ago} days)")
            
            # Perform search
            search_results = exa.search_and_contents(
                query=input_data.search_query,
                use_autoprompt=True,
                start_published_date=date_cutoff,
                num_results=input_data.max_results,
                text={"include_html_tags": False, "max_characters": 5000},
            )
            
            # Format results
            formatted_results = []
            for result in search_results.results:
                content_preview = None
                if hasattr(result, 'text') and result.text:
                    max_chars = input_data.max_preview_chars
                    content_preview = result.text[:max_chars] + "..." if len(result.text) > max_chars else result.text
                
                formatted_result = {
                    "title": result.title,
                    "url": result.url,
                    "published_date": getattr(result, 'published_date', None),
                    "content_preview": content_preview
                }
                formatted_results.append(formatted_result)
            
            print(f"✅ Search completed with {len(formatted_results)} results")
            
            # Return successful output
            return {
                "success": True,
                "error_message": None,
                "results": formatted_results,
                "search_query": input_data.search_query,
                "total_results_found": len(formatted_results)
            }
            
        except Exception as e:
            error_msg = f"Error performing search: {str(e)}"
            print(f"❌ Search error: {error_msg}")
            
            # Return error output
            return {
                "success": False,
                "error_message": error_msg,
                "results": None
            }


# For testing outside of the main application
if __name__ == "__main__":
    # Create the search tool
    search_tool = SearchAndContentsTool()
    
    # Create a test input
    test_input = SearchInputSchema(
        search_query="latest developments in AI healthcare",
        days_ago=7,
        max_results=3
    )
    
    # Run the search
    result = search_tool.run(test_input)
    
    # Print results
    if result.get("success"):
        print(f"Search for '{result['search_query']}' found {result['total_results_found']} results:")
        for i, res in enumerate(result['results']):
            print(f"\n--- Result {i+1} ---")
            print(f"Title: {res['title']}")
            print(f"URL: {res['url']}")
            print(f"Published: {res['published_date']}")
            preview = res['content_preview']
            if preview:
                print(f"Preview: {preview[:100]}...")
    else:
        print(f"Search failed: {result['error_message']}")