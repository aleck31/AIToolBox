# Copyright iX.
# SPDX-License-Identifier: MIT-0
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from utils.common import get_secret


# api key secret_name = "dev_gemini_api"
gemin_api_key = get_secret('dev_gemini_api').get('api_key')

llm = ChatGoogleGenerativeAI(
    model="gemini-pro",
    google_api_key=gemin_api_key
)

llmv = ChatGoogleGenerativeAI(
    model="gemini-pro-vision",
    google_api_key=gemin_api_key
)

inference_modifier = {
    'max_tokens_to_sample':2048, 
    "temperature":1,
    "top_p":0.999,
    "top_k":250,
    "stop_sequences": ["\n\nHuman:"]
    }

