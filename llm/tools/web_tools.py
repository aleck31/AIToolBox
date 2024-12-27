import random
import requests
from requests.exceptions import HTTPError
from core.logger import logger

# Create session for requests
session = requests.Session()

UserAgents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:45.0) Gecko/20100101 Firefox/45.0.."
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; rv:16.0) Gecko/20100101 Firefox/16.0",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36"
]

def get_text_from_url(url: str):
    """Convert webpage URL to text content"""
    if not url:
        return {"error": "URL is required"}

    req_url = f"https://r.jina.ai/{url}"

    rd = random.Random()
    headers = {
        'Accept': 'application/json',
        'X-No-Cache': 'true',
        # 'X-With-Generated-Alt': 'true',
        "User-Agent": UserAgents[rd.randint(0, len(UserAgents)-1)]
    }

    try:
        # Send a GET request to fetch the website content
        resp = session.get(req_url, headers=headers)
        resp.raise_for_status()

        resp_body = resp.json().get('data')
        title = resp_body.get('title')
        content = resp_body.get('content')

        return {
            "title": title,
            "content": content
        }
    
    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        return {"error": f"HTTP error occurred: {http_err}"}
    except Exception as e:
        logger.error(f"Error converting webpage: {e}")
        return {"error": "Failed to convert webpage"}

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
