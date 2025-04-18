#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simplified test script to debug Claude 3.7's thinking and tool use functionality.
This script isolates the specific issue with the signature field structure.
"""

import asyncio
import json
import logging
import os
import sys

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.logger import logger
from llm.model_manager import model_manager
from llm.api_providers import LLMMessage
from llm.api_providers.bedrock_converse import BedrockConverse
from llm import LLMParameters

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger.setLevel(logging.DEBUG)

# System prompt
SYSTEM_PROMPT = """
You are a helpful assistant that thinks step by step and uses tools when needed.
"""

QUESTION="What is the capital of France? Please search to verify."

# Create LLM parameters
llm_params = LLMParameters(
    max_tokens=2048,
    temperature=0.7
)

async def test_reasoning_with_tool_use():
    """
    Test reasoning model with tool use
    Verify the structure of the signature field in thinking blocks
    """
    try:
        # Get reasoning model (e.g., Claude 3.7)
        models = model_manager.get_models(filter={'reasoning': True})
        if not models:
            logger.error("No reasoning models available")
            return
        
        # Use the first available reasoning model
        model = models[0]
        logger.info(f"Testing with model: {model.name} ({model.model_id})")
        
        # Create provider with thinking enabled
        thinking_params = {
            'thinking': {
                'type': 'enabled',
                'budget_tokens': 1024
            }
        }
        
        # Create provider with no tools first
        provider = BedrockConverse(
            model_id=model.model_id,
            llm_params=llm_params,
            tools=[]  # No tools for initial test
        )
        
        # Create message that will trigger thinking
        message = LLMMessage(
            role="user", 
            content=QUESTION
        )
        
        # Track thinking blocks and raw chunks to examine structure
        thinking_blocks = []
        raw_chunks = []
        
        logger.info("=== Testing Thinking Block Structure ===")
        
        # Process streaming response
        logger.info("\n--- Starting stream without tools ---")
        async for chunk in provider.generate_stream(
            messages=[message],
            system_prompt=SYSTEM_PROMPT,
            **thinking_params
        ):
            # Log the raw chunk for debugging
            logger.debug(f"Raw chunk: {json.dumps(chunk)}")
            raw_chunks.append(chunk)
            
            # Track thinking blocks
            if thinking := chunk.get('thinking'):
                thinking_blocks.append(thinking)
                logger.info(f"Thinking chunk received: {len(thinking)}")
        
        # Look for signature in raw chunks
        logger.info("\nExamining raw chunks for signature field:")
        for i, chunk in enumerate(raw_chunks):
            if 'signature' in json.dumps(chunk):
                logger.info(f"Found signature in chunk {i}:")
                logger.info(json.dumps(chunk, indent=2))
                break
        
        # Now test with a tool to see the error
        logger.info("\n=== Testing with Tool Use ===")
        
        # Create provider with a tool
        provider_with_tool = BedrockConverse(
            model_id=model.model_id,
            llm_params=llm_params,
            tools=['search_wikipedia']  # Add Wikipedia search tool
        )
        
        # Create message that will trigger tool use
        message_with_tool = LLMMessage(
            role="user", 
            content=QUESTION
        )
        
        # Process streaming response with tool
        logger.info("\n--- Starting stream with tools ---")
        try:
            async for chunk in provider_with_tool.generate_stream(
                messages=[message_with_tool],
                system_prompt=SYSTEM_PROMPT,
                **thinking_params
            ):
                # Just consume the stream
                pass
        except Exception as e:
            logger.error(f"Error with tool use: {str(e)}")
            logger.info("\nThis error confirms the issue with the signature field structure.")
            logger.info("The fix is to modify how the signature is included in the thinking block.")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_reasoning_with_tool_use())
