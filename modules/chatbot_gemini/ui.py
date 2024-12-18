# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from fastapi import Request
from . import sync_multimodal_chat
from core.logger import logger
from modules.login import get_user

def create_chat_interface(request: Request = None):
    """Create chat interface with user context"""
    try:
        # Get user from session - this will raise HTTPException if not authenticated
        username = get_user(request) if request else None
        logger.debug(f"Creating chat interface for user: {username}")
        
        # Create chat interface with request context
        return gr.ChatInterface(
            fn=lambda msg, history: sync_multimodal_chat(msg, history, request),
            type='messages',
            multimodal=True,
            description="Let's chat ... (Powered by Gemini)",
            textbox=gr.MultimodalTextbox(
                file_types=['image', "video", "audio"],
                file_count='multiple',
                placeholder="Type a message or upload image(s)",
                scale=13,
                min_width=90
            ),
            stop_btn='🟥'
        )
    except Exception as e:
        logger.error(f"Error creating chat interface: {str(e)}")
        # Return a disabled interface with error message
        return gr.Textbox(
            value="Error: Please login to access the chat interface",
            interactive=False
        )

# Create default interface instance
tab_gemini = create_chat_interface()
