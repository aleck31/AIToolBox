import random
import requests
import time
from cachetools import TTLCache
from requests.exceptions import HTTPError, Timeout, SSLError, ConnectionError
from urllib.parse import urlparse
from core.logger import logger

# Constants
MAX_CONTENT_LENGTH = 1024 * 1024  # 1MB
TIMEOUT_SECONDS = 15
CACHE_TTL = 86400  # Cache for 1 day
CACHE_MAX_SIZE = 1000  # Maximum number of cached responses

# Create session for requests
session = requests.Session()

# Create cache for responses
response_cache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)

UserAgents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:45.0) Gecko/20100101 Firefox/45.0.."
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; rv:16.0) Gecko/20100101 Firefox/16.0",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36"
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

def get_text_from_url_with_cache(url: str):
    """Convert webpage URL to text content with caching
    
    Args:
        url: The webpage URL to convert to text
        
    Returns:
        dict: Contains either the extracted content or error information
        
    The function handles various failure cases:
    - Invalid URL format
    - Network connectivity issues
    - SSL certificate errors
    - Timeouts
    - Response size limits
    - Invalid response format
    """
    # Validate URL
    is_valid, error = validate_url(url)
    if not is_valid:
        return {"error": error}

    req_url = f"https://r.jina.ai/{url}"

    rd = random.Random()
    headers = {
        'Accept': 'application/json',
        'X-No-Cache': 'true',
        "User-Agent": UserAgents[rd.randint(0, len(UserAgents)-1)]
    }

    try:
        # Send a GET request to fetch the website content
        resp = session.get(
            req_url, 
            headers=headers, 
            timeout=TIMEOUT_SECONDS,
            verify=True  # Enforce SSL verification
        )
        resp.raise_for_status()
        
        # Check content length
        if resp.headers.get('content-length'):
            content_length = int(resp.headers['content-length'])
            if content_length > MAX_CONTENT_LENGTH:
                return {"error": "Content too large"}
        
        # Parse response
        try:
            resp_body = resp.json()
            if not resp_body or 'data' not in resp_body:
                return {"error": "Invalid response format"}
            
            data = resp_body['data']
            title = data.get('title', '').strip()
            content = data.get('content', '').strip()
            
            if not content:
                return {"error": "No content found"}
                
            result = {
                "title": title,
                "content": content,
                "url": url,  # Include original URL for reference
                "cached": False,
                "timestamp": time.time()
            }
            
            # Cache successful response
            response_cache[url] = result
            return result
            
        except ValueError:
            return {"error": "Invalid JSON response"}
    
    except Timeout:
        logger.error(f"Timeout accessing URL: {url}")
        return {"error": "Request timed out"}
    except SSLError as ssl_err:
        logger.error(f"SSL error: {ssl_err}")
        return {"error": "SSL certificate verification failed"}
    except ConnectionError as conn_err:
        logger.error(f"Connection error: {conn_err}")
        return {"error": "Failed to connect to server"}
    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        return {"error": f"HTTP error occurred: {http_err}"}
    except Exception as e:
        logger.error(f"Error converting webpage: {e}")
        return {"error": "Failed to convert webpage"}

def get_text_from_url(url: str):
    """Cached wrapper for get_text_from_url_with_cache"""
    # Check cache first
    if url in response_cache:
        cached_result = response_cache[url]
        cached_result["cached"] = True
        return cached_result
        
    return get_text_from_url_with_cache(url)

# Tool specification in Bedrock format
list_of_tools_specs = [
    {
        "toolSpec": {
            "name": "get_text_from_url",
            "description": "Extract readable text content from a webpage URL. Use this when asked to read, summarize, or analyze the content of a specific webpage. This tool helps access online articles, documentation, or any web content that needs to be processed. The URL should be a direct web address (e.g., 'https://example.com/article').",
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
