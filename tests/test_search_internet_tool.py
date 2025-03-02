import asyncio
import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.tools.search_tools import search_internet

async def test_search_internet(query, num_results=5, language="en"):
    """Test internet search with specified parameters"""
    result = await search_internet(query, num_results=num_results, language=language)
    print(f"Result for query '{query}' (language: {language}, num_results: {num_results}):")
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return result
        
    print(f"Found {len(result.get('results', []))} results")
    
    for i, item in enumerate(result.get('results', [])):
        print(f"Result {i+1}:")
        print(f"  Title: {item.get('title', 'N/A')}")
        print(f"  URL: {item.get('url', 'N/A')}")
        print(f"  Description: {item.get('description', 'N/A')[:100]}...")
    
    print("\n")
    return result

async def test_caching():
    """Test that caching works correctly"""
    query = "Python programming language"
    
    # First call should not be cached
    start_time = time.time()
    result1 = await search_internet(query)
    first_call_time = time.time() - start_time
    print(f"First call took {first_call_time:.4f} seconds")
    print(f"Cached: {result1.get('cached', False)}")
    
    # Second call should be cached and faster
    start_time = time.time()
    result2 = await search_internet(query)
    second_call_time = time.time() - start_time
    print(f"Second call took {second_call_time:.4f} seconds")
    print(f"Cached: {result2.get('cached', False)}")
    print(f"Speed improvement: {first_call_time / second_call_time:.2f}x faster")
    print("\n")

async def test_multilingual():
    """Test internet search in multiple languages"""
    print("=== TESTING MULTILINGUAL SEARCH ===")
    
    # Test English
    await test_search_internet("Machine Learning", language="en")
    
    # Test Chinese
    await test_search_internet("机器学习", language="zh")
    
    # Test Spanish
    await test_search_internet("Aprendizaje automático", language="es")
    
    print("=== MULTILINGUAL TESTING COMPLETE ===\n")

async def main():
    # Test with a few different queries in English
    print("=== TESTING ENGLISH QUERIES ===")
    english_queries = [
        "Python programming language",
        "Artificial Intelligence",
        "Latest technology news"
    ]
    
    for query in english_queries:
        await test_search_internet(query)
    
    # Test with different number of results
    print("=== TESTING DIFFERENT RESULT COUNTS ===")
    await test_search_internet("Climate change", num_results=3)
    await test_search_internet("Renewable energy", num_results=7)
    
    # Test multilingual search
    await test_multilingual()
    
    # Test caching
    await test_caching()

if __name__ == "__main__":
    asyncio.run(main())
