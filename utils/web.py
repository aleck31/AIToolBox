# Copyright iX.
# SPDX-License-Identifier: MIT-0
import json
import random
import requests
from gne import GeneralNewsExtractor



UserAgents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:45.0) Gecko/20100101 Firefox/45.0.."   
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; rv:16.0) Gecko/20100101 Firefox/16.0",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36"
    ]

rd = random.Random()

def fetch_url_content(url):
    """
    Fetches the content of a given URL and returns it as text.
    """
    headers = {
        "User-Agent": UserAgents[rd.randint(0, len(UserAgents)-1)],
        'Accept': 'text / html, application / xhtml + xml, application / xml'
    }    

    try:
        # Send a GET request to fetch the website content
        resp = requests.get(url, headers=headers)
        # resp.encoding = 'utf-8'
        resp.encoding = resp.apparent_encoding

        extractor = GeneralNewsExtractor()
        content = extractor.extract(
            resp.text, 
            noise_node_list=[
                '//div[@class="comment-list"]',
                '//div[@class="statement"]',
                '//*[@style="display:none"]'
            ],
            use_visiable_info=False
        )

        # Get the text content of the website
        json_content = json.dumps(content, ensure_ascii=False)
        
        return json_content

    
    except requests.exceptions.RequestException as ex:
        # Handle request exceptions
        print(f"Error: {ex}")
        return None
