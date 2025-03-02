import time
import asyncio
import wikipedia
from googlesearch import search
from cachetools import TTLCache
from core.logger import logger

# Constants
CACHE_TTL = 86400  # Cache for 1 day
CACHE_MAX_SIZE = 1000  # Maximum number of cached responses
MAX_SEARCH_RESULTS = 10  # Maximum number of search results to return

# Create cache for responses
wiki_cache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
google_cache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)

def _get_wikipedia_page_and_summary(title, sentences=5):
    """Helper function to get Wikipedia page and summary
    
    Args:
        title: The title to search for
        sentences: Number of sentences for summary
        
    Returns:
        tuple: (page, summary) or (None, None) if not found
    """
    try:
        # Clean up the title to avoid common errors
        clean_title = title.strip()

        # Try with auto_suggest first
        try:
            page = wikipedia.page(clean_title, auto_suggest=True)
            summary = wikipedia.summary(clean_title, sentences=sentences, auto_suggest=True)
            return page, summary
        except wikipedia.PageError:
            # If that fails, try a direct search
            search_results = wikipedia.search(clean_title, results=1)
            if search_results:
                page = wikipedia.page(search_results[0], auto_suggest=False)
                summary = wikipedia.summary(search_results[0], sentences=sentences, auto_suggest=False)
                return page, summary
            return None, None
    except (wikipedia.PageError, wikipedia.DisambiguationError):
        return None, None
    except Exception as e:
        logger.error(f"Error getting Wikipedia page: {e}")
        return None, None

def search_wikipedia(query: str, num_results: int = 3, language: str = "en"):
    """Search Wikipedia and return relevant information
    
    Args:
        query: The search query
        num_results: Number of results to return (default: 3)
        language: Wikipedia language edition (default: "en")
        
    Returns:
        dict: Contains search results and article content
    """
    # Check cache first
    cache_key = f"{query}:{language}:{num_results}"
    if cache_key in wiki_cache:
        cached_result = wiki_cache[cache_key]
        cached_result["cached"] = True
        return cached_result
    
    try:
        # Set language
        wikipedia.set_lang(language)

        # Search for articles
        search_results = wikipedia.search(query, results=num_results)
        
        if not search_results:
            return {
                "query": query,
                "results": [],
                "content": f"No Wikipedia articles found for '{query}'."
            }
        
        # Try the first search result
        page, summary = _get_wikipedia_page_and_summary(search_results[0])
        
        # If first result fails, try the original query
        if not page and not summary:
            page, summary = _get_wikipedia_page_and_summary(query)
        
        # If we have a page and summary, return the result
        if page and summary:
            result = {
                "query": query,
                "results": search_results,
                "title": page.title,
                "url": page.url,
                "content": summary,
                "timestamp": time.time()
            }
            wiki_cache[cache_key] = result
            return result
            
        # Handle disambiguation
        try:
            # This will raise DisambiguationError if it's a disambiguation page
            wikipedia.page(search_results[0])
        except wikipedia.DisambiguationError as e:
            if e.options:
                # Try the first disambiguation option
                page, summary = _get_wikipedia_page_and_summary(e.options[0])
                if page and summary:
                    result = {
                        "query": query,
                        "results": e.options[:num_results],
                        "title": page.title,
                        "url": page.url,
                        "content": summary,
                        "disambiguation": True,
                        "timestamp": time.time()
                    }
                    wiki_cache[cache_key] = result
                    return result
                else:
                    return {
                        "query": query,
                        "results": e.options[:num_results],
                        "content": f"Found disambiguation options for '{query}', but couldn't retrieve a specific article.",
                        "disambiguation": True,
                        "timestamp": time.time()
                    }
        
        # If we get here, we found search results but couldn't get a specific article
        return {
            "query": query,
            "results": search_results,
            "content": f"Found search results for '{query}', but couldn't retrieve a specific article.",
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Wikipedia search error: {e}")
        return {
            "query": query,
            "error": f"Failed to search Wikipedia: {str(e)}"
        }

async def search_internet(query: str, num_results: int = 5, language: str = "en"):
    """Search the internet via Google and return relevant search results
    
    Args:
        query: The search query
        num_results: Number of results to return (default: 5, max: 10)
        language: Search language (default: "en")
        
    Returns:
        dict: Contains search results with titles and URLs
    """
    # Check cache first
    cache_key = f"{query}:{language}:{num_results}"
    if cache_key in google_cache:
        cached_result = google_cache[cache_key]
        cached_result["cached"] = True
        return cached_result
    
    # Limit number of results
    num_results = min(num_results, MAX_SEARCH_RESULTS)
    
    try:
        # Run the search in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        search_results = await loop.run_in_executor(
            None,
            lambda: list(search(
                query, 
                num_results=num_results, 
                lang=language,
                advanced=True
            ))
        )
        
        # Format results
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "title": result.title if hasattr(result, 'title') and result.title else result.url,
                "url": result.url,
                "description": result.description if hasattr(result, 'description') else ""
            })
        
        # Create response
        result = {
            "query": query,
            "results": formatted_results,
            "timestamp": time.time()
        }
        
        # Cache the result
        google_cache[cache_key] = result
        return result
            
    except Exception as e:
        logger.error(f"Google search error: {e}")
        return {
            "query": query,
            "error": f"Failed to search Google: {str(e)}"
        }

# Tool specification in Bedrock format
list_of_tools_specs = [
    {
        "toolSpec": {
            "name": "search_wikipedia",
            "description": "Search Wikipedia and retrieve information about a topic. Use this when asked to find factual information, explanations, or background on specific topics, people, places, events, or concepts. This tool provides access to Wikipedia's encyclopedia content.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for Wikipedia"
                        },
                        "results": {
                            "type": "integer",
                            "description": "Number of search results to return (default: 3)",
                            "default": 3
                        },
                        "language": {
                            "type": "string",
                            "description": "Wikipedia language edition (default: 'en')",
                            "default": "en"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "search_internet",
            "description": "Search the internet via Google and retrieve search results for a query. Use this when asked to find information on the web, look up current events, or research topics that may not be covered in Wikipedia. This tool provides access to Google search results with titles and URLs.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for Google"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of search results to return (default: 5, max: 10)",
                            "default": 5
                        },
                        "language": {
                            "type": "string",
                            "description": "Search language (default: 'en')",
                            "default": "en"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    }
]
