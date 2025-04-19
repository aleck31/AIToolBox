import asyncio
import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.tools.search_tools import search_wikipedia

def test_search_wikipedia(query, language="en"):
    """Test Wikipedia search with specified language"""
    result = search_wikipedia(query, language=language)
    print(f"Result for query '{query}' (language: {language}):")
    print(f"Title: {result.get('title', 'N/A')}")
    print(f"URL: {result.get('url', 'N/A')}")
    print(f"Results: {result.get('results', [])}")
    print(f"Content: {result.get('content', 'No content')[:200]}...")
    print("\n")
    return result

def test_caching():
    """Test that caching works correctly"""
    query = "Python programming language"
    
    # First call should not be cached
    start_time = time.time()
    result1 = search_wikipedia(query)
    first_call_time = time.time() - start_time
    print(f"First call took {first_call_time:.4f} seconds")
    print(f"Cached: {result1.get('cached', False)}")
    
    # Second call should be cached and faster
    start_time = time.time()
    result2 = search_wikipedia(query)
    second_call_time = time.time() - start_time
    print(f"Second call took {second_call_time:.4f} seconds")
    print(f"Cached: {result2.get('cached', False)}")
    print(f"Speed improvement: {first_call_time / second_call_time:.2f}x faster")
    print("\n")

def test_multilingual():
    """Test Wikipedia search in multiple languages"""
    print("=== TESTING MULTILINGUAL SEARCH ===")
    
    # Test English
    test_search_wikipedia("Machine Learning", "en")
    
    # Test Chinese
    test_search_wikipedia("机器学习", "zh")
    
    # Test Spanish
    test_search_wikipedia("Aprendizaje automático", "es")
    
    # Test French
    test_search_wikipedia("Apprentissage automatique", "fr")
    
    # Test German
    test_search_wikipedia("Maschinelles Lernen", "de")
    
    print("=== MULTILINGUAL TESTING COMPLETE ===\n")

if __name__ == "__main__":
    # Test with a few different queries in English
    print("=== TESTING ENGLISH QUERIES ===")
    english_queries = [
        "Python programming language",
        "Artificial Intelligence",
        "Machine Learning",
        "Natural Language Processing"
    ]
    
    for query in english_queries:
        test_search_wikipedia(query)
    
    # Test multilingual search
    test_multilingual()
    
    # Test caching
    test_caching()
