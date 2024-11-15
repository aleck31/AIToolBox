# Copyright iX.
# SPDX-License-Identifier: MIT-0
import random
import requests
from requests.exceptions import HTTPError
# from selectolax.parser import HTMLParser
from common.logger import logger
# from gne import GeneralNewsExtractor


UserAgents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:45.0) Gecko/20100101 Firefox/45.0.."
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; rv:16.0) Gecko/20100101 Firefox/16.0",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36"
]

session = requests.Session()

# def fetch_web_text(url):
#     """
#     Fetch content from a given URL, return plain text.
#     """
#     rd = random.Random()
#     headers = {
#         "User-Agent": UserAgents[rd.randint(0, len(UserAgents)-1)],
#         'Accept': 'text / html, application / xhtml + xml, application / xml'
#     }

#     remove_tags = ['head', 'style', 'script', 'nav', 'header',
#                    'ul', 'link', 'img', 'xmp', 'iframe', 'noembed', 'noframes']

#     try:
#         # Send a GET request to fetch the website content
#         resp = session.get(url, headers=headers)

#         parser = HTMLParser(resp.text)
#         parser.strip_tags(remove_tags)
#         # for node in parser.css('div[class]'):
#         #     if node.css_matches('qr_code'):
#         #         node.decompose()
#         text = parser.text(deep=True, separator=" ", strip=True)

#         return text

#     except requests.exceptions.RequestException as ex:
#         # Handle request exceptions
#         logger.error(ex)
#         return None


def convert_url_text(url):
    """
    Converting a website URL into text format. 
    """

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

        return f"{title}'\n'{content}"
    
    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        return None
    

# def fetch_url_content(url):
#     """
#     Fetches the content of a given URL and returns it as text.
#     """
#     headers = {
#         "User-Agent": UserAgents[rd.randint(0, len(UserAgents)-1)],
#         'Accept': 'text / html, application / xhtml + xml, application / xml'
#     }

#     try:
#         # Send a GET request to fetch the website content
#         html = requests.get(url, headers=headers)
#         # resp.encoding = 'utf-8'
#         html.encoding = html.apparent_encoding

#         extractor = GeneralNewsExtractor()
#         content = extractor.extract(
#             html.text,
#             noise_node_list=[
#                 '//*[@style="display:none"]',
#                 '//div[@class="comment-list"]',
#             ],
#             use_visiable_info=False
#         )

#         # Get the text content of the website
#         json_content = json.dumps(content, ensure_ascii=False)

#         return json_content

#     except requests.exceptions.RequestException as ex:
#         # Handle request exceptions
#         logger.error(f"Error: {ex}")
#         return None
