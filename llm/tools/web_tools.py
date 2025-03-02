import random
import time
import asyncio
import aiohttp
from cachetools import TTLCache
from urllib.parse import urlparse
from core.logger import logger

# Constants
CACHE_TTL = 86400  # Cache for 1 day
CACHE_MAX_SIZE = 1000  # Maximum number of cached responses
MAX_CONTENT_LENGTH = 2048 * 1024  # 2MB
TIMEOUT_SECONDS = 15

# Create caches for responses
url_cache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)

UserAgents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:45.0) Gecko/20100101 Firefox/45.0.."
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; rv:16.0) Gecko/20100101 Firefox/16.0",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
    "curl/8.5.0"
]

def validate_url(url: str) -> tuple[bool, str]:
    """Validate URL format and scheme"""
    if not url:
        return False, "URL is required"
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use http or https scheme"
        return True, ""
    except Exception:
        return False, "Invalid URL format"

async def fetch_content(url: str, service: str, session) -> dict:
    """Fetch content from a specific service
    
    Args:
        url: The webpage URL to convert to text
        service: The service to use ('jina' or 'markdowner')
        session: aiohttp ClientSession to use for requests
        
    Returns:
        dict: Contains either the extracted content or error information
    """
    rd = random.Random()
    headers = {
        'User-Agent': UserAgents[rd.randint(0, len(UserAgents)-1)],
        'Accept': 'text/plain',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    }

    try:
        if service == 'jina':
            req_url = f"https://r.jina.ai/{url}"
        else: # 'urltomarkdown':
            req_url = f"https://urltomarkdown.herokuapp.com/?url={url}"

        async with session.get(req_url, headers=headers, timeout=TIMEOUT_SECONDS) as resp:
            resp.raise_for_status()

            # Check content length
            if resp.headers.get('content-length'):
                content_length = int(resp.headers['content-length'])
                if content_length > MAX_CONTENT_LENGTH:
                    return {"error": "Content too large", "service": service}

            # Return plain text response in Markdown format
            try:
                if content := await resp.text():
                    return {
                        "content": content,
                        "url": url,
                        "timestamp": time.time()
                    }
                else:
                    return {"error": "No content found", "service": service}

            except ValueError:
                return {"error": "Invalid response format", "service": service}
    
    except asyncio.TimeoutError:
        logger.error(f"Timeout accessing URL via {service}: {url}")
        return {"error": "Request timed out", "service": service}
    except Exception as e:
        logger.error(f"Error fetching from {service}: {e}")
        return {"error": f"Failed to fetch content: {str(e)}", "service": service}

async def get_text_from_url_with_cache(url: str):
    """Convert webpage URL to text content with caching and parallel fetching
    
    Args:
        url: The webpage URL to convert to text
        
    Returns:
        dict: Contains either the extracted content or error information
    """
    # Validate URL
    is_valid, error = validate_url(url)
    if not is_valid:
        return {"error": error}

    async with aiohttp.ClientSession() as session:
        # Use only the reliable 'jina' service
        result = await fetch_content(url, 'jina', session)
        
        if "error" not in result:
            # Cache successful response
            url_cache[url] = result
            return result
        
        # If jina service failed, return the error
        return {"error": f"Service failed: {result['error']}"}

async def get_text_from_url(url: str):
    """Cached wrapper for get_text_from_url_with_cache"""
    # Check cache first
    if url in url_cache:
        cached_result = url_cache[url]
        cached_result["cached"] = True
        return cached_result
        
    return await get_text_from_url_with_cache(url)


# Tool specification in Bedrock format
list_of_tools_specs = [
    {
        "toolSpec": {
            "name": "get_text_from_url",
            "description": "Extract text content in Markdown format from a webpage URL. Use this when asked to read, summarize, or analyze the content of a specific webpage. This tool helps access online articles, documentation, or any web content that needs to be processed. The URL should be a direct web address (e.g., 'https://example.com/article').",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The webpage URL to convert to text"
                        }
                    },
                    "required": ["url"]
                }
            }
        }
    }
]
