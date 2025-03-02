import asyncio
import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.tools.tool_registry import br_registry

async def test_tool_registry_search():
    """Test the search_internet tool through the Bedrock tool registry"""
    
    # Get the tool specification
    tool_spec = br_registry.get_tool_spec('search_internet')
    print("Tool specification:")
    print(json.dumps(tool_spec, indent=2, ensure_ascii=False))
    print("\n")
    
    # Execute the tool with a Chinese query
    print("Executing search_internet tool with query '机器学习'...")
    result = await br_registry.execute_tool(
        'search_internet',
        query="机器学习",
        num_results=5,
        language="zh"
    )
    
    # Print the full result
    print("Complete result from tool registry:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

async def main():
    await test_tool_registry_search()

if __name__ == "__main__":
    asyncio.run(main())
