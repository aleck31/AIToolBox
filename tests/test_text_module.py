import asyncio
import sys
import os
import logging
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import logger
from core.session import Session
from core.service.gen_service import GenService

# Configure logging
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

async def test_gen_text():
    """Test the gen_text method to identify the issue with response.content"""
    try:
        # Create a mock session with proper parameters
        from datetime import datetime
        from core.session.models import SessionMetadata
        
        session = Session(
            session_id="test-session",
            session_name="Test Session",
            created_time=datetime.now(),
            updated_time=datetime.now(),
            user_name="demo",
            metadata=SessionMetadata(module_name="text")
        )
        
        # Add system prompt to session context
        session.context['system_prompt'] = """
        You are an expert in concise writing and text simplification.
        Your task is to simplify the text by removing redundant information and simplifying sentence structure
        while preserving the core message and key points. Focus on clarity and brevity.
        Ensure the output is in en_US language.
        Output only with the succinct context and nothing else.
        """
        
        # Create GenService
        gen_service = GenService(module_name="text")
        
        # Test content
        content = {
            "text": "Process the text within <original_text></original_text> tags according to the given instructions:\n"
                    "Ensuring the output is in en_US language:\n"
                    "<original_text>\n"
                    "Artificial Intelligence, commonly abbreviated as AI, is a broad field of computer science that focuses on creating intelligent machines that can perform tasks that typically require human intelligence. These tasks include visual perception, speech recognition, decision-making, and language translation.\n"
                    "</original_text>\n"
        }
        
        # Call gen_text and print the response structure
        print("\n=== Testing gen_text method ===")
        response = await gen_service.gen_text(session=session, content=content)
        print(f"Response type: {type(response)}")
        print(f"Response value: {response}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gen_text())
