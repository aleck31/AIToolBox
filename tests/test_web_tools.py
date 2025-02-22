import asyncio
from llm.tools.web_tools import get_text_from_url

async def test_get_text_from_url(url):
    # Test with a simple webpage
    result = await get_text_from_url(url)
    print(f"Result for {url}:")
    print(result)

if __name__ == "__main__":
    url = "https://example.com"
    asyncio.run(test_get_text_from_url(url))
